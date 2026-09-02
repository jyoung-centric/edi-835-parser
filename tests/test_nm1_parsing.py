from edi_835_parser.transaction_set.transaction_set import TransactionSet


def test_claim_json_emits_all_nm1_entities_in_source_order(tmp_path):
    edi_file = tmp_path / "all_nm1_entities.edi"
    edi_file.write_text(
        "ST*835*0001~"
        "CLP*CLAIM1*1*100*80*20*12*ICN1~"
        "NM1*82*1*PROVIDER*RENDERING****XX*1000000001~"
        "NM1*74*1*PATIENT*CORRECTED****MI*MEMBER74~"
        "NM1*IL*1*SUBSCRIBER*INSURED****MI*MEMBERIL~"
        "NM1*PR*2*PAYER NAME*****PI*PAYER1~"
        "NM1*QC*1*PATIENT*CURRENT****MI*MEMBERQC~"
        "NM1*TT*2*TRANSFER CARRIER*****PI*PAYER2~"
        "SE*9*0001~"
    )

    transaction = TransactionSet.build(str(edi_file))
    claim_json = transaction.to_json()["interchange"]["transactions"][0]["CLP_loop"][0]

    assert [entity["entity_identifier_code"] for entity in claim_json["NM1"]] == [
        "rendering provider",
        "insured",
        "IL",
        "PR",
        "patient",
        "TT",
    ]
    assert [entity["identification_code"] for entity in claim_json["NM1"]] == [
        "1000000001",
        "MEMBER74",
        "MEMBERIL",
        "PAYER1",
        "MEMBERQC",
        "PAYER2",
    ]
