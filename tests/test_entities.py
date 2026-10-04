"""Entity behaviour: services press the right keys, toggles are tracked."""

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MP_DOMAIN,
    SERVICE_VOLUME_MUTE,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_UP,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from custom_components.audioengine_infrared import media_player
from custom_components.audioengine_infrared.const import (
    CONF_INFRARED_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DOMAIN,
)
from custom_components.audioengine_infrared.protocol import AudioengineKey

ENTITY = "media_player.speakers"


async def _setup(hass, receiver=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Speakers",
        data={
            CONF_INFRARED_ENTITY_ID: "infrared.fake_emitter",
            CONF_INFRARED_RECEIVER_ENTITY_ID: receiver,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY) is not None
    return entry


async def _call(hass, service, domain=MP_DOMAIN, entity_id=ENTITY, **data):
    await hass.services.async_call(
        domain, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )
    await hass.async_block_till_done()


def _keys(emitter):
    return [AudioengineKey.from_raw_timings(c.get_raw_timings()) for c in emitter.sent]


async def test_volume_and_mute(hass, ir):
    emitter, _ = ir
    await _setup(hass)
    state = hass.states.get(ENTITY)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_MEDIA_VOLUME_MUTED] is False

    await _call(hass, SERVICE_VOLUME_UP)
    await _call(hass, SERVICE_VOLUME_DOWN)
    await _call(hass, SERVICE_VOLUME_MUTE, **{ATTR_MEDIA_VOLUME_MUTED: True})
    assert hass.states.get(ENTITY).attributes[ATTR_MEDIA_VOLUME_MUTED] is True
    # Already muted: the toggle is not pressed again.
    await _call(hass, SERVICE_VOLUME_MUTE, **{ATTR_MEDIA_VOLUME_MUTED: True})
    await _call(hass, SERVICE_VOLUME_MUTE, **{ATTR_MEDIA_VOLUME_MUTED: False})
    assert hass.states.get(ENTITY).attributes[ATTR_MEDIA_VOLUME_MUTED] is False
    assert _keys(emitter) == [
        AudioengineKey.VOLUME_UP,
        AudioengineKey.VOLUME_DOWN,
        AudioengineKey.MUTE,
        AudioengineKey.MUTE,
    ]


async def test_power_is_a_tracked_toggle(hass, ir):
    emitter, _ = ir
    await _setup(hass)
    await _call(hass, SERVICE_TURN_ON)  # assumed on already: nothing sent
    assert emitter.sent == []
    await _call(hass, SERVICE_TURN_OFF)
    assert hass.states.get(ENTITY).state == STATE_OFF
    await _call(hass, SERVICE_TURN_OFF)
    await _call(hass, SERVICE_TURN_ON)
    assert hass.states.get(ENTITY).state == STATE_ON
    assert _keys(emitter) == [AudioengineKey.SLEEP, AudioengineKey.SLEEP]


async def test_buttons_send_raw_keys_without_touching_state(hass, ir):
    emitter, _ = ir
    await _setup(hass)
    for name in ("sleep", "mute", "volume_down", "volume_up"):
        await _call(hass, SERVICE_PRESS, BUTTON_DOMAIN, f"button.speakers_{name}")
    assert _keys(emitter) == [
        AudioengineKey.SLEEP,
        AudioengineKey.MUTE,
        AudioengineKey.VOLUME_DOWN,
        AudioengineKey.VOLUME_UP,
    ]
    state = hass.states.get(ENTITY)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_MEDIA_VOLUME_MUTED] is False


async def test_restores_state(hass, ir):
    mock_restore_cache(hass, [State(ENTITY, STATE_OFF)])
    await _setup(hass)
    assert hass.states.get(ENTITY).state == STATE_OFF


async def test_restores_mute(hass, ir):
    mock_restore_cache(hass, [State(ENTITY, STATE_ON, {ATTR_MEDIA_VOLUME_MUTED: True})])
    await _setup(hass)
    assert hass.states.get(ENTITY).attributes[ATTR_MEDIA_VOLUME_MUTED] is True


async def test_receiver_follows_physical_remote(hass, ir):
    emitter, receiver = ir
    await _setup(hass, receiver="infrared.fake_receiver")

    receiver.inject(AudioengineKey.MUTE.to_command().get_raw_timings())
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).attributes[ATTR_MEDIA_VOLUME_MUTED] is True

    receiver.inject(AudioengineKey.SLEEP.to_command().get_raw_timings())
    receiver.inject(AudioengineKey.VOLUME_UP.to_command().get_raw_timings())
    receiver.inject([9000, 2250, 562])  # held-key repeat frame
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == STATE_OFF
    assert emitter.sent == []


async def test_receiver_ignores_echo_of_own_send(hass, ir, monkeypatch):
    _, receiver = ir
    await _setup(hass, receiver="infrared.fake_receiver")
    now = 1000.0
    monkeypatch.setattr(media_player.time, "monotonic", lambda: now)

    await _call(hass, SERVICE_TURN_OFF)
    receiver.inject(AudioengineKey.SLEEP.to_command().get_raw_timings())
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == STATE_OFF

    now += 5
    receiver.inject(AudioengineKey.SLEEP.to_command().get_raw_timings())
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == STATE_ON


async def test_unavailable_when_emitter_is(hass, ir):
    await _setup(hass)
    hass.states.async_set("infrared.fake_emitter", STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == STATE_UNAVAILABLE
