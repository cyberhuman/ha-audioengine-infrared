"""Media player entity for an Audioengine A5+ driven through an infrared emitter."""

from __future__ import annotations

import logging
import time
from typing import override

from homeassistant.components.infrared import (
    InfraredReceivedSignal,
    InfraredReceiverConsumerEntity,
)
from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_MUTED,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_INFRARED_RECEIVER_ENTITY_ID
from .entity import AudioengineEntity
from .protocol import AudioengineKey

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

# A receiver next to the emitter may hear our own transmission; received keys
# are ignored for this long after a send so toggles are not counted twice.
_ECHO_WINDOW = 1.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the media player entity from a config entry."""
    config = {**entry.data, **entry.options}
    if receiver := config.get(CONF_INFRARED_RECEIVER_ENTITY_ID):
        async_add_entities([AudioengineMediaPlayerWithReceiver(entry, receiver)])
    else:
        async_add_entities([AudioengineMediaPlayer(entry)])


class AudioengineMediaPlayer(AudioengineEntity, MediaPlayerEntity, RestoreEntity):
    """Assumed-state speaker: Sleep and Mute are toggles, volume is relative."""

    _attr_name = None
    _attr_assumed_state = True
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
    )

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialise as on and unmuted."""
        super().__init__(entry, "media_player")
        self._attr_state = MediaPlayerState.ON
        self._attr_is_volume_muted = False
        self._last_sent = 0.0

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the assumed power and mute state."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None or last.state not in (STATE_ON, STATE_OFF):
            return
        self._attr_state = MediaPlayerState(last.state)
        self._attr_is_volume_muted = bool(last.attributes.get(ATTR_MEDIA_VOLUME_MUTED))

    @override
    async def _press(self, key: AudioengineKey) -> None:
        await super()._press(key)
        self._last_sent = time.monotonic()

    async def _async_set_power(self, state: MediaPlayerState) -> None:
        """Press Sleep only if the assumed state differs (it is a toggle)."""
        if self._attr_state != state:
            await self._press(AudioengineKey.SLEEP)
            self._attr_state = state
        self.async_write_ha_state()

    @override
    async def async_turn_on(self) -> None:
        """Wake the speaker."""
        await self._async_set_power(MediaPlayerState.ON)

    @override
    async def async_turn_off(self) -> None:
        """Put the speaker to sleep."""
        await self._async_set_power(MediaPlayerState.OFF)

    @override
    async def async_volume_up(self) -> None:
        """Step the volume up."""
        await self._press(AudioengineKey.VOLUME_UP)

    @override
    async def async_volume_down(self) -> None:
        """Step the volume down."""
        await self._press(AudioengineKey.VOLUME_DOWN)

    @override
    async def async_mute_volume(self, mute: bool) -> None:
        """Press Mute only if the assumed state differs (it is a toggle)."""
        if self._attr_is_volume_muted != mute:
            await self._press(AudioengineKey.MUTE)
            self._attr_is_volume_muted = mute
        self.async_write_ha_state()

    # ---- receiver sync ----------------------------------------------------

    @callback
    def _apply_received(self, key: AudioengineKey) -> None:
        """Mirror a key pressed on the physical remote into the assumed state."""
        if time.monotonic() - self._last_sent < _ECHO_WINDOW:
            _LOGGER.debug("%s: ignoring echo of %s", self.entity_id, key.name)
            return
        if key is AudioengineKey.SLEEP:
            self._attr_state = (
                MediaPlayerState.OFF
                if self._attr_state == MediaPlayerState.ON
                else MediaPlayerState.ON
            )
        elif key is AudioengineKey.MUTE:
            self._attr_is_volume_muted = not self._attr_is_volume_muted
        else:
            return
        self.async_write_ha_state()


class AudioengineMediaPlayerWithReceiver(
    AudioengineMediaPlayer, InfraredReceiverConsumerEntity
):
    """Media player that also listens to an infrared receiver."""

    def __init__(self, entry: ConfigEntry, receiver_entity_id: str) -> None:
        """Initialise with a receiver entity."""
        super().__init__(entry)
        self._infrared_receiver_entity_id: str = receiver_entity_id

    @override
    @callback
    def _handle_signal(self, signal: InfraredReceivedSignal) -> None:
        """Decode a received burst and, if it is an A5+ key, follow it."""
        key = AudioengineKey.from_raw_timings(signal.timings)
        if key is not None:
            self._apply_received(key)
