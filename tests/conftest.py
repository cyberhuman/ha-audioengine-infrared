"""Test fixtures: importable repo root, custom integrations enabled, fake IR devices."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.components.infrared import (  # noqa: E402
    InfraredCommand,
    InfraredEmitterEntity,
    InfraredReceivedSignal,
    InfraredReceiverEntity,
)
from homeassistant.components.infrared.const import DATA_COMPONENT  # noqa: E402
from homeassistant.setup import async_setup_component  # noqa: E402


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components from the repo."""
    return


class FakeEmitter(InfraredEmitterEntity):
    """Records every command it is asked to send."""

    _attr_has_entity_name = True
    _attr_name = "Fake emitter"
    _attr_unique_id = "fake-emitter"

    def __init__(self) -> None:
        self.sent: list[InfraredCommand] = []

    async def async_send_command(self, command: InfraredCommand) -> None:
        self.sent.append(command)


class FakeReceiver(InfraredReceiverEntity):
    """Lets a test inject a received burst."""

    _attr_has_entity_name = True
    _attr_name = "Fake receiver"
    _attr_unique_id = "fake-receiver"

    def inject(self, timings: list[int]) -> None:
        self._handle_received_signal(InfraredReceivedSignal(timings=timings))


@pytest.fixture
async def ir(hass):
    """Set up the infrared domain with one fake emitter and one fake receiver."""
    assert await async_setup_component(hass, "infrared", {})
    emitter, receiver = FakeEmitter(), FakeReceiver()
    await hass.data[DATA_COMPONENT].async_add_entities([emitter, receiver])
    await hass.async_block_till_done()
    assert emitter.entity_id == "infrared.fake_emitter"
    assert receiver.entity_id == "infrared.fake_receiver"
    return emitter, receiver
