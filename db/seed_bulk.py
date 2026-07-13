"""Fast bulk seeding using execute_values (parent tables) + COPY (leaf tables).

Strategy
--------
Parent tables (payments_835, raw_835_files, edi_transactions, claims,
service_lines) are inserted with ``execute_values(..., fetch=True)`` so we
get back the auto-generated SERIAL ids needed as FK references.

Leaf tables (payers, payees, nm1_entities, cas_adjustments, plb_adjustments)
have no downstream FK dependents, so they use PostgreSQL ``COPY FROM STDIN``
for maximum throughput.
"""

import io
import json
import logging
from typing import Any, Dict, List, Optional

from psycopg2.extensions import connection as Connection
from psycopg2.extras import execute_values, Json

from .models import (
    build_payments_835_row,
    build_raw_835_file_row,
    build_edi_transaction_row,
    build_payer_row,
    build_payee_row,
    build_claim_row,
    build_service_line_row,
    build_nm1_row,
    build_cas_rows,
    build_plb_row,
    find_org_by_type,
)

logger = logging.getLogger(__name__)

DEFAULT_RAW_JSON_TRANSACTION = ""
JSON_COLUMNS = {'raw_json_transaction'}


# =========================================================
# INSERT helper — returns auto-generated ids
# =========================================================

def _insert_row(cursor, table: str, row: Dict[str, Any]) -> int:
    """Single INSERT ... RETURNING id.  Returns the auto-generated PK."""
    columns = list(row.keys())
    values = []
    for col in columns:
        v = row[col]
        values.append(Json(v) if col in JSON_COLUMNS or isinstance(v, (dict, list)) else v)
    cols_str = ', '.join(columns)
    placeholders = ', '.join(['%s'] * len(columns))
    sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) RETURNING id"
    cursor.execute(sql, values)
    return cursor.fetchone()[0]


def _batch_insert_returning(cursor, table: str, rows: List[Dict[str, Any]]) -> List[int]:
    """Batch INSERT using execute_values.  Returns list of auto-generated ids
    in insertion order.  Falls back gracefully on an empty list."""
    if not rows:
        return []

    columns = list(rows[0].keys())
    tuples = []
    for row in rows:
        vals = []
        for col in columns:
            v = row[col]
            vals.append(Json(v) if col in JSON_COLUMNS or isinstance(v, (dict, list)) else v)
        tuples.append(tuple(vals))

    cols_str = ', '.join(columns)
    sql = f"INSERT INTO {table} ({cols_str}) VALUES %s RETURNING id"
    results = execute_values(cursor, sql, tuples, fetch=True)
    return [r[0] for r in results]


# =========================================================
# COPY helper — leaf tables (no id needed back)
# =========================================================

def _escape_copy(value: str) -> str:
    """Escape a string value for PostgreSQL COPY text format.

    Backslash, newline, carriage-return, and tab must be escaped.
    """
    return (
        value
        .replace('\\', '\\\\')
        .replace('\n', '\\n')
        .replace('\r', '\\r')
        .replace('\t', '\\t')
    )


def _copy_table(cursor, table: str, rows: List[Dict[str, Any]]):
    """Fast bulk insert via COPY FROM STDIN (no RETURNING)."""
    if not rows:
        return

    columns = list(rows[0].keys())
    buf = io.StringIO()

    for row in rows:
        vals = []
        for col in columns:
            v = row[col]
            if v is None:
                vals.append(r'\N')
            elif isinstance(v, (dict, list)):
                vals.append(_escape_copy(json.dumps(v)))
            else:
                vals.append(_escape_copy(str(v)))
        buf.write('\t'.join(vals) + '\n')

    buf.seek(0)
    sql = f"""COPY {table} ({','.join(columns)})
              FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '\\N')"""
    cursor.copy_expert(sql, buf)


# =========================================================
# Main bulk seed function
# =========================================================

