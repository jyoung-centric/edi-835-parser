"""Database seeding functions for EDI 835 files."""

import logging
from typing import Dict, Any, Optional
from psycopg2.extensions import cursor as Cursor, connection as Connection
from psycopg2.extras import Json

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


def insert_row(cursor: Cursor, table: str, row_dict: Dict[str, Any]) -> int:
    """
    Generic INSERT helper that builds SQL from a dictionary.

    Wraps dict/list values with Json() for JSONB columns.
    Returns the auto-generated id from RETURNING id.
    """
    processed = {}
    for key, value in row_dict.items():
        if isinstance(value, (dict, list)):
            processed[key] = Json(value)
        else:
            processed[key] = value

    columns = list(processed.keys())
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)

    sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders}) RETURNING id"
    cursor.execute(sql, list(processed.values()))
    result = cursor.fetchone()
    return result[0] if result else None


def is_already_processed(cursor: Cursor, file_id: str) -> bool:
    """Check if file has already been inserted (idempotency guard)."""
    cursor.execute(
        "SELECT 1 FROM payments_835 WHERE file_id = %s",
        (file_id,)
    )
    return cursor.fetchone() is not None


def seed_file(
    conn: Connection,
    file_id: str,
    file_name: str,
    json_data: Dict,
    raw_edi: str
) -> Dict[str, Any]:
    """
    Insert all normalized tables for a single EDI 835 file.

    Inserts in foreign-key order. Uses a single transaction — commits on
    success, rolls back on any error.

    Args:
        conn:      psycopg2 connection (autocommit=False)
        file_id:   UUID string generated from the file name
        file_name: Original file name
        json_data: Parsed JSON from parse_to_json()
        raw_edi:   Raw EDI file content

    Returns:
        Dict with counts: transactions, claims, service_lines,
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
        if is_already_processed(cursor, file_id):
            logger.info(f"File {file_name} already processed (file_id={file_id}), skipping")
            cursor.close()
            return stats

        transactions = json_data.get('interchange', {}).get('transactions', [])
        logger.info(f"File {file_name} contains {len(transactions)} transaction(s)")

        for txn_index, transaction in enumerate(transactions):
            stats['transactions'] += 1

            # 1. payments_835 — one row per transaction
            payments_row = build_payments_835_row(file_id, file_name, json_data, raw_edi, txn_index)
            insert_row(cursor, 'payments_835', payments_row)
            # Capture the file_id used for this transaction (may differ for txn_index > 0)
            txn_file_id = payments_row['file_id']
            logger.debug(f"Inserted payments_835 file_id={txn_file_id}")

            # 2. raw_835_files — FK is file_id UUID (not int id)
            raw_file_row = build_raw_835_file_row(txn_file_id)
            raw_file_id = insert_row(cursor, 'raw_835_files', raw_file_row)
            logger.debug(f"Inserted raw_835_files id={raw_file_id}")

            # 3. edi_transactions
            edi_txn_row = build_edi_transaction_row(raw_file_id, transaction)
            edi_transaction_id = insert_row(cursor, 'edi_transactions', edi_txn_row)
            logger.debug(f"Inserted edi_transactions id={edi_transaction_id}")

            # 4. payers and payees from N1_loop
            n1_loop_list = transaction.get('N1_loop', [])

            payer_loop = find_org_by_type(n1_loop_list, 'PR')
            if payer_loop:
                payer_row = build_payer_row(edi_transaction_id, payer_loop)
                insert_row(cursor, 'payers', payer_row)
                stats['payers'] += 1

            payee_loop = find_org_by_type(n1_loop_list, 'PE')
            if payee_loop:
                payee_row = build_payee_row(edi_transaction_id, payee_loop)
                insert_row(cursor, 'payees', payee_row)
                stats['payees'] += 1

            # 5. claims (CLP_loop)
            for clp_loop in transaction.get('CLP_loop', []):
                stats['claims'] += 1

                claim_row = build_claim_row(edi_transaction_id, clp_loop)
                claim_id = insert_row(cursor, 'claims', claim_row)

                # Claim-level NM1 entities
                nm1_list = clp_loop.get('NM1', [])
                if not isinstance(nm1_list, list):
                    nm1_list = [nm1_list] if nm1_list else []
                for nm1_dict in nm1_list:
                    if nm1_dict:
                        nm1_row = build_nm1_row(claim_id, None, nm1_dict)
                        insert_row(cursor, 'nm1_entities', nm1_row)
                        stats['nm1_entities'] += 1

                # Claim-level CAS adjustments
                cas_list = clp_loop.get('CAS', [])
                if not isinstance(cas_list, list):
                    cas_list = [cas_list] if cas_list else []
                for cas_dict in cas_list:
                    if cas_dict:
                        for cas_row in build_cas_rows(claim_id, None, cas_dict):
                            insert_row(cursor, 'cas_adjustments', cas_row)
                            stats['cas_adjustments'] += 1

                # 6. service lines (SVC_loop)
                for svc_loop in clp_loop.get('SVC_loop', []):
                    stats['service_lines'] += 1

                    svc_row = build_service_line_row(claim_id, svc_loop)
                    service_line_id = insert_row(cursor, 'service_lines', svc_row)

                    # Service-level CAS adjustments
                    svc_cas_list = svc_loop.get('CAS', [])
                    if not isinstance(svc_cas_list, list):
                        svc_cas_list = [svc_cas_list] if svc_cas_list else []
                    for cas_dict in svc_cas_list:
                        if cas_dict:
                            for cas_row in build_cas_rows(None, service_line_id, cas_dict):
                                insert_row(cursor, 'cas_adjustments', cas_row)
                                stats['cas_adjustments'] += 1

            # 7. PLB adjustments (provider level balance)
            plb_list = transaction.get('PLB', [])
            if not isinstance(plb_list, list):
                plb_list = [plb_list] if plb_list else []
            for plb_dict in plb_list:
                if plb_dict:
                    plb_row = build_plb_row(edi_transaction_id, plb_dict)
                    insert_row(cursor, 'plb_adjustments', plb_row)
                    stats['plb_adjustments'] += 1

        conn.commit()
        logger.info(
            f"Seeded {file_name}: {stats['transactions']} transactions, "
            f"{stats['claims']} claims, {stats['service_lines']} service lines"
        )
        cursor.close()
        return stats

    except Exception as e:
        conn.rollback()
        cursor.close()
        logger.error(f"Error seeding {file_name}: {e}")
        raise
