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
    build_cas_row,
    build_plb_row,
    find_org_by_type,
)

logger = logging.getLogger(__name__)


def insert_row(cursor: Cursor, table: str, row_dict: Dict[str, Any]) -> int:
    """
    Generic INSERT helper that builds SQL from dictionary.

    Args:
        cursor: psycopg2 cursor
        table: Table name
        row_dict: Dictionary with column names as keys

    Returns:
        Inserted row ID from RETURNING id clause

    Raises:
        psycopg2.Error: If insert fails
    """
    # Wrap dict/list values with Json() for proper JSONB handling
    processed_values = {}
    for key, value in row_dict.items():
        if isinstance(value, (dict, list)):
            processed_values[key] = Json(value)
        else:
            processed_values[key] = value

    columns = list(processed_values.keys())
    values = list(processed_values.values())
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)

    sql = f"""
        INSERT INTO {table} ({columns_str})
        VALUES ({placeholders})
        RETURNING id
    """

    cursor.execute(sql, values)
    result = cursor.fetchone()
    return result[0] if result else None


def is_already_processed(cursor: Cursor, file_id: str) -> bool:
    """
    Check if file has already been processed (idempotency check).

    Args:
        cursor: psycopg2 cursor
        file_id: File UUID from generate_file_id()

    Returns:
        True if file exists in payments_835 table
    """
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
    Seed all database tables for a single EDI 835 file.

    Respects foreign key constraints by inserting in proper order.
    Uses a single transaction - commits on success, rolls back on error.

    Args:
        conn: psycopg2 connection (autocommit=False)
        file_id: Generated UUID for file
        file_name: Original file name
        json_data: Parsed JSON from parse_to_json()
        raw_edi: Raw EDI file content

    Returns:
        Dictionary with processing statistics:
            - transactions: count
            - claims: count
            - service_lines: count
            - payers: count
            - payees: count

    Raises:
        psycopg2.Error: If any database operation fails
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
        # Check idempotency
        if is_already_processed(cursor, file_id):
            logger.info(f"File {file_name} already processed (file_id={file_id}), skipping")
            cursor.close()
            return stats

        # Process each transaction - each gets its own payments_835 row
        transactions = json_data.get('interchange', {}).get('transactions', [])
        logger.info(f"File {file_name} contains {len(transactions)} transaction(s)")

        for txn_index, transaction in enumerate(transactions):
            stats['transactions'] += 1

            # 1. Insert into payments_835 (one row per transaction)
            payments_835_row = build_payments_835_row(file_id, file_name, json_data, raw_edi, txn_index)
            payments_835_id = insert_row(cursor, 'payments_835', payments_835_row)
            logger.debug(f"Inserted payments_835 id={payments_835_id} (transaction {txn_index + 1}/{len(transactions)})")

            # 2. Insert into raw_835_files
            raw_file_row = build_raw_835_file_row(payments_835_id, file_name)
            raw_file_id = insert_row(cursor, 'raw_835_files', raw_file_row)
            logger.debug(f"Inserted raw_835_files id={raw_file_id}")

            # Insert edi_transactions
            edi_transaction_row = build_edi_transaction_row(raw_file_id, transaction)
            edi_transaction_id = insert_row(cursor, 'edi_transactions', edi_transaction_row)
            logger.debug(f"Inserted edi_transaction id={edi_transaction_id}")

            # Insert payer (PR) and payee (PE) from N1_loop
            n1_loop_list = transaction.get('N1_loop', [])

            payer_loop = find_org_by_type(n1_loop_list, 'PR')
            if payer_loop:
                payer_row = build_payer_row(edi_transaction_id, payer_loop)
                payer_id = insert_row(cursor, 'payers', payer_row)
                stats['payers'] += 1
                logger.debug(f"Inserted payer id={payer_id}")

            payee_loop = find_org_by_type(n1_loop_list, 'PE')
            if payee_loop:
                payee_row = build_payee_row(edi_transaction_id, payee_loop)
                payee_id = insert_row(cursor, 'payees', payee_row)
                stats['payees'] += 1
                logger.debug(f"Inserted payee id={payee_id}")

            # Process claims (CLP_loop)
            clp_loop_list = transaction.get('CLP_loop', [])
            for clp_loop in clp_loop_list:
                stats['claims'] += 1

                # Insert claim
                claim_row = build_claim_row(edi_transaction_id, clp_loop)
                claim_id = insert_row(cursor, 'claims', claim_row)
                logger.debug(f"Inserted claim id={claim_id}")

                # Insert claim-level NM1 entities
                nm1_list = clp_loop.get('NM1', [])
                if not isinstance(nm1_list, list):
                    nm1_list = [nm1_list] if nm1_list else []

                for nm1_dict in nm1_list:
                    if nm1_dict:  # Skip empty dicts
                        nm1_row = build_nm1_row(claim_id, None, nm1_dict)
                        nm1_id = insert_row(cursor, 'nm1_entities', nm1_row)
                        stats['nm1_entities'] += 1
                        logger.debug(f"Inserted nm1_entity (claim-level) id={nm1_id}")

                # Insert claim-level CAS adjustments
                cas_list = clp_loop.get('CAS', [])
                if not isinstance(cas_list, list):
                    cas_list = [cas_list] if cas_list else []

                for cas_dict in cas_list:
                    if cas_dict:  # Skip empty dicts
                        cas_row = build_cas_row(claim_id, None, cas_dict)
                        cas_id = insert_row(cursor, 'cas_adjustments', cas_row)
                        stats['cas_adjustments'] += 1
                        logger.debug(f"Inserted cas_adjustment (claim-level) id={cas_id}")

                # Process service lines (SVC_loop)
                svc_loop_list = clp_loop.get('SVC_loop', [])
                for svc_loop in svc_loop_list:
                    stats['service_lines'] += 1

                    # Insert service line
                    service_line_row = build_service_line_row(claim_id, svc_loop)
                    service_line_id = insert_row(cursor, 'service_lines', service_line_row)
                    logger.debug(f"Inserted service_line id={service_line_id}")

                    # Insert service-level CAS adjustments
                    svc_cas_list = svc_loop.get('CAS', [])
                    if not isinstance(svc_cas_list, list):
                        svc_cas_list = [svc_cas_list] if svc_cas_list else []

                    for cas_dict in svc_cas_list:
                        if cas_dict:  # Skip empty dicts
                            cas_row = build_cas_row(None, service_line_id, cas_dict)
                            cas_id = insert_row(cursor, 'cas_adjustments', cas_row)
                            stats['cas_adjustments'] += 1
                            logger.debug(f"Inserted cas_adjustment (service-level) id={cas_id}")

            # Insert PLB adjustments (provider level balance)
            plb_list = transaction.get('PLB', [])
            if not isinstance(plb_list, list):
                plb_list = [plb_list] if plb_list else []

            for plb_dict in plb_list:
                if plb_dict:  # Skip empty dicts
                    plb_row = build_plb_row(edi_transaction_id, plb_dict)
                    plb_id = insert_row(cursor, 'plb_adjustments', plb_row)
                    stats['plb_adjustments'] += 1
                    logger.debug(f"Inserted plb_adjustment id={plb_id}")

        # Commit transaction
        conn.commit()
        logger.info(
            f"Successfully seeded {file_name}: "
            f"{stats['transactions']} transactions, "
            f"{stats['claims']} claims, "
            f"{stats['service_lines']} service lines"
        )

        cursor.close()
        return stats

    except Exception as e:
        # Rollback on any error
        conn.rollback()
        cursor.close()
        logger.error(f"Error seeding {file_name}: {e}")
        raise
