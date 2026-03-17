"""Tests for _util type coercion helpers."""

from __future__ import annotations

import pytest

from markdown_docx_compiler._util import as_bool, as_dict, as_float, as_int, as_list, as_list_of_str, as_str


class TestAsStr:
    @pytest.mark.parametrize(
        ("input_val", "expected"),
        [
            ("hello", "hello"),
            (42, "42"),
            (3.14, "3.14"),
            (0, "0"),
            (0.0, "0.0"),
        ],
    )
    def test_valid_values(self, input_val: object, expected: str) -> None:
        assert as_str(input_val) == expected

    @pytest.mark.parametrize("input_val", ["", None, [], {}])
    def test_returns_none(self, input_val: object) -> None:
        assert as_str(input_val) is None

    def test_bool_coerced_as_int_subclass(self) -> None:
        assert as_str(True) == "True"
        assert as_str(False) == "False"


class TestAsFloat:
    @pytest.mark.parametrize(
        ("input_val", "expected"),
        [
            (1, 1.0),
            (3.14, 3.14),
            ("2.5", 2.5),
            ("0", 0.0),
        ],
    )
    def test_valid_values(self, input_val: object, expected: float) -> None:
        assert as_float(input_val) == expected

    def test_none_returns_none(self) -> None:
        assert as_float(None) is None

    @pytest.mark.parametrize("input_val", ["abc", [], {}])
    def test_unconvertible_returns_none(self, input_val: object) -> None:
        assert as_float(input_val) is None


class TestAsInt:
    @pytest.mark.parametrize(
        ("input_val", "expected"),
        [
            (5, 5),
            ("10", 10),
            (3.9, 3),
        ],
    )
    def test_valid_values(self, input_val: object, expected: int) -> None:
        assert as_int(input_val) == expected

    def test_none_returns_none(self) -> None:
        assert as_int(None) is None

    @pytest.mark.parametrize("input_val", ["abc", [], {}])
    def test_unconvertible_returns_none(self, input_val: object) -> None:
        assert as_int(input_val) is None


class TestAsBool:
    @pytest.mark.parametrize("input_val", [True, "true", "True", "yes", "YES", "1"])
    def test_truthy(self, input_val: object) -> None:
        assert as_bool(input_val) is True

    @pytest.mark.parametrize("input_val", [False, "false", "False", "no", "NO", "0"])
    def test_falsy(self, input_val: object) -> None:
        assert as_bool(input_val) is False

    def test_none_returns_none(self) -> None:
        assert as_bool(None) is None

    @pytest.mark.parametrize("input_val", ["maybe", 42, [], {}])
    def test_unrecognized_returns_none(self, input_val: object) -> None:
        assert as_bool(input_val) is None

    def test_whitespace_stripped(self) -> None:
        assert as_bool("  true  ") is True


class TestAsDict:
    def test_dict_passthrough(self) -> None:
        d = {"a": 1}
        assert as_dict(d) is d

    @pytest.mark.parametrize("input_val", [None, "string", 42, []])
    def test_non_dict_returns_empty(self, input_val: object) -> None:
        assert as_dict(input_val) == {}


class TestAsList:
    def test_list_passthrough(self) -> None:
        lst = [1, 2, 3]
        assert as_list(lst) is lst

    @pytest.mark.parametrize("input_val", [None, "string", 42, {}])
    def test_non_list_returns_empty(self, input_val: object) -> None:
        assert as_list(input_val) == []


class TestAsListOfStr:
    def test_string_list(self) -> None:
        assert as_list_of_str(["a", "b"]) == ["a", "b"]

    def test_mixed_types_coerced(self) -> None:
        assert as_list_of_str([1, 2.5, "c"]) == ["1", "2.5", "c"]

    def test_empty_list(self) -> None:
        assert as_list_of_str([]) == []

    @pytest.mark.parametrize("input_val", [None, "string", 42, {}])
    def test_non_list_returns_none(self, input_val: object) -> None:
        assert as_list_of_str(input_val) is None
