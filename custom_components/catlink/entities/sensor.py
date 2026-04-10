"""Sensor entity for CatLink integration."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityDescription

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
