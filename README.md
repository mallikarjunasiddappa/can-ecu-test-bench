# CAN ECU Test Bench — pytest automation

Self-built home lab for **automotive CAN ECU testing**: a real 3-node CAN bus, two Arduino-based ECUs,
and a **pytest + python-can + pyserial** framework that tests the "Dashboard ECU" against written
requirements (REQ-001 … REQ-012) — including fault injection, end-to-end (E2E) protection checks,
timing measurements and defect retests.

> Personal learning project (self-driven, 2026). No commercial tools: no Vector CANoe/CANalyzer/CAPL —
> everything here is open source (python-can, pytest) on low-cost hardware.

---

## The bench

```
 PC (Windows, Python 3.13, pytest)
   │ USB                      │ USB serial (115200)
   ▼                          ▼
 CANable 2.0 (slcan)     Arduino Uno + MCP2515 #2  "Dashboard ECU"  ← device under test
   │                          │
 ══╪══════════ CAN bus 500 kbit/s, twisted pair, 2 × 120 Ω (measured 59.7 Ω) ══════════
                              │
                         Arduino Uno + MCP2515 #1  "Sender ECU" (VehicleSpeed 0x123, 100 ms)
```

| Node | Hardware | Role |
|---|---|---|
| Test node | CANable 2.0 USB-CAN (slcan) | Python sender / bus observer / fault injector |
| Sender ECU | Arduino Uno + MCP2515 (TJA1050, 8 MHz) | Sends 0x123 VehicleSpeed every 100 ms |
| Dashboard ECU | Arduino Uno + MCP2515 | Decodes speed, detects timeout / invalid value / E2E errors, prints state on serial |

Firmware for both ECUs is in [`firmware/`](firmware/) (Arduino IDE 2.3, library `mcp_can` by coryjfowler).
`dashboard_ecu.ino` carries its version history v0.1 → v0.5 in the header; each version was driven by a
requirement or a defect found by these tests.

## Message under test — 0x123 VehicleSpeed (11-bit ID, DLC 8)

| Byte | Signal | Rule |
|---|---|---|
| 0 | Alive counter | 0..15, +1 per frame, 15 → 0 (REQ-011) |
| 1 | Vehicle speed | km/h, factor 1; 0–250 valid, 251–253 out of range, 0xFE error, 0xFF not available (REQ-003, REQ-010) |
| 2–6 | — | 0x00 |
| 7 | Checksum | (byte 0 + … + byte 6) & 0xFF (REQ-012) |

Example: `05 32 00 00 00 00 00 37` = counter 5, 50 km/h.

## Requirements tested

| Req | Requirement (short) |
|---|---|
| REQ-001 | 0x123, standard 11-bit ID, DLC 8 |
| REQ-002 | Cycle time 100 ms ± 10 % |
| REQ-003 | Byte 1 = speed in km/h |
| REQ-004 | First 0x123 within 2 s after power-up |
| REQ-007 | No 0x123 for > 300 ms → SIGNAL LOST; recovery → RESTORED |
| REQ-010 | Speed validity: > 250 → INVALID, never shown as a number |
| REQ-011 | Alive counter checked by the receiver |
| REQ-012 | Checksum checked by the receiver |

(REQ-005 bitrate, REQ-006 termination, REQ-008 .asc logging and REQ-009 wiring faults are bench /
manual checks and not part of this code.)

## Framework

| File | Purpose |
|---|---|
| `config.py` | All bench settings in one place (ports, bitrate, IDs, timing limits, expected ECU version) |
| `conftest.py` | Fixtures: `dashboard` (serial port, handles Arduino auto-reset, captures boot banner) and `can_bus` (python-can slcan bus) with clean teardown |
| `vehicle.dbc` | DBC for the bench network: nodes, message 0x123 `VehicleSpeed_Msg` (AliveCounter, VehicleSpeed 0–250 km/h, Checksum) and named values 254 `Error` / 255 `NotAvailable` |
| `frames.py` | Builds valid 0x123 frames: `checksum()`, `speed_frame(speed, counter)`, `speed_frames(speed)` → 16 frames for `send_periodic`; `speed_frame_dbc(speed, counter, strict=True)` builds the same frame from `vehicle.dbc` by signal name (`strict=False` for fault injection, e.g. speed 251) |
| `requirements.txt` | Pinned versions: pytest 9.1.1, pytest-html 4.2.0, pyserial 3.5, python-can 4.6.1 |

## Tests

**`tests/` — regression suite (15 files, 53 test items + 1 long run)**

