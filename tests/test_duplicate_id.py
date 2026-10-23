# test_duplicate_id.py - Exp B (v0.3: risk shown) -> step 5d (v0.4): a SECOND sender of 0x123 must be DETECTED, never displayed
import re
import time
import can
import pytest
import config
import frames

DURATION_S = 5
PYTHON_SPEED = 100      # Arduino #1 sends 50 km/h on 0x123; Python sends 100 km/h on the SAME ID


def fake_frames(kind):
    if kind == "bad_e2e":                       # naive fake: counter 0, checksum 0
        return can.Message(arbitration_id=config.SPEED_MSG_ID,
                           data=[0x00, PYTHON_SPEED, 0, 0, 0, 0, 0, 0], is_extended_id=False)
    return frames.speed_frames(PYTHON_SPEED)    # smart fake: correct checksum + its own counter


@pytest.mark.parametrize("kind", ["bad_e2e", "good_e2e"])
def test_duplicate_sender_is_detected(can_bus, dashboard, kind):
    while can_bus.recv(timeout=0.01) is not None:      # drain old frames
        pass
    task = can_bus.send_periodic(fake_frames(kind), config.CYCLE_TIME_S)
    dashboard.reset_input_buffer()

    lines = []                                         # read continuously (many error lines!)
    end = time.time() + DURATION_S
    while time.time() < end:
        line = dashboard.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    task.stop()

    text = "\n".join(lines)
    speeds = [int(s) for s in re.findall(r"Speed = (\d+) km/h", text)]
    cs_err = text.count("CHECKSUM ERROR")
    ctr_err = text.count("COUNTER ERROR")
    print(f"\n[{kind}] speed lines: {len(speeds)} (50: {speeds.count(50)}, 100: {speeds.count(PYTHON_SPEED)})"
          f"  CHECKSUM ERROR: {cs_err}  COUNTER ERROR: {ctr_err}  LOST: {text.count('SPEED SIGNAL LOST')}")
    print("First 6 lines:", lines[:6])

    assert speeds.count(PYTHON_SPEED) == 0, "fake value 100 km/h was DISPLAYED"
    assert cs_err + ctr_err >= DURATION_S * 5, "duplicate sender not reported"