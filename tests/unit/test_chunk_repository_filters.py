"""Unit tests for chunk_repository._build_property_filter_conditions."""

from relrag.infrastructure.persistence.postgres.chunk_repository import (
    _build_property_filter_conditions,
)


class TestBuildPropertyFilterConditions:
    """Tests for _build_property_filter_conditions."""

    def test_empty_dict(self) -> None:
        conditions, params = _build_property_filter_conditions({})
        assert conditions == []
        assert params == []

    def test_none_spec_skipped(self) -> None:
        conditions, params = _build_property_filter_conditions({"key": None})
        assert conditions == []
        assert params == []

    def test_one_of_list(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "status": {"one_of": ["a", "b"]},
        })
        assert len(conditions) == 1
        assert "EXISTS" in conditions[0]
        assert "ANY(%s)" in conditions[0]
        assert params == ["status", ["a", "b"]]

    def test_one_of_empty_list_skipped(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "x": {"one_of": []},
        })
        assert conditions == []
        assert params == []

    def test_one_of_non_list_skipped(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "x": {"one_of": "not a list"},
        })
        assert conditions == []
        assert params == []

    def test_gte_and_lte_numeric(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "num": {"gte": 10, "lte": 20},
        })
        assert len(conditions) == 1
        assert "::numeric" in conditions[0]
        assert ">= %s" in conditions[0]
        assert "<= %s" in conditions[0]
        assert params == ["num", 10, 20]

    def test_gte_only(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "n": {"gte": 5},
        })
        assert len(conditions) == 1
        assert ">= %s" in conditions[0]
        assert params == ["n", 5]

    def test_lte_only(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "n": {"lte": 100},
        })
        assert len(conditions) == 1
        assert "<= %s" in conditions[0]
        assert params == ["n", 100]

    def test_gte_lte_date_cast(self) -> None:
        # value that can't be float -> ::date
        conditions, params = _build_property_filter_conditions({
            "d": {"gte": "2020-01-01", "lte": "2020-12-31"},
        })
        assert len(conditions) == 1
        assert "::date" in conditions[0]
        assert params == ["d", "2020-01-01", "2020-12-31"]

    def test_eq_string(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "k": {"eq": "v"},
        })
        assert len(conditions) == 1
        assert "value = %s" in conditions[0]
        assert params == ["k", "v"]

    def test_eq_bool_true(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "flag": {"eq": True},
        })
        assert params == ["flag", "true"]

    def test_eq_bool_false(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "flag": {"eq": False},
        })
        assert params == ["flag", "false"]

    def test_primitive_as_eq(self) -> None:
        # bool, int, float, str as spec -> treated as {"eq": value}
        conditions, params = _build_property_filter_conditions({
            "a": True,
            "b": 42,
        })
        assert len(conditions) == 2
        assert params == ["a", "true", "b", "42"]

    def test_non_dict_spec_skipped(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "x": 123,  # becomes eq
            "y": [1, 2],  # not dict, not primitive -> skipped after isinstance(spec, dict) fails
        })
        # x -> eq 42; y -> list is not dict so skipped
        assert len(conditions) == 1
        assert params == ["x", "123"]

    def test_multiple_filters(self) -> None:
        conditions, params = _build_property_filter_conditions({
            "status": {"one_of": ["open"]},
            "count": {"gte": 1, "lte": 10},
            "name": {"eq": "test"},
        })
        assert len(conditions) == 3
        assert len(params) == 7  # status + [open], count + 1 + 10, name + test
