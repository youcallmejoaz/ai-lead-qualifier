import json

import pytest

from app.llm.schemas import TriageResult, output_schema
from app.pipeline.classify import TriageParseError, fallback_triage, parse_triage
from tests.conftest import make_fields


def valid(**overrides):
    data = {
        "category": "Sales",
        "confidence": 0.93,
        "reason": "Freight company asking for booking automation with a budget.",
        "injection_suspected": False,
        "fields": json.loads(make_fields().model_dump_json()),
    }
    data.update(overrides)
    return data


def test_parses_valid_output():
    result = parse_triage(json.dumps(valid()))
    assert result.category == "Sales"
    assert result.fields.company_size.value == 180


@pytest.mark.parametrize("alias,expected", [("sales lead", "Sales"), ("SUPPORT", "Support"), (" junk ", "Spam")])
def test_category_aliases_are_normalised(alias, expected):
    assert parse_triage(json.dumps(valid(category=alias))).category == expected


def test_unknown_category_is_rejected():
    with pytest.raises(TriageParseError, match="category"):
        parse_triage(json.dumps(valid(category="Partnership")))


def test_confidence_out_of_range_is_rejected():
    with pytest.raises(TriageParseError, match="confidence"):
        parse_triage(json.dumps(valid(confidence=1.4)))


def test_field_confidence_out_of_range_is_rejected():
    data = valid()
    data["fields"]["budget"]["confidence"] = -0.1
    with pytest.raises(TriageParseError, match="fields.budget.confidence"):
        parse_triage(json.dumps(data))


def test_missing_field_is_rejected():
    data = valid()
    del data["fields"]["timeline"]
    with pytest.raises(TriageParseError, match="timeline"):
        parse_triage(json.dumps(data))


def test_extra_keys_are_rejected():
    with pytest.raises(TriageParseError):
        parse_triage(json.dumps(valid(score=100)))


def test_malformed_json_is_rejected():
    with pytest.raises(TriageParseError, match="not valid JSON"):
        parse_triage('{"category": "Sales",')


def test_fallback_goes_to_a_person():
    result = fallback_triage("Model refused")
    assert result.category == "Other" and result.confidence == 0.0
    assert result.fields.urgency.value == "unknown"


def test_output_schema_is_closed_and_has_no_refs():
    schema = output_schema(TriageResult)
    text = json.dumps(schema)
    assert "$ref" not in text and "minimum" not in text
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    budget = schema["properties"]["fields"]["properties"]["budget"]
    assert budget["additionalProperties"] is False and budget["required"] == ["value", "confidence"]
