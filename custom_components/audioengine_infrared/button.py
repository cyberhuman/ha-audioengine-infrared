"""Button entities: one per key of the A5+ remote.

These send the raw key and leave the media player's assumed state alone, so the
Sleep and Mute buttons double as the way to bring the speaker back in line when
the assumed state has drifted.
"""

from __future__ import annotations

from typing import override

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import AudioengineEntity
from .protocol import AudioengineKey

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one button per remote key."""
    async_add_entities(AudioengineButton(entry, key) for key in AudioengineKey)


class AudioengineButton(AudioengineEntity, ButtonEntity):
    """One remote key."""

    def __init__(self, entry: ConfigEntry, key: AudioengineKey) -> None:
        """Initialise the button for one key."""
        super().__init__(entry, key.name.lower())
        self._key = key
        self._attr_translation_key = key.name.lower()

    @override
    async def async_press(self) -> None:
        """Send the key."""
        await self._press(self._key)
