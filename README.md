# Audioengine Infrared

Home Assistant integration for Audioengine A5+ powered speakers, sent through a
native `infrared` emitter entity (for example a Broadlink RM4).

- HACS custom repository
- Config flow, one device per speaker pair
- `media_player` entity: on/off (Sleep), volume up/down, mute
- `button` entities for the four remote keys: Sleep, Mute, Volume up, Volume down
- Optional infrared receiver to follow the physical remote
- Assumed state, restored across restarts

## Requirements

- Home Assistant 2026.9 or newer
- An `infrared.*` emitter entity pointing at the left (powered) speaker

## Install

1. HACS → Integrations → ⋮ → Custom repositories → add this repo as *Integration*
2. Download, restart Home Assistant
3. Settings → Devices & services → Add integration → **Audioengine Infrared**

The emitter and receiver can be changed later via *Configure*.

## Assumed state

The remote only has toggles for Sleep and Mute, so the media player tracks what
it believes the speaker is doing and presses a toggle only when that differs
from what was asked.

- If the state drifts (someone used the remote and no receiver is configured),
  press the **Sleep** or **Mute** button entity: buttons send the raw key and do
  not change the media player's state
- With a receiver, Sleep and Mute presses on the physical remote flip the state
- Received keys are ignored for 1 s after a send, so a receiver that hears the
  emitter does not count a toggle twice
- Volume is relative; there is no volume level

## Protocol

NEC extended, 38 kHz, address `0xFD00`, one 32-bit frame per key press.

| Key         | Command | Frame bytes   |
|-------------|---------|---------------|
| Sleep       | `0x01`  | `00 FD 01 FE` |
| Mute        | `0x03`  | `00 FD 03 FC` |
| Volume down | `0x07`  | `00 FD 07 F8` |
| Volume up   | `0x09`  | `00 FD 09 F6` |

- Source: [Flipper-IRDB](https://github.com/Lucaslhm/Flipper-IRDB)
  `Speakers/Audioengine/Audioengine_a5.ir`, cross-checked against the raw
  capture in `_Converted_/IR_Plus/A/AUDIOENGINE/A5+.ir`
- Not yet tried against real speakers

## Development

```sh
python -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```
