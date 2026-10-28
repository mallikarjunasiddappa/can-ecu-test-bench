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
| `frames.py` | Builds valid 0x123 frames (and `damage_checksum(frame)`: fault injection by signal name): `checksum()`, `speed_frame(speed, counter)` (hand-built), `speed_frames(speed, strict=True)` → 16 DBC-built frames for `send_periodic`; `speed_frame_dbc(speed, counter, strict=True)` builds the same frame from `vehicle.dbc` by signal name (`strict=False` for fault injection, e.g. speed 251) |
| `analyze_trace.py` | Offline trace analysis: reads a Vector `.asc` trace (e.g. recorded with `python -m can.logger -i slcan -c COM5 -b 500000 -f logs/trace.asc`), decodes 0x123 with `vehicle.dbc` and checks checksum (REQ-012), alive counter (REQ-011) and cycle time 90–110 ms (REQ-002); exit code 1 if errors. Red checks on a damaged copy: 1 bad checksum → 1 error; + 1 deleted frame → 3 errors (CHECKSUM, COUNTER, GAP) |
| `pytest.ini` | `testpaths = tests`: plain `python -m pytest` collects only `tests/` (82 items), never stray practice files |
| `requirements.txt` | Pinned versions: pytest 9.1.1, pytest-html 4.2.0, pyserial 3.5, python-can 4.6.1 |

## Tests

**Test layout:** `tests/unit/` = no hardware (5 files, 60 items, ~3 s — `python -m pytest tests/unit`), `tests/bench/` = needs the CAN bench (21 files). All 82 items: `python -m pytest`.

**Regression suite (15 files, 53 test items + 1 long run)** — file names follow `test_tc<ID>_<what_it_checks>.py`; every file starts with a header (requirement, purpose, setup, steps, pass criteria, history)

| File | TC | What it proves |
|---|---|---|
| `test_smoke_dashboard_boot.py` | — | Dashboard boots with the expected firmware version |
| `test_support_python_sender_display.py` | — | Python-sent 100 km/h is displayed |
| `test_tc13_speed_signal_timeout.py` | TC-13 | Exactly one LOST at 300–350 ms, no stale speed, RESTORED |
| `test_tc14_speed_valid_values.py` | TC-14 | Boundary values 0, 1, 50, 100, 249, 250 displayed (parametrized) |
| `test_tc15_speed_invalid_values.py` | TC-15 | 251, 253, 0xFE, 0xFF → INVALID, no number shown |
| `test_unit_frames_counter_checksum.py` | — | Tests the test tool itself on a virtual bus (no hardware) |
| `test_unit_dbc_frame_equivalence.py` | — | Equivalence test, no hardware: DBC-built frames == hand-built frames for 7 speeds × 4 counters (28 cases). Red check with a wrong start bit in the DBC → 24 failed (speed 0 cannot reveal a wrong position) |
| `test_unit_damage_checksum.py` | — | Unit test, no hardware: `frames.damage_checksum()` changes only the Checksum signal (+1, found via the DBC) for 5 speeds × 3 counters (15 cases). Red check `+ 0` → 15 failed |
| `test_tc16_two_ids_cycle_time.py` | TC-16 | 0x123 timing unaffected by a second ID on the bus |
| `test_tc19_sender_e2e_conformance.py` | TC-19 | Sender ECU conformance: checksum, counter, rollover |
| `test_tc20_duplicate_sender_rejected.py` | TC-20 | A fake second sender of 0x123 is never displayed |
| `test_tc21_checksum_error_injection.py` | TC-21 | Damaged checksums rejected → LOST → recovery |
| `test_tc22_stuck_alive_counter.py` | TC-22 | Frozen alive counter detected → LOST → resync |
| `test_tc23_single_damaged_frame.py` | TC-23 | One damaged frame must NOT cause a false LOST |
| `test_tc23_single_damaged_frame_long_run.py` | TC-23 long | Same over 160 s / 100 damaged frames (found DEF-003) |
| `test_tc24_26_e2e_tolerance.py` | TC-24..26 | Two damaged in a row; damaged + fake sender (wrong / "lucky" counter) |

**Round 2 — tests written from the requirement text only (8 files, 13 items, in `tests/bench/`)**

| File | Req | What it proves |
|---|---|---|
| `test_tc13_speed_signal_timeout_v2.py` | REQ-007 | LOST reaction time within limits (measured 301 ms) |
| `test_tc13_signal_recovery_timing.py` | REQ-007, REQ-011 | RESTORED only after 2 good frames; recovery time vs measured gap |
| `test_tc21_checksum_rejection_v2.py` | REQ-012 | Only damaged frames → every one rejected, LOST once |
| `test_req011_counter_jump.py` | REQ-011 | Skipped counter → COUNTER ERROR, isolated, display recovers |
| `test_tc04_speed_value_change.py` | REQ-003 | 50 → 100 km/h change shown at once, no false errors (TC-04) |
| `test_tc14_15_speed_boundary.py` | REQ-010 | 249/250 valid vs 251/253/0xFE/0xFF invalid, exact expected line |
| `test_tc03_sender_cycle_time.py` | REQ-002 | Every gap 90–110 ms, average drift check (measured 99.3–102.5 ms) |
| `test_tc05_sender_startup_time.py` | REQ-004 | First frame after reset ≤ 2 s (measured 1.503 s, TC-05) |

Every test was checked **green → red → green**: after it passed, the limit or the stimulus was broken on
purpose to prove the test can fail with a clear message, then restored.

