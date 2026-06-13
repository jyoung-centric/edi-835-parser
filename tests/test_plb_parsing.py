from edi_835_parser.segments.provider_adjustment import ProviderAdjustment
from edi_835_parser.transaction_set.transaction_set import TransactionSet


def test_provider_adjustment_parses_multiple_adjustment_pairs():
	plb = ProviderAdjustment(
		"PLB*1033166244*20251231*AH:32T*1451.40*WO^22646576066*-1096.29"
	)

	assert plb.reference_identification == "1033166244"
	assert plb.fiscal_period_date == "20251231"

	plb_dicts = plb.to_adjustment_dicts()
	assert plb_dicts == [
		{
			"reference_identification": "1033166244",
			"fiscal_period_date": "20251231",
			"provider_adjustment_reason_code": "AH",
			"provider_adjustment_identifier": "32T",
			"provider_adjustment_amount": "1451.40",
			"provider_adjustment_identifier_raw": "AH:32T",
		},
		{
			"reference_identification": "1033166244",
			"fiscal_period_date": "20251231",
			"provider_adjustment_reason_code": "WO",
			"provider_adjustment_identifier": "22646576066",
			"provider_adjustment_amount": "-1096.29",
			"provider_adjustment_identifier_raw": "WO^22646576066",
		},
	]


def test_provider_adjustment_supports_pipe_and_greater_than_delimiters():
	plb = ProviderAdjustment("PLB|1033166244|20231015|AH>XJ23X166000130|24.50")

	assert plb.to_adjustment_dicts() == [
		{
			"reference_identification": "1033166244",
			"fiscal_period_date": "20231015",
			"provider_adjustment_reason_code": "AH",
			"provider_adjustment_identifier": "XJ23X166000130",
			"provider_adjustment_amount": "24.50",
			"provider_adjustment_identifier_raw": "AH>XJ23X166000130",
		}
	]


def test_transaction_set_json_includes_plb_after_last_service(tmp_path):
	edi_file = tmp_path / "with_plb.edi"
	edi_file.write_text(
		"ST*835*0001~"
		"CLP*CLAIM1*1*100*80*20*12*ICN1~"
		"NM1*QC*1*DOE*JANE****MI*123~"
		"SVC*HC:99213*100*80**1~"
		"DTM*472*20250101~"
		"PLB*1033166244*20251231*AH:32T*1451.40*WO^22646576066*-1096.29~"
		"SE*7*0001~"
	)

	transaction_set = TransactionSet.build(str(edi_file))
	transaction_json = transaction_set.to_json()["interchange"]["transactions"][0]

	assert len(transaction_set.claims) == 1
	assert len(transaction_set.claims[0].services) == 1
	assert len(transaction_set.provider_adjustments) == 1
	assert transaction_json["PLB_TOTAL"] == "355.11"
	assert transaction_json["PLB"] == [
		{
			"reference_identification": "1033166244",
			"fiscal_period_date": "20251231",
			"provider_adjustment_reason_code": "AH",
			"provider_adjustment_identifier": "32T",
			"provider_adjustment_amount": "1451.40",
			"provider_adjustment_identifier_raw": "AH:32T",
		},
		{
			"reference_identification": "1033166244",
			"fiscal_period_date": "20251231",
			"provider_adjustment_reason_code": "WO",
			"provider_adjustment_identifier": "22646576066",
			"provider_adjustment_amount": "-1096.29",
			"provider_adjustment_identifier_raw": "WO^22646576066",
		},
	]
