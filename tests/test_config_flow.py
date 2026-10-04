"""Config and options flow."""

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.audioengine_infrared.const import (
    CONF_INFRARED_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DOMAIN,
)


async def test_abort_without_emitters(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_infrared_entities"


async def test_user_flow_creates_entry(hass, ir):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Desk speakers", CONF_INFRARED_ENTITY_ID: "infrared.fake_emitter"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Desk speakers"
    assert result["data"] == {
        CONF_INFRARED_ENTITY_ID: "infrared.fake_emitter",
        CONF_INFRARED_RECEIVER_ENTITY_ID: None,
    }
    await hass.async_block_till_done()
    assert hass.states.get("media_player.desk_speakers") is not None


async def test_options_flow_adds_receiver(hass, ir):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Desk speakers",
        data={
            CONF_INFRARED_ENTITY_ID: "infrared.fake_emitter",
            CONF_INFRARED_RECEIVER_ENTITY_ID: None,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_INFRARED_ENTITY_ID: "infrared.fake_emitter",
            CONF_INFRARED_RECEIVER_ENTITY_ID: "infrared.fake_receiver",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[CONF_INFRARED_RECEIVER_ENTITY_ID] == "infrared.fake_receiver"
    assert hass.states.get("media_player.desk_speakers") is not None
