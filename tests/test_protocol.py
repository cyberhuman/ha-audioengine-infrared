"""Key frames against the Flipper-IRDB raw capture of the A5+ remote."""

import pytest
from infrared_protocols.commands.nec import NECCommand

from custom_components.audioengine_infrared.protocol import ADDRESS, AudioengineKey

_HEAD = "9041 4507 " + "573 573 " * 8 + "573 1694 573 573 " + "573 1694 " * 6


def _raw(command_bits: str) -> list[int]:
    """IR_Plus-style capture: header, address 00 FD, command + complement, gap."""
    bits = command_bits + "".join("1" if b == "0" else "0" for b in command_bits)
    body = "".join("573 1694 " if b == "1" else "573 573 " for b in bits)
    return [int(t) for t in (_HEAD + body + "573 40906").split()]


# Command bits LSB first, as they appear in _Converted_/IR_Plus/A/AUDIOENGINE/A5+.ir
CAPTURES = {
    AudioengineKey.SLEEP: _raw("10000000"),
    AudioengineKey.MUTE: _raw("11000000"),
    AudioengineKey.VOLUME_UP: _raw("10010000"),
    AudioengineKey.VOLUME_DOWN: _raw("11100000"),
}

# The VOL+ line of that file, verbatim, to keep _raw() honest.
VOL_UP_VERBATIM = (
    "9041 4507 573 573 573 573 573 573 573 573 573 573 573 573 573 573 573 573 "
    "573 1694 573 573 573 1694 573 1694 573 1694 573 1694 573 1694 573 1694 "
    "573 1694 573 573 573 573 573 1694 573 573 573 573 573 573 573 573 "
    "573 573 573 1694 573 1694 573 573 573 1694 573 1694 573 1694 573 1694 573 40906"
)


def test_raw_helper_matches_verbatim_capture():
    assert CAPTURES[AudioengineKey.VOLUME_UP] == [int(t) for t in VOL_UP_VERBATIM.split()]


@pytest.mark.parametrize("key", list(AudioengineKey))
def test_decodes_capture(key):
    assert AudioengineKey.from_raw_timings(CAPTURES[key]) is key


@pytest.mark.parametrize("key", list(AudioengineKey))
def test_encoding_matches_capture_bits(key):
    """Our frame carries the same 32 bits as the capture (space length = bit)."""
    sent = key.to_command().get_raw_timings()
    capture = CAPTURES[key]
    assert len(sent) == 67  # leader pair, 32 bit pairs, end pulse; no repeats
    assert [s < -1000 for s in sent[3:66:2]] == [c > 1000 for c in capture[3:66:2]]
    assert key.to_command().modulation == 38000


@pytest.mark.parametrize("key", list(AudioengineKey))
def test_round_trip(key):
    assert AudioengineKey.from_raw_timings(key.to_command().get_raw_timings()) is key


def test_foreign_signals_are_ignored():
    other_address = NECCommand(address=0xE710, command=0x01).get_raw_timings()
    unknown_key = NECCommand(address=ADDRESS, command=0x55).get_raw_timings()
    nec_repeat = [9000, -2250, 562]
    for timings in (other_address, unknown_key, nec_repeat, [], [500, -500] * 40):
        assert AudioengineKey.from_raw_timings(timings) is None
