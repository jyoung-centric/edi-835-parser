"""Type coercion helpers and field mapping functions for database row building.

Column names match the Flyway schema in schema-bot-automation-main/migrations/.
"""

import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional


# ============================================================================
# Utility Functions - Type Coercion
# ============================================================================

def safe_decimal(value: Any) -> Optional[Decimal]:
    """Convert value to Decimal, returning None for empty/invalid values."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == '' or value.lower() == 'none':
            return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def safe_text(value: Any) -> Optional[str]:
    """Convert value to string, returning None for empty values."""
    if value is None:
        return None
    text = str(value).strip()
    if text == '' or text.lower() == 'none':
        return None
    return text


def parse_edi_date(date_str: Any) -> Optional[date]:
    """Parse EDI date format YYYYMMDD to Python date."""
    if not date_str:
        return None
    text = safe_text(date_str)
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        try:
            return datetime.strptime(text, '%Y%m%d').date()
        except ValueError:
            return None
    return None


def extract_status_code(status_str: Any) -> Optional[str]:
    """Extract bare status code from a Status object string or plain string."""
    if not status_str:
        return None
    text = str(status_str)
    match = re.search(r"code='([^']+)'", text)
    if match:
        return match.group(1)
    clean = safe_text(text)
    if clean and len(clean) <= 2:
        return clean
    return None


def generate_file_id(file_name: str) -> str:
    """Generate deterministic UUID5 from file name for idempotency."""
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    return str(uuid.uuid5(namespace, file_name))


def find_org_by_type(n1_loop_list: List[Dict], type_code: str) -> Optional[Dict]:
    """
    Find organization in N1_loop list by entity_identifier_code.

    Args:
        n1_loop_list: List of N1_loop dictionaries
        type_code: 'PR' for payer, 'PE' for payee
    """
    if not n1_loop_list:
        return None
    for n1_loop in n1_loop_list:
        n1 = n1_loop.get('N1', {})
        if n1.get('entity_identifier_code') == type_code:
            return n1_loop
    return None


# ============================================================================
# Row Builders — payments_835
# ============================================================================

def build_payments_835_row(
    file_id: str,
    file_name: str,
    json_data: Dict,
    raw_edi: str,
    transaction_index: int = 0
) -> Dict[str, Any]:
    """
    Build row for payments_835 table (one row per transaction).

    Schema columns: file_id, file_name, receive_date_time, check_number,
                    payment_date, payment_amount, payer_id, payee_id,
                    json_transaction, raw_edi
    """
    transactions = json_data.get('interchange', {}).get('transactions', [])
    transaction = transactions[transaction_index] if transaction_index < len(transactions) else {}

    bpr = transaction.get('BPR') or {}
    trn = transaction.get('TRN') or {}
    n1_loop = transaction.get('N1_loop') or []

    payee_loop = find_org_by_type(n1_loop, 'PE')
    payee_id = None
    if payee_loop:
        payee_id = safe_text(payee_loop.get('N1', {}).get('identification_code'))

    txn_file_id = file_id
    if transaction_index > 0:
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        txn_file_id = str(uuid.uuid5(namespace, f"{file_name}::txn_{transaction_index}"))

    return {
        'file_id': txn_file_id,
        'file_name': safe_text(file_name),
        'receive_date_time': datetime.now(),
        'check_number': safe_text(trn.get('reference_identification')),
        'payment_date': parse_edi_date(bpr.get('check_issue_or_eft_effective_date')),
        'payment_amount': safe_decimal(bpr.get('monetary_amount')),
        'payer_id': safe_text(trn.get('originating_company_identifier')),
        'payee_id': payee_id,
        'json_transaction': json_data,
        'raw_edi': raw_edi,
    }


# ============================================================================
# Row Builders — Normalized Tables
# ============================================================================

def build_raw_835_file_row(
    file_id: str,
    s3_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build row for raw_835_files table.

    Schema columns: file_id (UUID FK → payments_835.file_id),
                    receive_date_time, archive_s3_key
    """
    return {
        'file_id': file_id,
        'receive_date_time': datetime.now(),
        'archive_s3_key': safe_text(s3_key),
    }


