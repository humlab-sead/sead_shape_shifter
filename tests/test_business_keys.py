"""Tests for stable business-key serialization used by SIMS identity work."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
import pytest

from src.business_keys import (
    BUSINESS_ID_FORMAT_VERSION,
    BusinessKeyError,
    business_id_for_row,
    business_key_errors,
    encode_business_key,
    serialize_business_key,
)


class TestEncodeBusinessKey:
    """Tests for one row's normalized key parts."""

    def test_keeps_declared_key_order(self):
        parts = encode_business_key(["second", "first"], {"first": "A", "second": "B"})

        assert [part.column for part in parts] == ["second", "first"]
        assert [(part.type_tag, part.value) for part in parts] == [("string", "B"), ("string", "A")]

    def test_string_keeps_case_and_contents(self):
        parts = encode_business_key(["code"], {"code": "  Mixed Case  "})

        assert parts[0].type_tag == "string"
        assert parts[0].value == "  Mixed Case  "

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (5, "5"),
            (Decimal("5.00"), "5"),
            (5.25, "5.25"),
            (100.0, "100"),
        ],
    )
    def test_numbers_normalize_to_decimal_text(self, value, expected):
        parts = encode_business_key(["amount"], {"amount": value})

        assert parts[0].type_tag == "number"
        assert parts[0].value == expected

    def test_booleans_use_lowercase_text(self):
        assert encode_business_key(["flag"], {"flag": True})[0].value == "true"
        assert encode_business_key(["flag"], {"flag": False})[0].value == "false"

    def test_dates_use_iso_text(self):
        parts = encode_business_key(["day"], {"day": date(2026, 10, 18)})

        assert (parts[0].type_tag, parts[0].value) == ("date", "2026-10-18")

    def test_timezone_aware_datetimes_convert_to_utc(self):
        local = datetime(2026, 10, 18, 12, 0, tzinfo=timezone(timedelta(hours=2)))

        parts = encode_business_key(["at"], {"at": local})

        assert parts[0].type_tag == "datetime"
        assert parts[0].value == local.astimezone(timezone.utc).isoformat()

    def test_missing_value_is_rejected(self):
        with pytest.raises(BusinessKeyError, match="value is missing"):
            encode_business_key(["code"], {"code": None})

    def test_blank_string_is_rejected(self):
        with pytest.raises(BusinessKeyError, match="value is blank"):
            encode_business_key(["code"], {"code": "   "})

    def test_nan_is_rejected(self):
        with pytest.raises(BusinessKeyError, match="not a finite number"):
            encode_business_key(["amount"], {"amount": float("nan")})

    def test_naive_datetime_is_rejected(self):
        with pytest.raises(BusinessKeyError, match="naive datetimes"):
            encode_business_key(["at"], {"at": datetime(2026, 10, 18, 12, 0)})

    def test_missing_column_is_rejected(self):
        with pytest.raises(BusinessKeyError, match="does not contain this column"):
            encode_business_key(["code"], {"other": "value"})

    def test_unsupported_type_is_rejected(self):
        with pytest.raises(BusinessKeyError, match="unsupported value type"):
            encode_business_key(["value"], {"value": object()})

    def test_empty_key_list_is_rejected(self):
        with pytest.raises(BusinessKeyError, match="at least one business key"):
            encode_business_key([], {"code": "A"})


class TestSerializeBusinessKey:
    """Tests for the serialized business ID shape."""

    def test_serializes_versioned_ordered_array(self):
        parts = encode_business_key(["code", "amount"], {"code": "A", "amount": 2})

        assert serialize_business_key(parts) == f'[{BUSINESS_ID_FORMAT_VERSION},[["code","string","A"],["amount","number","2"]]]'

    def test_serialization_is_deterministic(self):
        row = {"code": "A", "amount": 2}

        assert business_id_for_row(["code", "amount"], row) == business_id_for_row(["code", "amount"], row)

    def test_key_order_changes_the_business_id(self):
        row = {"first": "A", "second": "B"}

        assert business_id_for_row(["first", "second"], row) != business_id_for_row(["second", "first"], row)

    def test_non_key_fields_do_not_change_the_business_id(self):
        keys = ["code"]

        assert business_id_for_row(keys, {"code": "A", "name": "one"}) == business_id_for_row(keys, {"code": "A", "name": "two"})


class TestBusinessKeyErrors:
    """Tests for declared-key validation across one entity table."""

    def test_accepts_unique_present_keys(self):
        frame = pd.DataFrame({"site_code": ["A", "B"]})

        assert business_key_errors("site", ["site_code"], frame) == []

    def test_rejects_empty_key_declaration(self):
        errors = business_key_errors("site", [], pd.DataFrame({"site_code": ["A"]}))

        assert errors == ["Tracked entity 'site' declares no business keys; declare ordered 'keys' in the project entity configuration"]

    def test_rejects_duplicate_key_declaration(self):
        errors = business_key_errors("site", ["a", "a"], pd.DataFrame({"a": ["1"]}))

        assert any("duplicate business key column(s): a" in error for error in errors)

    def test_rejects_managed_identifier_columns(self):
        errors = business_key_errors("site", ["system_id"], pd.DataFrame({"system_id": [1]}), public_id="site_id")
        errors_with_public_id = business_key_errors("site", ["site_id"], pd.DataFrame({"site_id": [1]}), public_id="site_id")

        assert any("managed identifier column(s) as business keys: system_id" in error for error in errors)
        assert any("managed identifier column(s) as business keys: site_id" in error for error in errors_with_public_id)

    def test_rejects_missing_key_column(self):
        errors = business_key_errors("site", ["site_code"], pd.DataFrame({"other": ["A"]}))

        assert errors == ["Tracked entity 'site' is missing declared business key column(s) 'site_code' in the transformed delivery"]

    def test_rejects_duplicate_values_in_one_delivery(self):
        frame = pd.DataFrame({"site_code": ["A", "A"]})

        errors = business_key_errors("site", ["site_code"], frame)

        assert len(errors) == 1
        assert "rows '0' and '1' share one business key value" in errors[0]

    def test_rejects_missing_value_in_one_row(self):
        frame = pd.DataFrame({"site_code": ["A", None]})

        errors = business_key_errors("site", ["site_code"], frame)

        assert len(errors) == 1
        assert "row '1'" in errors[0]
        assert "value is missing" in errors[0]

    def test_composite_keys_compare_the_whole_tuple(self):
        frame = pd.DataFrame({"site_code": ["A", "A"], "layer": ["1", "2"]})

        assert business_key_errors("site", ["site_code", "layer"], frame) == []

    def test_repeated_values_across_tables_are_not_compared(self):
        first = pd.DataFrame({"site_code": ["A"]})
        second = pd.DataFrame({"site_code": ["A"]})

        assert business_key_errors("site", ["site_code"], first) == []
        assert business_key_errors("other_site", ["site_code"], second) == []
