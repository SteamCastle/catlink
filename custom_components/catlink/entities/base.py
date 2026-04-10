"""The component."""

import asyncio

from homeassistant.components import persistent_notification
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from ..const import _LOGGER, DOMAIN
from ..devices.base import Device


class CatlinkEntity(CoordinatorEntity):
    """Base Catlink entity using EntityDescription pattern."""

    _attr_has_entity_name = True

    def __init__(
        self,
        description: EntityDescription,
        device: Device,
        option=None,
    ) -> None:
        """Initialize the entity."""
        self.coordinator = device.coordinator
        CoordinatorEntity.__init__(self, self.coordinator)
        self.account = self.coordinator.account
        self.entity_description = description
        self._device = device
        self._option = option or {}
        # Device identifier
        self._attr_device_id = f"{device.type}_{device.mac}"
        mac = device.mac[-4:] if device.mac else device.id
        object_id = f"{device.type}_{mac}_{description.key}"
        self.entity_id = f"{DOMAIN}.{slugify(object_id)}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_device_id)},
            name=device.name,
            model=device.model,
            manufacturer="CatLink",
            sw_version=device.detail.get("firmwareVersion"),
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._device.listeners[self.entity_id] = self._handle_coordinator_update
        self._handle_coordinator_update()

    def _handle_coordinator_update(self):
        self.update()
        self.async_write_ha_state()

    async def _async_after_action(self, success: bool, delay: float | None = None) -> None:
        """Run after an action: write state, optional delay, then coordinator refresh."""
        if success:
            self.async_write_ha_state()
            if delay is not None:
                await asyncio.sleep(delay)
            self._handle_coordinator_update()

    def update(self) -> None:
        """Update the entity."""
        if hasattr(self._device, self.entity_description.key):
            self._attr_state = getattr(self._device, self.entity_description.key)
            _LOGGER.debug(
                "Entity update: %s", [self.entity_id, self.entity_description.key, self._attr_state]
            )
        entity_picture = self._option.get("entity_picture")
        if callable(entity_picture):
            self._attr_entity_picture = entity_picture()

        fun = self._option.get("state_attrs")
        if callable(fun):
            self._attr_extra_state_attributes = fun()

    @property
    def state(self) -> str:
        """Return the state of the entity."""
        return self._attr_state

    async def async_request_api(self, api, params=None, method="GET", **kwargs) -> dict:
        """Request API."""
        throw = kwargs.pop("throw", None)
        rdt = await self.account.request(api, params, method, **kwargs)
        if throw:
            persistent_notification.async_create(
                self.hass,
                f"{rdt}",
                f"Request: {api}",
                f"{DOMAIN}-request",
            )
        return rdt
