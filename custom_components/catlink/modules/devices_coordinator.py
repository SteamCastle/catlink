"""The component."""

import asyncio

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import CONF_DEVICES
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .account import Account
from ..const import _LOGGER, CONF_DEVICE_IDS, DOMAIN, SUPPORTED_DOMAINS
from ..devices.cat import CatDevice
from ..devices.registry import create_device
from ..entities.registry import DOMAIN_ENTITY_CLASSES
from ..models.additional_cfg import AdditionalDeviceConfig

ENTITY_DESCRIPTION_CLASSES: dict[str, type] = {
    "sensor": SensorEntityDescription,
    "binary_sensor": BinarySensorEntityDescription,
    "switch": SwitchEntityDescription,
    "select": SelectEntityDescription,
    "button": ButtonEntityDescription,
    "number": NumberEntityDescription,
}


class DevicesCoordinator(DataUpdateCoordinator):
    """Devices Coordinator for CatLink integration."""

    def __init__(
        self,
        account: "Account",
        config_entry_id: str,
        device_ids: list[str] | None = None,
    ) -> None:
        """Initialize the devices coordinator."""
        super().__init__(
            account.hass,
            _LOGGER,
            name=f"{DOMAIN}-{account.uid}-{CONF_DEVICES}",
            update_interval=account.update_interval,
        )
        self.account = account
        self.config_entry_id = config_entry_id
        self._subs = {}
        self._device_ids = device_ids
        self.additional_config = self.hass.data[DOMAIN]["config"].get(CONF_DEVICES, {})
        self.additional_config = [
            AdditionalDeviceConfig(**cfg) for cfg in self.additional_config
        ]

    async def _async_update_data(self) -> dict:
        """Update data via API."""
        dls = await self.account.get_devices()
        for dat in dls:
            did = dat.get("id")
            if not did:
                continue
            if self._device_ids is not None and did not in self._device_ids:
                _LOGGER.debug(
                    "Device %s (%s) skipped because it is not in configured device list",
                    dat.get("deviceName"),
                    did,
                )
                continue
            additional_config = next(
                (cfg for cfg in self.additional_config if cfg.mac == dat.get("mac")),
                None,
            )
            old = self.hass.data[DOMAIN][CONF_DEVICES].get(did)
            if old:
                dvc = old
                dvc.update_data(dat)
            else:
                dvc = create_device(dat, self, additional_config)
                self.hass.data[DOMAIN][CONF_DEVICES][did] = dvc
            await dvc.async_init()
            for d in SUPPORTED_DOMAINS:
                await self.update_hass_entities(d, dvc)
        cats = await self.account.get_cats(self.hass.config.time_zone)
        if cats:
            timezone_id = self.hass.config.time_zone
            date = dt_util.now().date().isoformat()
            requests = [
                self.account.get_cat_summary_simple(
                    cat.get("id"), date, timezone_id
                )
                for cat in cats
                if cat.get("id")
            ]
            summaries = (
                await asyncio.gather(*requests) if requests else []
            )
        else:
            summaries = []

        summary_map = {
            cat.get("id"): summary
            for cat, summary in zip(cats, summaries, strict=False)
            if cat.get("id")
        }
        for cat in cats:
            pet_id = cat.get("id")
            if not pet_id:
                continue
            cat_data = {**cat}
            cat_data["pet_id"] = pet_id
            cat_data["id"] = f"cat-{pet_id}"
            cat_data["mac"] = f"cat-{pet_id}"
            cat_data["deviceType"] = "CAT"
            cat_data["deviceName"] = cat_data.get("petName") or f"Cat {pet_id}"
            cat_data.setdefault("model", cat_data.get("breedName") or "Cat")
            cat_data["summary_simple"] = summary_map.get(pet_id, {})
            did = cat_data["id"]
            old = self.hass.data[DOMAIN][CONF_DEVICES].get(did)
            if old:
                dvc = old
                dvc.update_data(cat_data)
            else:
                dvc = create_device(cat_data, self, None)
                self.hass.data[DOMAIN][CONF_DEVICES][did] = dvc
            await dvc.async_init()
            for d in SUPPORTED_DOMAINS:
                await self.update_hass_entities(d, dvc)

        # Discover cats from device logs (cat activity logs)
        await self._discover_cats_from_device_logs()

        # Update cat details (avatar, etc.) from API
        await self._update_cat_details()

        return self.hass.data[DOMAIN][CONF_DEVICES]

    async def update_hass_entities(self, domain, dvc) -> None:
        """Update Home Assistant entities."""
        hdk = f"hass_{domain}"
        add_entities = self.hass.data[DOMAIN].get("add_entities", {})
        add = add_entities.get(self.config_entry_id, {}).get(domain)
        if not add or not hasattr(dvc, hdk):
            return
        added_entity_ids: list[str] = []
        entity_cls = DOMAIN_ENTITY_CLASSES.get(domain)
        desc_cls = ENTITY_DESCRIPTION_CLASSES.get(domain, EntityDescription)
        for k, cfg in getattr(dvc, hdk).items():
            key = f"{domain}.{k}.{dvc.id}"
            new = None
            if key in self._subs:
                pass
            elif entity_cls is not None:
                # Always use device-type prefixed translation_key to match translation files
                # Translation files use keys like "SCOOPER_state", "C08_temperature", etc.
                translation_key = f"{dvc.type}_{k}"

                # Build description with proper field names for each domain
                # Note: has_entity_name is set on the entity class, not here
                desc_kwargs = {
                    "key": k,
                    "translation_key": translation_key,
                    "icon": cfg.get("icon"),
                    "entity_category": cfg.get("category"),
                }
                # Map config keys to EntityDescription field names for sensors
                if domain == "sensor":
                    if cfg.get("class"):
                        desc_kwargs["device_class"] = cfg["class"]
                    if cfg.get("state_class"):
                        desc_kwargs["state_class"] = cfg["state_class"]
                    if cfg.get("unit"):
                        desc_kwargs["unit_of_measurement"] = cfg["unit"]
                description = desc_cls(**desc_kwargs)
                new = entity_cls(description, dvc, cfg)
            if new:
                self._subs[key] = new
                add([new])
                added_entity_ids.append(new.entity_id)
        if added_entity_ids:
            _LOGGER.info(
                "Device %s entities: %s",
                dvc.name,
                added_entity_ids,
            )

    async def _discover_cats_from_device_logs(self) -> None:
        """Discover cats from device logs and create/update CatDevice instances."""
        discovered_cats: dict[str, dict] = {}  # pet_id -> {activities, source_device}

        # Collect cat activities from all devices with logs
        for device in list(self.hass.data[DOMAIN][CONF_DEVICES].values()):
            if not hasattr(device, "get_cat_activities_from_logs"):
                continue
            activities = device.get_cat_activities_from_logs()
            for activity in activities:
                pet_id = activity["pet_id"]
                if pet_id not in discovered_cats:
                    discovered_cats[pet_id] = {
                        "activities": [],
                        "source_device": device.id,
                    }
                discovered_cats[pet_id]["activities"].append(activity)

        # Create or update cat devices
        for pet_id, data in discovered_cats.items():
            cat_device_id = f"cat-{pet_id}"

            # Sort activities by time (newest first)
            activities = sorted(
                data["activities"],
                key=lambda x: x.get("time", ""),
                reverse=True,
            )

            existing = self.hass.data[DOMAIN][CONF_DEVICES].get(cat_device_id)
            if existing:
                # Update existing cat - process all activities
                for activity in activities:
                    existing.update_from_activity(activity)
            else:
                # Create new cat - use latest activity for initialization
                latest_activity = activities[0] if activities else None
                if not latest_activity:
                    continue

                cat_data = {
                    "id": cat_device_id,
                    "pet_id": pet_id,
                    "petName": latest_activity.get("name"),
                    "weight": latest_activity.get("weight"),
                    "deviceType": "CAT",
                    "mac": f"cat-{pet_id}",
                    "model": "Cat",
                    "deviceName": latest_activity.get("name") or f"Cat {pet_id}",
                }
                cat_device = create_device(cat_data, self, None)
                cat_device._source_device_id = data["source_device"]
                # Process all activities
                for activity in activities:
                    cat_device.update_from_activity(activity)
                self.hass.data[DOMAIN][CONF_DEVICES][cat_device_id] = cat_device
                await cat_device.async_init()
                for d in SUPPORTED_DOMAINS:
                    await self.update_hass_entities(d, cat_device)

    async def _update_cat_details(self) -> None:
        """Update cat details (avatar, etc.) from API."""
        for device in list(self.hass.data[DOMAIN][CONF_DEVICES].values()):
            if not isinstance(device, CatDevice):
                continue
            if device.avatar_url:  # Skip if already has avatar
                continue

            pet_id = device.pet_id
            if not pet_id:
                continue

            try:
                detail = await self.account.get_cat_detail(pet_id)
                if detail:
                    if detail.get("avatar"):
                        device.data["avatar"] = detail["avatar"]
                    if detail.get("petName") and not device.discovered_name:
                        device.data["petName"] = detail["petName"]
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Failed to update cat details for %s", pet_id)