| File | TC | What it proves |
|---|---|---|
| `test_smoke.py` | — | Dashboard boots with the expected firmware version |
| `test_python_sender.py` | — | Python-sent 100 km/h is displayed |
| `test_tc13_timeout.py` | TC-13 | Exactly one LOST at 300–350 ms, no stale speed, RESTORED |
| `test_speed_values.py` | TC-14 | Boundary values 0, 1, 50, 100, 249, 250 displayed (parametrized) |
| `test_speed_invalid.py` | TC-15 | 251, 253, 0xFE, 0xFF → INVALID, no number shown |
| `test_frames_helper.py` | — | Tests the test tool itself on a virtual bus (no hardware) |
| `test_frames_dbc.py` | — | Equivalence test, no hardware: DBC-built frames == hand-built frames for 7 speeds × 4 counters (28 cases). Red check with a wrong start bit in the DBC → 24 failed (speed 0 cannot reveal a wrong position) |
| `test_two_senders.py` | TC-16 | 0x123 timing unaffected by a second ID on the bus |
| `test_sender_e2e.py` | TC-19 | Sender ECU conformance: checksum, counter, rollover |
| `test_duplicate_id.py` | TC-20 | A fake second sender of 0x123 is never displayed |
| `test_bad_checksum.py` | TC-21 | Damaged checksums rejected → LOST → recovery |
| `test_stuck_counter.py` | TC-22 | Frozen alive counter detected → LOST → resync |
| `test_single_corrupt.py` | TC-23 | One damaged frame must NOT cause a false LOST |
| `test_single_corrupt_long.py` | TC-23 long | Same over 160 s / 100 damaged frames (found DEF-003) |
| `test_e2e_tolerance_v05.py` | TC-24..26 | Two damaged in a row; damaged + fake sender (wrong / "lucky" counter) |

**`learning/test_round2_*.py` — tests written from the requirement text only (8 files, 13 items)**

| File | Req | What it proves |
|---|---|---|
| `test_round2_timeout.py` | REQ-007 | LOST reaction time within limits (measured 301 ms) |
| `test_round2_recovery.py` | REQ-007, REQ-011 | RESTORED only after 2 good frames; recovery time vs measured gap |
| `test_round2_checksum.py` | REQ-012 | Only damaged frames → every one rejected, LOST once |
| `test_round2_counter.py` | REQ-011 | Skipped counter → COUNTER ERROR, isolated, display recovers |
| `test_round2_speed_change.py` | REQ-003 | 50 → 100 km/h change shown at once, no false errors (TC-04) |
| `test_round2_speed_boundary.py` | REQ-010 | 249/250 valid vs 251/253/0xFE/0xFF invalid, exact expected line |
| `test_round2_cycle_time.py` | REQ-002 | Every gap 90–110 ms, average drift check (measured 99.3–102.5 ms) |
| `test_round2_startup.py` | REQ-004 | First frame after reset ≤ 2 s (measured 1.503 s, TC-05) |

Every test was checked **green → red → green**: after it passed, the limit or the stimulus was broken on
purpose to prove the test can fail with a clear message, then restored.

## Results so far

- 26 test cases in the test-case workbook: **19 Pass, 0 Fail, 7 Not Run** (wiring-fault, .asc logging and bus-side checks still to do).
- Last regressions on Dashboard v0.5: Setup A **17 passed**, Setup B **5 passed**.
- **3 product defects found by these tests and closed after retest:**
  - **DEF-001** — no timeout detection, stale speed stayed on screen → fixed in v0.2.
  - **DEF-002** — 0xFB–0xFF shown as real speeds → range check in v0.3.
  - **DEF-003** — one damaged frame caused a false SIGNAL LOST in ~2 % of cases (found only by the
    160 s long run) → requirement REQ-011 revised (v3) → v0.5 → long run 0/100.
- **Open observation OBS-002:** E2E (counter + checksum) is a *safety* mechanism, not *security* — a
  sender that mimics the next counter is accepted for one frame. Mitigation would be SecOC / an IDS rule.
- Requirement gaps raised during test design: REQ-003 has no response time (test uses an assumption),
  REQ-004 "power-up" — reset via USB is not a true power cycle.

## How to run

```bash
pip install -r requirements.txt
# edit config.py: CAN_CHANNEL (CANable) and DASHBOARD_PORT (Dashboard Arduino)
python -m pytest tests/test_smoke.py -v                    # bench check
python -m pytest tests -v -s                               # regression (see setups below)
python -m pytest learning/test_round2_timeout.py -v -s     # one round 2 test
python -m pytest tests -v --html=reports/report.html       # HTML report
```

Two bench setups (chosen by hand — no pytest markers yet):

| Setup | Sender ECU | Used by |
|---|---|---|
| A | OFF — Python sends 0x123 via CANable | smoke, python_sender, tc13, speed_*, bad_checksum, stuck_counter, single_corrupt*, e2e_tolerance, most round 2 tests |
| B | ON | two_senders, sender_e2e, duplicate_id, round2 cycle_time |
| — | Sender on PC USB, Dashboard unplugged | round2 startup |
| none | virtual bus / no bus | frames_helper, frames_dbc |

Close the Arduino Serial Monitor before running (it locks the Dashboard port).

## Known limitations / next steps

- No pytest markers for setups yet; ports hard-coded in `config.py`.
- Function-scoped fixtures → ~2 s Arduino reset per test.
- Bench tests still build frames with `speed_frame()`; switching them to `speed_frame_dbc()` is next.
- The E2E checksum is a plain byte sum: it cannot detect bytes in the wrong position (shown by the DBC red check). Production E2E profiles use a CRC.
- No `.asc` trace per run (REQ-008) — planned.
- UDS diagnostics, LIN and real vehicle ECUs are out of scope so far.
- `firmware/` is a copy of the Arduino sketches; re-copy after a firmware change.
