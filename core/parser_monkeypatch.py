from edi_835_parser.loops.claim import Claim as ClaimLoop
from edi_835_parser.loops.service import Service as ServiceLoop
from edi_835_parser.loops.organization import Organization as OrganizationLoop
from edi_835_parser.segments.financial_information import FinancialInformation as FinancialInformationSegment
from edi_835_parser.segments.trace import Trace as TraceSegment

from core.parser_extension import (
    ClaimLoopJsonMixin,
    ServiceLoopJsonMixin, 
    OrganizationLoopJsonMixin,
    FinancialInformationJsonMixin,
    TraceJsonMixin
)

def apply_json_mixins():
    """Apply JSON conversion mixins to existing classes"""
    # Add to_dict methods to classes
    ClaimLoop.to_dict = ClaimLoopJsonMixin.to_dict
    ClaimLoop._get_nm1_data = ClaimLoopJsonMixin._get_nm1_data
    ClaimLoop._get_claim_dtm_data = ClaimLoopJsonMixin._get_claim_dtm_data
    ClaimLoop._get_claim_cas_data = ClaimLoopJsonMixin._get_claim_cas_data

    ServiceLoop.to_dict = ServiceLoopJsonMixin.to_dict
    ServiceLoop._get_service_dtm_data = ServiceLoopJsonMixin._get_service_dtm_data
    ServiceLoop._get_service_amt_data = ServiceLoopJsonMixin._get_service_amt_data
    ServiceLoop._get_service_cas_data = ServiceLoopJsonMixin._get_service_cas_data

    OrganizationLoop.to_dict = OrganizationLoopJsonMixin.to_dict
    OrganizationLoop._get_entity_identifier = OrganizationLoopJsonMixin._get_entity_identifier

    FinancialInformationSegment.to_dict = FinancialInformationJsonMixin.to_dict
    TraceSegment.to_dict = TraceJsonMixin.to_dict

# Apply mixins when module is imported
apply_json_mixins()