def build_edi_transaction_row(
    raw_file_id: int,
    transaction: Dict
) -> Dict[str, Any]:
    """
    Build row for edi_transactions table.

    Schema columns: raw_file_id, trace_number, payment_method, payment_amount,
                    payment_date, payer_id, payee_id, check_amount, check_date,
                    json_tr (NOT NULL)
    """
    bpr = transaction.get('BPR') or {}
    trn = transaction.get('TRN') or {}

    payee_loop = find_org_by_type(transaction.get('N1_loop') or [], 'PE')
    payee_id = None
    if payee_loop:
        payee_id = safe_text(payee_loop.get('N1', {}).get('identification_code'))

    payment_date = parse_edi_date(bpr.get('check_issue_or_eft_effective_date'))

    return {
        'raw_file_id': raw_file_id,
        'trace_number': safe_text(trn.get('reference_identification')),
        'payment_method': safe_text(bpr.get('payment_method_code')),
        'payment_amount': safe_decimal(bpr.get('monetary_amount')),
        'payment_date': payment_date,
        'payer_id': safe_text(trn.get('originating_company_identifier')),
        'payee_id': payee_id,
        'check_amount': safe_decimal(bpr.get('monetary_amount')),
        'check_date': payment_date,
        'json_tr': transaction,
    }


