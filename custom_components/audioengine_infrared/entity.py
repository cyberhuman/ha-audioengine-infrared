"""Common base entity for Audioengine Infrared."""

from __future__ import annotations

from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_INFRARED_ENTITY_ID, DOMAIN
from .protocol import AudioengineKey


class AudioengineEntity(InfraredEmitterConsumerEntity):
    """Entity of the speaker device that can press remote keys."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, unique_id_suffix: str) -> None:
        """Initialise from the merged entry data/options."""
        config = {**entry.data, **entry.options}
        self._infrared_emitter_entity_id: str = config[CONF_INFRARED_ENTITY_ID]
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Audioengine",
            model="A5+",
        )

    async def _press(self, key: AudioengineKey) -> None:
        """Send one key press."""
        await self._send_command(key.to_command())
