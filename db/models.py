"""Type coercion helpers and field mapping functions for database row building."""

import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional


# ============================================================================
# Utility Functions - Type Coercion
# ============================================================================

def safe_decimal(value: Any) -> Optional[Decimal]:
    """
    Convert value to Decimal, handling None, empty strings, and "None" strings.

    Args:
        value: Input value (str, int, float, Decimal, or None)

    Returns:
        Decimal or None
    """
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
    """
    Convert value to text, handling None, empty strings, and "None" strings.

    Args:
        value: Input value

    Returns:
        Stripped string or None
    """
    if value is None:
        return None
    text = str(value).strip()
    if text == '' or text.lower() == 'none':
        return None
    return text


def parse_edi_date(date_str: Any) -> Optional[date]:
    """
    Parse EDI date format (YYYYMMDD or CCYYMMDD) to Python date.

    Args:
        date_str: Date string in format "20110108" or 8-digit format

    Returns:
        date object or None if invalid/empty
    """
    if not date_str:
        return None
    text = safe_text(date_str)
    if not text:
        return None

    # Handle YYYYMMDD (8 digits)
    if len(text) == 8 and text.isdigit():
        try:
            return datetime.strptime(text, '%Y%m%d').date()
        except ValueError:
            return None

    return None


def extract_status_code(status_str: Any) -> Optional[str]:
    """
    Extract status code from Status object string representation.

    Args:
        status_str: Status string like "Status(code='1', ...)"

    Returns:
        Status code or None
    """
    if not status_str:
        return None
    text = str(status_str)

    # Try to extract code='X' pattern
    match = re.search(r"code='([^']+)'", text)
    if match:
        return match.group(1)

    # If it's just a simple code value
    clean = safe_text(text)
    if clean and len(clean) <= 2:
        return clean

    return None


def generate_file_id(file_name: str) -> str:
    """
    Generate deterministic UUID5 from file name for idempotency.

    Args:
        file_name: Base file name (without path)

    Returns:
        UUID string
    """
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
    return str(uuid.uuid5(namespace, file_name))


def find_org_by_type(n1_loop_list: List[Dict], type_code: str) -> Optional[Dict]:
    """
    Find organization in N1_loop list by entity_type_code.

    Args:
        n1_loop_list: List of N1_loop dictionaries
        type_code: Entity type code ('PR' for payer, 'PE' for payee)

    Returns:
        N1_loop dictionary or None
    """
    if not n1_loop_list:
        return None
    for n1_loop in n1_loop_list:
        n1 = n1_loop.get('N1', {})
        if n1.get('entity_type_code') == type_code:
            return n1_loop
    return None


# ============================================================================
# Row Builders - payments_835 (Simple Storage)
# ============================================================================

def build_payments_835_row(
    file_id: str,
    file_name: str,
    json_data: Dict,
    raw_edi: str,
    transaction_index: int = 0
) -> Dict[str, Any]:
    """
    Build row for payments_835 table (simple storage with complete JSON).

    Args:
        file_id: Generated UUID for file
        file_name: Original file name
        json_data: Complete parsed JSON from parse_to_json()
        raw_edi: Raw EDI file content
        transaction_index: Index of the transaction within the file (0-based)

    Returns:
        Dictionary with column names and values
    """
    transactions = json_data.get('interchange', {}).get('transactions', [])
    transaction = transactions[transaction_index] if transaction_index < len(transactions) else {}

    bpr = transaction.get('BPR', {})
    trn = transaction.get('TRN', {})
    n1_loop = transaction.get('N1_loop', [])

    # Find payee (PE) in N1_loop
    payee = find_org_by_type(n1_loop, 'PE')
    payee_id = None
    if payee:
        payee_n1 = payee.get('N1', {})
        payee_id = safe_text(payee_n1.get('identification_code'))

    # For multi-transaction files, make file_id unique per transaction
    # by appending the transaction index (only if >0 to preserve backward compat)
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
        'json_transaction': json_data,  # Will be wrapped with Json() in insert_row
        'raw_edi': raw_edi,
    }


# ============================================================================
# Row Builders - Normalized Tables
# ============================================================================

