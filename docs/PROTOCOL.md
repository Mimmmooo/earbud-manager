# CMF Buds 2 protocol notes

This is a community reverse-engineered description, not an official protocol specification. NTAPP runs over Bluetooth RFCOMM (channel 16 in the tested setup). Supported behavior may change by firmware version.

## Commands used

| Function | Request/SET | Expected response or verification |
| --- | --- | --- |
| Battery | GET `0xC007` | battery response; left/right/case when available |
| ANC status | GET `0xC01E` | ANC state |
| ANC set | SET `0xF00F` | read back via `0xC01E` |
| Low latency status | GET `0xC041` | `01` ON / `02` OFF |
| Low latency set | SET `0xF040` | read back via `0xC041` |
| Dual Connection status | GET `0xC027` | `0x4027`, `01` ON / `00` OFF |
| Dual Connection set | SET `0xF01A` | `0x701A` acknowledgement and read-back via `0xC027` |
| Dual device list | GET `0xC028` with page offset | `0x4028` per-page data |
| Find left/right | SET `0xF002` | command-level acknowledgement; auditory effect firmware-dependent |

**Not enabled:** Device switching uses an unverified command and is not accessible in this application.

## Why controls may pause

Each command establishes an RFCOMM session and waits for firmware read-back. The desktop interface is updated independently of those operations, but on-device acknowledgement still has physical network cost. Settings are verified before the UI reports success.

## Reporting protocol issues safely

Include model, firmware version (if known), OS, intended command, and an anonymized error description. **Never paste raw connection logs with Bluetooth MAC addresses or paired-device names into public issues.**
