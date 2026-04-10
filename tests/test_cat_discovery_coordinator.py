"""Tests for cat discovery in DevicesCoordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.catlink.devices.cat import CatDevice
from custom_components.catlink.devices.c08 import C08Device
from custom_components.catlink.modules.devices_coordinator import DevicesCoordinator


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {
        "catlink": {
            "config": {},
            "add_entities": {},
            "devices": {},
        }
    }
    hass.config.time_zone = "Asia/Shanghai"
    return hass


@pytest.fixture
def mock_account(mock_hass):
    """Create a mock Account instance."""
    account = MagicMock()
    account.hass = mock_hass
    account.uid = "86-13812345678"
    account.update_interval = timedelta(minutes=1)
    account.get_devices = AsyncMock(return_value=[])
    account.get_cats = AsyncMock(return_value=[])
    account.get_cat_summary_simple = AsyncMock(return_value={})
    account.get_cat_detail = AsyncMock(return_value={})
    return account


class TestDiscoverCatsFromDeviceLogs:
    """Tests for _discover_cats_from_device_logs method."""

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_discovers_cat_from_device_logs(
        self, mock_hass, mock_account
    ) -> None:
        """Test that cats are discovered from device logs."""
        coordinator = DevicesCoordinator(mock_account, "test_entry_id")
        mock_hass.data["catlink"]["devices"] = {}

        # Create a device with cat activity logs
        device_data = {
            "id": "c08-1",
            "mac": "01:23:45:67:89:AB",
            "model": "Open-X",
            "deviceName": "Bedroom C08",
            "deviceType": "C08",
        }
        device = C08Device(device_data, coordinator)
        device.logs = [
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
        ]
        mock_hass.data["catlink"]["devices"]["c08-1"] = device

        await coordinator._discover_cats_from_device_logs()

        # Should discover a cat
        assert "cat-548334" in mock_hass.data["catlink"]["devices"]
        cat_device = mock_hass.data["catlink"]["devices"]["cat-548334"]
        assert isinstance(cat_device, CatDevice)
        assert cat_device.discovered_name == "土豆🥔"

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_updates_existing_cat_from_logs(
        self, mock_hass, mock_account
    ) -> None:
        """Test that existing cat is updated from new logs."""
        coordinator = DevicesCoordinator(mock_account, "test_entry_id")
        mock_hass.data["catlink"]["devices"] = {}

        # Create existing cat device
        cat_data = {
            "id": "cat-548334",
            "pet_id": "548334",
            "petName": "土豆🥔",
            "deviceName": "土豆🥔",
            "deviceType": "CAT",
            "mac": "cat-548334",
        }
        existing_cat = CatDevice(cat_data, coordinator)
        await existing_cat.async_init()
        mock_hass.data["catlink"]["devices"]["cat-548334"] = existing_cat

        # Create a device with new activity
        device_data = {
            "id": "c08-1",
            "mac": "01:23:45:67:89:AB",
            "model": "Open-X",
            "deviceName": "Bedroom C08",
            "deviceType": "C08",
        }
        device = C08Device(device_data, coordinator)
        device.logs = [
            {
                "time": "11:30",
                "event": "土豆🥔 peed",
                "firstSection": "7.5kg",
                "secondSection": "60s",
                "id": "899877559",
                "type": "WC",
                "petId": "548334",
                "snFlag": 0,
            },
        ]
        mock_hass.data["catlink"]["devices"]["c08-1"] = device

        initial_count = existing_cat.local_pee_count
        await coordinator._discover_cats_from_device_logs()

        # Should update cat's count
        assert existing_cat.local_pee_count == initial_count + 1
