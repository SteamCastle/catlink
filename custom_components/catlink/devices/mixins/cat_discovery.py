"""Mixin for discovering cats from device logs."""

import re
from typing import Any


def extract_name_and_action(event: str) -> tuple[str | None, str | None]:
    """Extract cat name and action from event string.

    Args:
        event: Event string like "土豆🥔 pooped" or "三多🐱 peed"

    Returns:
        Tuple of (name, action) or (None, None) if not parseable
    """
    for action in ["pooped", "peed"]:
        if action in event:
            name = event.replace(action, "").strip()
            return name, action
    return None, None


def parse_weight(section: str) -> float | None:
    """Parse weight from firstSection string.

    Args:
        section: String like "7.9kg" or "5.2 kg"

    Returns:
        Weight as float or None if not parseable
    """
    match = re.search(r"([\d.]+)\s*kg", section, re.IGNORECASE)
    return float(match.group(1)) if match else None


def parse_duration(section: str) -> int | None:
    """Parse duration from secondSection string.

    Args:
        section: String like "173s" or "69 s"

    Returns:
        Duration in seconds as int or None if not parseable
    """
    match = re.search(r"(\d+)\s*s", section, re.IGNORECASE)
    return int(match.group(1)) if match else None


class CatDiscoveryMixin:
    """Mixin for devices that can discover cats from logs."""

    logs: list[dict[str, Any]]

    def get_cat_activities_from_logs(self) -> list[dict[str, Any]]:
        """Extract cat activities from device logs.

        Returns:
            List of activity dicts with keys:
            - pet_id: Cat's pet ID
            - name: Cat name extracted from event
            - type: "pee" or "poo"
            - weight: Weight in kg (or None)
            - duration: Duration in seconds (or None)
            - time: Time string
            - log_id: Log entry ID
            - raw_event: Original event string
        """
        activities = []
        for log in self.logs:
            # Skip non-WC type logs
            if log.get("type") != "WC":
                continue
            # Skip entries without valid pet ID
            pet_id = log.get("petId", "0")
            if pet_id == "0":
                continue

            activity = self._parse_cat_activity(log)
            if activity:
                activities.append(activity)
        return activities

    def _parse_cat_activity(self, log: dict[str, Any]) -> dict[str, Any] | None:
        """Parse a single log entry into cat activity data."""
        event = log.get("event", "")

        # Extract name and action
        name, action = extract_name_and_action(event)
        if not name:
            return None

        # Parse weight and duration
        weight = parse_weight(log.get("firstSection", ""))
        duration = parse_duration(log.get("secondSection", ""))

        # Determine activity type from snFlag
        sn_flag = log.get("snFlag", 0)
        activity_type = "poo" if sn_flag == 2 else "pee"

        return {
            "pet_id": log.get("petId"),
            "name": name,
            "type": activity_type,
            "weight": weight,
            "duration": duration,
            "time": log.get("time"),
            "log_id": log.get("id"),
            "raw_event": event,
        }
