"""Number entities for CatLink integration."""

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.entity import EntityDescription

from ..devices.base import Device
from .base import CatlinkEntity


class CatlinkNumberEntity(CatlinkEntity, NumberEntity):
    """Number entity for CatLink."""

    def __init__(
        self,
        description: EntityDescription,
        device: Device,
        option=None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(description, device, option)
        self._attr_native_min_value = self._option.get("min", 0)
        self._attr_native_max_value = self._option.get("max", 100)
        self._attr_native_step = self._option.get("step", 1)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if hasattr(self._device, self.entity_description.key):
            setattr(self._device, self.entity_description.key, int(value))
            self.async_write_ha_state()
