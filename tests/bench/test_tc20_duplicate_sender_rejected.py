"""TC-20 - A second sender of 0x123 is detected and its value never displayed

Requirement: REQ-011 / REQ-012 (E2E) and REQ-007
Purpose   : a CAN ID says WHAT a message is, not WHO sent it. A faulty or fake node sending
            the same ID must not reach the display. E2E protection (counter + checksum) must
            expose it.
Setup     : B - Arduino #1 ON sends 50 km/h; Python sends a fake 100 km/h on the same ID.
Runs      : "bad_e2e"  - naive fake: counter 0, checksum 0 (hand-built on purpose)
            "good_e2e" - smart fake: correct checksum and its own counter (built from the DBC)
Steps     : 1. Drain old frames, start the fake, read the Dashboard continuously for 5 s.
Pass when : - "Speed = 100 km/h" never appears
            - at least 25 CHECKSUM ERROR + COUNTER ERROR lines (the conflict is reported)
History   : TC-17 on v0.3 showed the risk (both values displayed). Limitation: OBS-002 - a fake
            that copies the next counter exactly is accepted for one frame (needs SecOC).
"""
import re
import time
import can
import pytest
import config
import frames
import helpers

pytestmark = pytest.mark.setup_b                           # Arduino #1 ON

DURATION_S = 5
PYTHON_SPEED = 100      # Arduino #1 sends 50 km/h on 0x123; Python sends 100 km/h on the SAME ID
FAKE_OFFSET = 8         # fake counter = real counter + 8: never "the next one" (the lucky case is TC-26)


def real_counter_now(can_bus):
    """AliveCounter of the next frame from the real ECU (Arduino #1)."""
    helpers.drain(can_bus)
    end = time.time() + 1.0
    while time.time() < end:
        msg = can_bus.recv(timeout=0.2)
        if msg is not None and msg.arbitration_id == config.SPEED_MSG_ID:
            return frames.decode_speed(msg.data)["AliveCounter"]
    raise AssertionError("no 0x123 from Arduino #1 within 1 s - is it ON?")


def fake_frames(kind, start_counter):
    if kind == "bad_e2e":                       # naive fake: counter 0, checksum 0
        return can.Message(arbitration_id=config.SPEED_MSG_ID,
                           data=[0x00, PYTHON_SPEED, 0, 0, 0, 0, 0, 0], is_extended_id=False)
    msgs = frames.speed_frames(PYTHON_SPEED)    # smart fake: correct checksum, counters 0..15
    return msgs[start_counter:] + msgs[:start_counter]   # rotated: the first frame has start_counter


@pytest.mark.parametrize("kind", ["bad_e2e", "good_e2e"])
def test_duplicate_sender_is_detected(can_bus, dashboard, kind):
    start = (real_counter_now(can_bus) + FAKE_OFFSET) % 16
    task = can_bus.send_periodic(fake_frames(kind, start), config.CYCLE_TIME_S)
    dashboard.reset_input_buffer()
    lines = helpers.read_lines_for(dashboard, DURATION_S)     # many error lines - read continuously
    task.stop()

    text = "\n".join(lines)
    speeds = [int(s) for s in re.findall(r"Speed = (\d+) km/h", text)]
    cs_err = text.count("CHECKSUM ERROR")
    ctr_err = text.count("COUNTER ERROR")
    print(f"\n[{kind}] fake starts at counter {start}; speed lines: {len(speeds)} (50: {speeds.count(50)}, "
          f"100: {speeds.count(PYTHON_SPEED)})  CHECKSUM ERROR: {cs_err}  COUNTER ERROR: {ctr_err}  "
          f"LOST: {text.count('SPEED SIGNAL LOST')}")
    print("First 6 lines:", lines[:6])

    assert speeds.count(PYTHON_SPEED) == 0, "fake value 100 km/h was DISPLAYED"
    assert cs_err + ctr_err >= DURATION_S * 5, "duplicate sender not reported"