def seed_file_copy(
    conn: Connection,
    file_id: str,
    file_name: str,
    json_data: Dict,
    raw_edi: str,
    raw_file_metadata: Optional[Dict[str, Any]] = None,
    location: Optional[str] = None,
    source_system: Optional[str] = None,
) -> Dict[str, Any]:
    """Seed all normalized tables for one EDI 835 file.

    Uses a single transaction — commits on success, rolls back on error.

    Returns:
        dict with counts: transactions, claims, service_lines,
                          payers, payees, nm1_entities, cas_adjustments,
                          plb_adjustments
    """
    cursor = conn.cursor()

    stats = {
        'transactions': 0,
        'claims': 0,
        'service_lines': 0,
        'payers': 0,
        'payees': 0,
        'nm1_entities': 0,
        'cas_adjustments': 0,
        'plb_adjustments': 0,
    }

    try:
        # Disable synchronous commit for speed
        cursor.execute("SET synchronous_commit = OFF")

        # ── Idempotency check ──────────────────────────────
        cursor.execute(
            "SELECT 1 FROM payments_835 WHERE file_id = %s LIMIT 1",
            (file_id,),
        )
        if cursor.fetchone():
            logger.info(f"{file_name} already processed")
            return stats

        transactions = json_data.get('interchange', {}).get('transactions', [])

        # ── Leaf-table buffers (COPY'd at the end) ────────
        payer_rows: List[Dict[str, Any]] = []
        payee_rows: List[Dict[str, Any]] = []
        nm1_rows: List[Dict[str, Any]] = []
        cas_rows: List[Dict[str, Any]] = []
        plb_rows: List[Dict[str, Any]] = []

        # ── Per-transaction processing ────────────────────
        for txn_index, txn in enumerate(transactions):
            stats['transactions'] += 1

            # 1. payments_835 — one row per transaction
            payments_row = build_payments_835_row(
                file_id, file_name, json_data, raw_edi, txn_index,
            )
            payments_row.setdefault('raw_json_transaction', DEFAULT_RAW_JSON_TRANSACTION)
            _insert_row(cursor, 'payments_835', payments_row)

            # 2. raw_835_files — FK via file_id UUID
            raw_row = build_raw_835_file_row(
                payments_row['file_id'],
                json_data,
                raw_edi,
                metadata=raw_file_metadata,
                location=location,
                source_system=source_system,
            )
            if raw_row.get('raw_json_transaction') is None:
                raw_row['raw_json_transaction'] = DEFAULT_RAW_JSON_TRANSACTION
            raw_file_id = _insert_row(cursor, 'raw_835_files', raw_row)

            # 3. edi_transactions — FK via raw_file_id (int)
            edi_row = build_edi_transaction_row(raw_file_id, txn)
            edi_txn_id = _insert_row(cursor, 'edi_transactions', edi_row)

            # 4. Payer / Payee (leaf — buffer for COPY)
            n1_loop = txn.get('N1_loop') or []

            payer = find_org_by_type(n1_loop, 'PR')
            if payer:
                payer_rows.append(build_payer_row(edi_txn_id, payer))
                stats['payers'] += 1

            payee = find_org_by_type(n1_loop, 'PE')
            if payee:
                payee_rows.append(build_payee_row(edi_txn_id, payee))
                stats['payees'] += 1

            # 5. Claims — batch INSERT to get claim_ids
            clp_loop_list = txn.get('CLP_loop') or []
            claim_rows = [build_claim_row(edi_txn_id, clp) for clp in clp_loop_list]
            claim_ids = _batch_insert_returning(cursor, 'claims', claim_rows)
            stats['claims'] += len(claim_ids)

            # 6. Per-claim children: service_lines (need ids), nm1, cas
            all_svc_rows: List[Dict[str, Any]] = []
            svc_parent_info: List[Dict] = []  # parallel list of svc_loop dicts

            for clp, claim_id in zip(clp_loop_list, claim_ids):
                # Claim-level NM1
                nm1_list = clp.get('NM1') or []
                if not isinstance(nm1_list, list):
                    nm1_list = [nm1_list]
                for nm1 in nm1_list:
                    if nm1:
                        nm1_rows.append(build_nm1_row(claim_id, None, nm1))
                        stats['nm1_entities'] += 1

                # Claim-level CAS
                cas_list = clp.get('CAS') or []
                if not isinstance(cas_list, list):
                    cas_list = [cas_list]
                for cas in cas_list:
                    if cas:
                        built = build_cas_rows(claim_id, None, cas)
                        cas_rows.extend(built)
                        stats['cas_adjustments'] += len(built)

                # Service lines — collect for batch INSERT
                for svc in clp.get('SVC_loop') or []:
                    all_svc_rows.append(build_service_line_row(claim_id, svc))
                    svc_parent_info.append(svc)

            # 7. Batch INSERT service_lines → get svc_ids
            svc_ids = _batch_insert_returning(cursor, 'service_lines', all_svc_rows)
            stats['service_lines'] += len(svc_ids)

            # 8. Service-level CAS + NM1 (leaf)
            for svc_dict, svc_id in zip(svc_parent_info, svc_ids):
                svc_cas = svc_dict.get('CAS') or []
                if not isinstance(svc_cas, list):
                    svc_cas = [svc_cas]
                for cas in svc_cas:
                    if cas:
                        built = build_cas_rows(None, svc_id, cas)
                        cas_rows.extend(built)
                        stats['cas_adjustments'] += len(built)

                svc_nm1 = svc_dict.get('NM1') or []
                if not isinstance(svc_nm1, list):
                    svc_nm1 = [svc_nm1]
                for nm1 in svc_nm1:
                    if nm1:
                        nm1_rows.append(build_nm1_row(None, svc_id, nm1))
                        stats['nm1_entities'] += 1

            # 9. PLB adjustments (leaf)
            plb_list = txn.get('PLB') or []
            if not isinstance(plb_list, list):
                plb_list = [plb_list]
            for plb in plb_list:
                if plb:
                    plb_rows.append(build_plb_row(edi_txn_id, plb))
                    stats['plb_adjustments'] += 1

        # ── COPY leaf tables in one shot ──────────────────
        _copy_table(cursor, 'payers', payer_rows)
        _copy_table(cursor, 'payees', payee_rows)
        _copy_table(cursor, 'nm1_entities', nm1_rows)
        _copy_table(cursor, 'cas_adjustments', cas_rows)
        _copy_table(cursor, 'plb_adjustments', plb_rows)

        conn.commit()
        logger.info(
            f"{file_name} seeded: {stats['transactions']} txn, "
            f"{stats['claims']} claims, {stats['service_lines']} svc lines"
        )
        return stats

    except Exception:
        conn.rollback()
        logger.exception("COPY seed failed")
        raise

    finally:
        cursor.close()