## Results so far

- 26 test cases in the test-case workbook: **19 Pass, 0 Fail, 7 Not Run** (wiring-fault, .asc logging and bus-side checks still to do).
- **Full regression 2026-10-27 after the DBC migration: 82 / 82 passed** — Setup A + unit 74 (251.6 s), Setup B 6 (48.4 s), TC-05 start-up 1 (1.505 s), TC-23 long run 1 (165.1 s). Every test builds and checks 0x123 through `vehicle.dbc` by signal name; no test reads or writes a byte position.
- **3 product defects found by these tests and closed after retest:**
  - **DEF-001** — no timeout detection, stale speed stayed on screen → fixed in v0.2.
  - **DEF-002** — 0xFB–0xFF shown as real speeds → range check in v0.3.
  - **DEF-003** — one damaged frame caused a false SIGNAL LOST in ~2 % of cases (found only by the
    160 s long run) → requirement REQ-011 revised (v3) → v0.5 → long run 0/100.
- **Open observation OBS-002:** E2E (counter + checksum) is a *safety* mechanism, not *security* — a
  sender that mimics the next counter is accepted for one frame. Mitigation would be SecOC / an IDS rule.
- Requirement gaps raised during test design: REQ-003 has no response time (test uses an assumption),
  REQ-004 "power-up" — reset via USB is not a true power cycle.

## UDS diagnostics (ISO 14229) — ECU simulator, no hardware yet

A small diagnostic ECU in Python, tested the way a workshop tester or test system talks to an ECU.

| Layer | File | What it does |
|---|---|---|
| UDS logic | `uds/ecu_simulator.py` | `EcuSimulator.handle(request) -> response`: 0x10 DiagnosticSessionControl (default 01 / extended 03), 0x22 ReadDataByIdentifier (F189 software version, F190 VIN), 0x2E WriteDataByIdentifier (extended session only); NRC 0x11, 0x12, 0x13, 0x31, 0x7F |
| Transport | `uds/ecu_server.py` | `EcuServer`: ISO-TP (ISO 15765-2) on CAN 0x7E0 (requests) / 0x7E8 (responses), padding 00, background thread |
| Demo | `uds/demo_vin_over_isotp.py` | reads the VIN over a virtual CAN bus and prints every frame: single frame request, first frame `10 14`, flow control `30 08 00`, consecutive frames `21`, `22` |
| Tests | `tests/unit/test_unit_uds_simulator.py` | 12 tests on the logic: positive / negative responses, session sequences, write + read back |
| Tests | `tests/unit/test_unit_uds_client.py` | 4 end-to-end tests with a real UDS client (`udsoncan`) over ISO-TP on a virtual bus; refusals checked with `pytest.raises(NegativeResponseException)` and the NRC |

Red checks: wrong positive SID (0x60) → 2 failed; session check removed → write in default accepted → 2 failed (logic) and "DID NOT RAISE NegativeResponseException" (client).

Next: DTCs (0x19 / 0x14) linked to the 0x123 timeout, security access (0x27), session timeout + TesterPresent, then the same tests over the real CANable.

## How to run

```bash
pip install -r requirements.txt
# edit config.py: CAN_CHANNEL (CANable) and DASHBOARD_PORT (Dashboard Arduino)
python -m pytest -m unit                         # no hardware: DBC, frame builder, UDS simulator (60 tests, ~3 s)
python -m pytest -m smoke                        # bench check: Dashboard boots with the expected firmware
python -m pytest -m "setup_a and not long"       # Setup A quick regression (30 tests)
python -m pytest -m setup_b                      # Setup B (6 tests)
python -m pytest -m special                      # TC-05 start-up (special wiring, see its header)
python -m pytest -m long                         # TC-23 long run (160 s)
python -m pytest -m unit -v --html=reports/report.html   # HTML report (any selection)
```

Every test file carries a marker (`pytestmark = …`), registered in `pytest.ini` with `--strict-markers`
(a typo in a marker name is an error, not a silently empty run):

| Marker | Bench setup | Tests |
|---|---|---|
| `unit` | none — pure Python / virtual CAN bus | 60 |
| `setup_a` | Arduino #1 OFF — Python sends 0x123 via the CANable | 31 (incl. smoke and the long run) |
| `setup_b` | Arduino #1 ON | 6 |
| `special` | Arduino #1 on PC USB (COM6), Dashboard unplugged | 1 (TC-05) |
| `long` | Setup A, > 1 min | 1 (TC-23 long run) |
| `smoke` | Setup A | 1 |

unit + setup_a + setup_b + special = 98 = all tests.

Close the Arduino Serial Monitor before running (it locks the Dashboard port).

## Known limitations / next steps

- Ports hard-coded in `config.py`.
- Function-scoped fixtures → ~2 s Arduino reset per test.
- One hand-built frame remains on purpose: the naive fake (`counter 0, checksum 0`) in TC-20, which must break the DBC rules; `speed_frame()` stays only as the reference in the DBC equivalence unit test.
- The E2E checksum is a plain byte sum: it cannot detect bytes in the wrong position (shown by the DBC red check). Production E2E profiles use a CRC.
- `.asc` traces are recorded by hand; automatic recording per test (REQ-008) is next. The CANable cannot record frames it sends itself (python-can slcan has no own-message receive), so Setup A traces need a second, listen-only interface (ordered).
- UDS diagnostics, LIN and real vehicle ECUs are out of scope so far.
- `firmware/` is a copy of the Arduino sketches; re-copy after a firmware change.
