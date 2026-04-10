"""Sensor entity for CatLink integration."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityDescription

from ..const import _LOGGER
from .base import CatlinkEntity


class CatlinkSensorEntity(CatlinkEntity, SensorEntity):
    """Sensor entity for CatLink."""

    def __init__(
        self,
        description: EntityDescription,
        device,
        option=None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(description, device, option)

    def update(self) -> None:
        """Update the entity."""
        # Get state from device property matching the entity key
        state = None
        if hasattr(self._device, self.entity_description.key):
            state = getattr(self._device, self.entity_description.key)
        # Use _attr_native_value for SensorEntity
        self._attr_native_value = state
        self._attr_state = state
        _LOGGER.debug(
            "Sensor entity update: %s.%s = %s",
            self.entity_id,
            self.entity_description.key,
            self._attr_native_value,
        )
        entity_picture = self._option.get("entity_picture")
        if callable(entity_picture):
            self._attr_entity_picture = entity_picture()

        fun = self._option.get("state_attrs")
        if callable(fun):
            self._attr_extra_state_attributes = fun()