def build_raw_835_file_row(
    payments_835_id: int,
    file_name: str,
    s3_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build row for raw_835_files table.

    Args:
        payments_835_id: FK to payments_835.id
        file_name: Original file name
        s3_key: S3 archive key (optional)

    Returns:
        Dictionary with column names and values
    """
    return {
        'payments_835_id': payments_835_id,
        'file_name': safe_text(file_name),
        'upload_timestamp': datetime.now(),
        's3_key': safe_text(s3_key),
    }


def build_edi_transaction_row(
    raw_file_id: int,
    transaction: Dict
) -> Dict[str, Any]:
    """
    Build row for edi_transactions table.

    Args:
        raw_file_id: FK to raw_835_files.id
        transaction: Transaction dictionary from JSON

    Returns:
        Dictionary with column names and values
    """
    bpr = transaction.get('BPR', {})
    trn = transaction.get('TRN', {})

    return {
        'raw_file_id': raw_file_id,
        'transaction_handling_code': safe_text(bpr.get('transaction_handling_code')),
        'payment_amount': safe_decimal(bpr.get('monetary_amount')),
        'credit_debit_flag': safe_text(bpr.get('credit_or_debit_flag_code')),
        'payment_method_code': safe_text(bpr.get('payment_method_code')),
        'payment_format_code': safe_text(bpr.get('payment_format_code')),
        'sender_dfi_id': safe_text(bpr.get('sender_dfi_identification')),
        'sender_account_number': safe_text(bpr.get('sender_account_number')),
        'payer_id': safe_text(bpr.get('originating_company_identifier')),
        'receiver_dfi_id': safe_text(bpr.get('receiver_dfi_identification')),
        'receiver_account_number': safe_text(bpr.get('receiver_account_number')),
        'check_issue_date': parse_edi_date(bpr.get('check_issue_or_eft_effective_date')),
        'trace_type_code': safe_text(trn.get('trace_type_code')),
        'trace_number': safe_text(trn.get('reference_identification')),
        'originating_company_identifier': safe_text(trn.get('originating_company_identifier')),
        'reference_identification': safe_text(trn.get('reference_identification_2')),
    }


def build_payer_row(
    edi_transaction_id: int,
    n1_loop_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for payers table.

    Args:
        edi_transaction_id: FK to edi_transactions.id
        n1_loop_dict: N1_loop dictionary for payer (PR)

    Returns:
        Dictionary with column names and values
    """
    n1 = n1_loop_dict.get('N1', {})
    n3 = n1_loop_dict.get('N3', {})
    n4 = n1_loop_dict.get('N4', {})
    ref = n1_loop_dict.get('REF', {})
    per = n1_loop_dict.get('PER', {})

    return {
        'edi_transaction_id': edi_transaction_id,
        'entity_type_code': safe_text(n1.get('entity_type_code')),
        'entity_identifier_code': safe_text(n1.get('entity_identifier_code')),
        'name': safe_text(n1.get('name')),
        'identification_code_qualifier': safe_text(n1.get('identification_code_qualifier')),
        'identification_code': safe_text(n1.get('identification_code')),
        'address_line_1': safe_text(n3.get('address_information_1')),
        'address_line_2': safe_text(n3.get('address_information_2')),
        'city': safe_text(n4.get('city_name')),
        'state': safe_text(n4.get('state_or_province_code')),
        'zip_code': safe_text(n4.get('postal_code')),
        'country_code': safe_text(n4.get('country_code')),
        'ref_qualifier': safe_text(ref.get('reference_identification_qualifier')) if ref else None,
        'ref_id': safe_text(ref.get('reference_identification')) if ref else None,
        'contact_name': safe_text(per.get('name')) if per else None,
        'contact_phone': safe_text(per.get('communication_number')) if per else None,
    }


def build_payee_row(
    edi_transaction_id: int,
    n1_loop_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for payees table.

    Args:
        edi_transaction_id: FK to edi_transactions.id
        n1_loop_dict: N1_loop dictionary for payee (PE)

    Returns:
        Dictionary with column names and values
    """
    # Same structure as payer
    return build_payer_row(edi_transaction_id, n1_loop_dict)


def build_claim_row(
    edi_transaction_id: int,
    clp_loop_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for claims table.

    Args:
        edi_transaction_id: FK to edi_transactions.id
        clp_loop_dict: CLP_loop dictionary from JSON

    Returns:
        Dictionary with column names and values
    """
    clp = clp_loop_dict.get('CLP', {})

    return {
        'edi_transaction_id': edi_transaction_id,
        'patient_control_number': safe_text(clp.get('patient_control_number')),
        'claim_status_code': extract_status_code(clp.get('claim_status_code')),
        'total_claim_charge_amount': safe_decimal(clp.get('total_claim_charge_amount')),
        'claim_net_amount': safe_decimal(clp.get('total_claim_payment_amount')),
        'claim_filing_indicator_code': safe_text(clp.get('claim_filing_indicator_code')),
        'claim_icn_number': safe_text(clp.get('payer_claim_control_number')),
        'facility_type_code': safe_text(clp.get('facility_type_code')),
        'claim_frequency_code': safe_text(clp.get('claim_frequency_code')),
        'patient_responsibility_amount': safe_decimal(clp.get('patient_responsibility_amount')),
        'json_clm': clp_loop_dict,  # Full CLP_loop structure
    }


def build_service_line_row(
    claim_id: int,
    svc_loop_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for service_lines table.

    Args:
        claim_id: FK to claims.id
        svc_loop_dict: SVC_loop dictionary from JSON

    Returns:
        Dictionary with column names and values
    """
    svc = svc_loop_dict.get('SVC', {})

    return {
        'claim_id': claim_id,
        'hcpcs_code': safe_text(svc.get('service_type_code')),
        'line_item_charge_amount': safe_decimal(svc.get('charge_amount')),
        'service_line_payment_amount': safe_decimal(svc.get('payment_amount')),
        'revenue_code': safe_text(svc.get('revenue_code')),
        'units_of_service_paid_count': safe_decimal(svc.get('units_of_service_paid')),
        'modifier1': None,  # Not in current JSON output; preserved in json_svc
        'modifier2': None,
        'modifier3': None,
        'modifier4': None,
        'json_svc': svc_loop_dict,  # Full SVC_loop structure
    }


def build_nm1_row(
    claim_id: Optional[int],
    service_line_id: Optional[int],
    nm1_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for nm1_entities table.

    Args:
        claim_id: FK to claims.id (for claim-level entities)
        service_line_id: FK to service_lines.id (for service-level entities)
        nm1_dict: NM1 dictionary from JSON

    Returns:
        Dictionary with column names and values
    """
    return {
        'claim_id': claim_id,
        'service_line_id': service_line_id,
        'entity_identifier_code': safe_text(nm1_dict.get('entity_identifier_code')),
        'entity_type_qualifier': safe_text(nm1_dict.get('entity_type_qualifier')),
        'last_name': safe_text(nm1_dict.get('name_last_or_organization_name')),
        'first_name': safe_text(nm1_dict.get('name_first')),
        'middle_name': safe_text(nm1_dict.get('name_middle')),
        'name_suffix': safe_text(nm1_dict.get('name_suffix')),
        'identification_code_qualifier': safe_text(nm1_dict.get('identification_code_qualifier')),
        'identification_code': safe_text(nm1_dict.get('identification_code')),
    }


def build_cas_row(
    claim_id: Optional[int],
    service_line_id: Optional[int],
    cas_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for cas_adjustments table.

    Args:
        claim_id: FK to claims.id (for claim-level adjustments)
        service_line_id: FK to service_lines.id (for service-level adjustments)
        cas_dict: CAS dictionary from JSON

    Returns:
        Dictionary with column names and values
    """
    return {
        'claim_id': claim_id,
        'service_line_id': service_line_id,
        'adjustment_group_code': safe_text(cas_dict.get('claim_adjustment_group_code')),
        'reason_code': safe_text(cas_dict.get('adjustment_reason_code')),
        'adjustment_amount': safe_decimal(cas_dict.get('adjustment_amount')),
        'adjustment_quantity': safe_decimal(cas_dict.get('adjustment_quantity')),
    }


def build_plb_row(
    edi_transaction_id: int,
    plb_dict: Dict
) -> Dict[str, Any]:
    """
    Build row for plb_adjustments table.

    Args:
        edi_transaction_id: FK to edi_transactions.id
        plb_dict: PLB dictionary from JSON

    Returns:
        Dictionary with column names and values
    """
    return {
        'edi_transaction_id': edi_transaction_id,
        'provider_identifier': safe_text(plb_dict.get('reference_identification')),
        'fiscal_period_date': parse_edi_date(plb_dict.get('fiscal_period_date')),
        'adjustment_reason_code': safe_text(plb_dict.get('provider_adjustment_reason_code')),
        'adjustment_identifier': safe_text(plb_dict.get('provider_adjustment_identifier')),
        'adjustment_amount': safe_decimal(plb_dict.get('provider_adjustment_amount')),
    }
