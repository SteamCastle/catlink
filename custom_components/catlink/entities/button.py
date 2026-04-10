"""Button entity for CatLink integration."""

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityDescription

from .base import CatlinkEntity


class CatlinkButtonEntity(CatlinkEntity, ButtonEntity):
    """Button entity for CatLink."""

    def __init__(
        self,
        description: EntityDescription,
        device,
        option=None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(description, device, option)

    async def async_press(self):
        """Press the button."""
        ret = False
        fun = self._option.get("async_press")
        if callable(fun):
            ret = await fun()
        return ret
