"""Audioengine A5+ remote codes (NEC extended, 38 kHz).

The A5+ remote has four keys. Every key is a single 32-bit NEC frame with the
16-bit address ``0xFD00`` (sent as bytes ``00 FD``) followed by the command and
its complement::

    Sleep        00 FD 01 FE
    Mute         00 FD 03 FC
    Volume down  00 FD 07 F8
    Volume up    00 FD 09 F6

Codes are from Flipper-IRDB (``Speakers/Audioengine/Audioengine_a5.ir``, parsed
NECext) and agree bit-for-bit with the independent raw capture in
``_Converted_/IR_Plus/A/AUDIOENGINE/A5+.ir``.

Sleep and Mute are toggles: the speaker has no discrete on/off or mute/unmute
codes.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import IntEnum

from infrared_protocols.commands.nec import NECCommand

ADDRESS = 0xFD00


class AudioengineKey(IntEnum):
    """Keys of the A5+ remote (NEC command byte)."""

    SLEEP = 0x01
    MUTE = 0x03
    VOLUME_DOWN = 0x07
    VOLUME_UP = 0x09

    def to_command(self) -> NECCommand:
        """Build the NEC frame for this key."""
        return NECCommand(address=ADDRESS, command=self.value)

    @classmethod
    def from_raw_timings(cls, timings: Sequence[int]) -> AudioengineKey | None:
        """Decode raw timings (signed or unsigned) into a key, or None.

        NEC repeat frames (a held key) carry no data and decode to None.
        """
        signed = [
            abs(int(t)) if i % 2 == 0 else -abs(int(t)) for i, t in enumerate(timings)
        ]
        command = NECCommand.from_raw_timings(signed)
        if command is None or command.address != ADDRESS:
            return None
        try:
            return cls(command.command)
        except ValueError:
            return None
