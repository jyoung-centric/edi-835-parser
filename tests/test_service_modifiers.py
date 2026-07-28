import pytest

from core import parser_monkeypatch  # noqa: F401 - applies JSON mixins
from db.models import build_service_line_row
from edi_835_parser.loops.service import Service as ServiceLoop
from edi_835_parser.segments.service import Service as ServiceSegment


@pytest.mark.parametrize("separator", ["^", ":", ">", "<"])
def test_service_segment_parses_all_modifier_positions(separator):
    composite = separator.join(["HC", "J0696", "JW", "JZ", "KX", "GA"])
    service = ServiceSegment(f"SVC*{composite}*268.76*0")

    assert service.code == "J0696"
    assert service.qualifier == "HC"
    assert service.modifier == "JW"
    assert service.modifiers == ["JW", "JZ", "KX", "GA"]


def test_service_segment_uses_empty_modifier_list_when_absent():
    service = ServiceSegment("SVC*HC^S9500*225*0")

    assert service.modifier is None
    assert service.modifiers == []


def test_service_json_includes_modifiers():
    service = ServiceSegment("SVC*HC^J0696^JW*268.76*0")
    svc_json = ServiceLoop(service=service).to_dict()["SVC"]

    assert svc_json["service_type_code"] == "J0696"
    assert svc_json["service_modifiers"] == ["JW"]


def test_service_json_includes_empty_modifier_list():
    service = ServiceSegment("SVC*HC^S9500*225*0")
    svc_json = ServiceLoop(service=service).to_dict()["SVC"]

    assert svc_json["service_modifiers"] == []


def test_service_line_row_maps_first_four_modifiers():
    svc_loop = {
        "SVC": {
            "service_type_code": "J0696",
            "service_modifiers": ["JW", "JZ", "KX", "GA"],
            "charge_amount": "268.76",
            "payment_amount": "0",
        }
    }

    row = build_service_line_row(42, svc_loop)

    assert row["modifier1"] == "JW"
    assert row["modifier2"] == "JZ"
    assert row["modifier3"] == "KX"
    assert row["modifier4"] == "GA"


def test_service_line_row_uses_nulls_for_absent_modifiers():
    row = build_service_line_row(
        42,
        {"SVC": {"service_type_code": "S9500", "service_modifiers": []}},
    )

    assert row["modifier1"] is None
    assert row["modifier2"] is None
    assert row["modifier3"] is None
    assert row["modifier4"] is None