def build_payer_row(
    edi_transaction_id: int,
    n1_loop_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for payers table.

    Schema columns: edi_transaction_id, payer_name, payer_id_qualifier,
                    payer_id, json_payer (NOT NULL)
    """
    n1 = n1_loop_dict.get('N1', {})
    return {
        'edi_transaction_id': edi_transaction_id,
        'payer_name': safe_text(n1.get('name')),
        'payer_id_qualifier': safe_text(n1.get('identification_code_qualifier')),
        'payer_id': safe_text(n1.get('identification_code')),
        'json_payer': n1_loop_dict,
    }


def build_payee_row(
    edi_transaction_id: int,
    n1_loop_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for payees table.

    Schema columns: edi_transaction_id, payee_name, payee_id_qualifier,
                    payee_id, json_payee (NOT NULL)
    """
    n1 = n1_loop_dict.get('N1', {})
    return {
        'edi_transaction_id': edi_transaction_id,
        'payee_name': safe_text(n1.get('name')),
        'payee_id_qualifier': safe_text(n1.get('identification_code_qualifier')),
        'payee_id': safe_text(n1.get('identification_code')),
        'json_payee': n1_loop_dict,
    }


def build_claim_row(
    edi_transaction_id: int,
    clp_loop_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for claims table.

    Schema columns: edi_transaction_id, claim_account_number,
                    patient_control_number, claim_status_code,
                    total_claim_charge_amount, claim_net_amount,
                    patient_responsibility_amount, claim_icn_number,
                    facility_type_code, claim_frequency_code,
                    json_clm (NOT NULL), post_date_time
    """
    clp = clp_loop_dict.get('CLP', {})
    return {
        'edi_transaction_id': edi_transaction_id,
        'claim_account_number': None,
        'patient_control_number': safe_text(clp.get('patient_control_number')),
        'claim_status_code': extract_status_code(clp.get('claim_status_code')),
        'total_claim_charge_amount': safe_decimal(clp.get('total_claim_charge_amount')),
        'claim_net_amount': safe_decimal(clp.get('total_claim_payment_amount')),
        'patient_responsibility_amount': safe_decimal(clp.get('patient_responsibility_amount')),
        'claim_icn_number': safe_text(clp.get('payer_claim_control_number')),
        'facility_type_code': safe_text(clp.get('facility_type_code')),
        'claim_frequency_code': safe_text(clp.get('claim_frequency_code')),
        'json_clm': clp_loop_dict,
        'post_date_time': None,
    }


def build_service_line_row(
    claim_id: int,
    svc_loop_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for service_lines table.

    Schema columns: claim_id, hcpcs_code, modifier1-4,
                    line_item_charge_amount, service_line_payment_amount,
                    revenue_code, units_of_service_paid_count,
                    units_of_service_submitted_count, json_svc (NOT NULL),
                    post_date_time
    """
    svc = svc_loop_dict.get('SVC', {})
    return {
        'claim_id': claim_id,
        'hcpcs_code': safe_text(svc.get('service_type_code')),
        'modifier1': None,
        'modifier2': None,
        'modifier3': None,
        'modifier4': None,
        'line_item_charge_amount': safe_decimal(svc.get('charge_amount')),
        'service_line_payment_amount': safe_decimal(svc.get('payment_amount')),
        'revenue_code': safe_text(svc.get('revenue_code')),
        'units_of_service_paid_count': safe_decimal(svc.get('units_of_service_paid')),
        'units_of_service_submitted_count': None,
        'json_svc': svc_loop_dict,
        'post_date_time': None,
    }


def build_nm1_row(
    claim_id: Optional[int],
    service_line_id: Optional[int],
    nm1_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for nm1_entities table.

    Schema columns: claim_id, service_line_id, entity_type, last_name,
                    first_name, middle_name, id_qualifier, entity_id,
                    json_nm1 (NOT NULL), name_prefix, name_suffix
    """
    return {
        'claim_id': claim_id,
        'service_line_id': service_line_id,
        'entity_type': safe_text(nm1_dict.get('entity_type_qualifier')),
        'last_name': safe_text(nm1_dict.get('last_name')),
        'first_name': safe_text(nm1_dict.get('first_name')),
        'middle_name': safe_text(nm1_dict.get('middle_name')),
        'id_qualifier': safe_text(nm1_dict.get('identification_code_qualifier')),
        'entity_id': safe_text(nm1_dict.get('identification_code')),
        'json_nm1': nm1_dict,
    }


def build_cas_rows(
    claim_id: Optional[int],
    service_line_id: Optional[int],
    cas_dict: Dict
) -> List[Dict[str, Any]]:
    """
    Build rows for cas_adjustments table (one row per adjustment within a CAS).

    CAS JSON structure:
        {
            "claim_adjustment_group_code": "CO",
            "adjustments": [
                {"claim_adjustment_reason_code": "45", "monetary_amount": "100.00", "quantity": "1"},
                ...
            ]
        }

    Schema columns: claim_id, service_line_id, group_code, reason_code,
                    amount, quantity, json_cas (NOT NULL)
    """
    group_code = safe_text(cas_dict.get('claim_adjustment_group_code'))
    rows = []
    for adj in cas_dict.get('adjustments', []):
        rows.append({
            'claim_id': claim_id,
            'service_line_id': service_line_id,
            'group_code': group_code,
            'reason_code': safe_text(adj.get('claim_adjustment_reason_code')),
            'amount': safe_decimal(adj.get('monetary_amount')),
            'quantity': safe_decimal(adj.get('quantity')),
            'json_cas': cas_dict,
        })
    return rows


def build_plb_row(
    edi_transaction_id: int,
    plb_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for plb_adjustments table.

    Schema columns: edi_transaction_id, provider_id, fiscal_period_date,
                    reason_code, reference_id, amount, json_plb (NOT NULL)
    """
    return {
        'edi_transaction_id': edi_transaction_id,
        'provider_id': safe_text(plb_dict.get('reference_identification')),
        'fiscal_period_date': parse_edi_date(plb_dict.get('fiscal_period_date')),
        'reason_code': safe_text(plb_dict.get('provider_adjustment_reason_code')),
        'reference_id': safe_text(plb_dict.get('provider_adjustment_identifier')),
        'amount': safe_decimal(plb_dict.get('provider_adjustment_amount')),
        'json_plb': plb_dict,
    }
