"""Tests for CatDiscoveryMixin."""

import pytest

from custom_components.catlink.devices.mixins.cat_discovery import (
    CatDiscoveryMixin,
    extract_name_and_action,
    parse_weight,
    parse_duration,
)


class TestExtractNameAndAction:
    """Tests for extract_name_and_action function."""

    def test_extract_name_from_pooped_event(self) -> None:
        """Test extracting cat name from pooped event."""
        name, action = extract_name_and_action("土豆🥔 pooped")
        assert name == "土豆🥔"
        assert action == "pooped"

    def test_extract_name_from_peed_event(self) -> None:
        """Test extracting cat name from peed event."""
        name, action = extract_name_and_action("三多🐱 peed")
        assert name == "三多🐱"
        assert action == "peed"

    def test_extract_name_with_spaces(self) -> None:
        """Test extracting name with extra spaces."""
        name, action = extract_name_and_action("  小花  pooped  ")
        assert name == "小花"
        assert action == "pooped"

    def test_returns_none_for_unknown_action(self) -> None:
        """Test returns None for unknown action."""
        name, action = extract_name_and_action("Auto-clean")
        assert name is None
        assert action is None

    def test_returns_none_for_empty_string(self) -> None:
        """Test returns None for empty string."""
        name, action = extract_name_and_action("")
        assert name is None
        assert action is None


class TestParseWeight:
    """Tests for parse_weight function."""

    def test_parse_weight_kg(self) -> None:
        """Test parsing weight in kg."""
        assert parse_weight("7.9kg") == 7.9

    def test_parse_weight_with_space(self) -> None:
        """Test parsing weight with space."""
        assert parse_weight("5.2 kg") == 5.2

    def test_parse_weight_uppercase(self) -> None:
        """Test parsing weight with uppercase KG."""
        assert parse_weight("6.0KG") == 6.0

    def test_parse_weight_returns_none_for_invalid(self) -> None:
        """Test returns None for invalid input."""
        assert parse_weight("") is None
        assert parse_weight("no weight") is None


class TestParseDuration:
    """Tests for parse_duration function."""

    def test_parse_duration_seconds(self) -> None:
        """Test parsing duration in seconds."""
        assert parse_duration("173s") == 173

    def test_parse_duration_with_space(self) -> None:
        """Test parsing duration with space."""
        assert parse_duration("69 s") == 69

    def test_parse_duration_uppercase(self) -> None:
        """Test parsing duration with uppercase S."""
        assert parse_duration("100S") == 100

    def test_parse_duration_returns_none_for_invalid(self) -> None:
        """Test returns None for invalid input."""
        assert parse_duration("") is None
        assert parse_duration("no duration") is None


class TestCatDiscoveryMixin:
    """Tests for CatDiscoveryMixin class."""

    def test_get_cat_activities_from_logs(self) -> None:
        """Test extracting cat activities from logs."""
        mixin = CatDiscoveryMixin()
        mixin.logs = [
            {
                "time": "11:24",
                "event": "土豆🥔 pooped",
                "firstSection": "7.9kg",
                "secondSection": "173s",
                "id": "899877558",
                "type": "WC",
                "petId": "548334",
                "snFlag": 2,
            },
            {
                "time": "10:29",
                "event": "三多🐱 peed",
                "firstSection": "5.2kg",
                "secondSection": "69s",
                "id": "899857182",
                "type": "WC",
                "petId": "548337",
                "snFlag": 0,
            },
            {
                "time": "11:27",
                "event": "Auto-clean",
                "type": "RUN",
                "petId": "0",
            },
        ]

        activities = mixin.get_cat_activities_from_logs()

        assert len(activities) == 2
        assert activities[0]["pet_id"] == "548334"
        assert activities[0]["name"] == "土豆🥔"
        assert activities[0]["type"] == "poo"
        assert activities[0]["weight"] == 7.9
        assert activities[0]["duration"] == 173
        assert activities[1]["pet_id"] == "548337"
        assert activities[1]["name"] == "三多🐱"
        assert activities[1]["type"] == "pee"

    def test_get_cat_activities_skips_pet_id_zero(self) -> None:
        """Test that activities with petId=0 are skipped."""
        mixin = CatDiscoveryMixin()
        mixin.logs = [
            {
                "time": "11:27",
                "event": "Auto-clean",
                "type": "RUN",
                "petId": "0",
            },
        ]

        activities = mixin.get_cat_activities_from_logs()
        assert len(activities) == 0

    def test_get_cat_activities_skips_non_wc_type(self) -> None:
        """Test that non-WC type logs are skipped."""
        mixin = CatDiscoveryMixin()
        mixin.logs = [
            {
                "time": "11:27",
                "event": "Auto-clean",
                "type": "RUN",
                "petId": "548334",
            },
        ]

        activities = mixin.get_cat_activities_from_logs()
        assert len(activities) == 0
