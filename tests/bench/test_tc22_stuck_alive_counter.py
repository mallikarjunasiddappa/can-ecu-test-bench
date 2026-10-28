"""TC-22 - A frozen (stuck) alive counter is detected, treated as "no frame", then recovery

Requirement: REQ-011 (alive counter), REQ-007 (timeout)
Purpose   : a sender whose software hangs can keep repeating its last frame. The checksum is
            still correct, so only the alive counter can reveal it.
Setup     : A - Arduino #1 OFF; Python sends 0x123.
Fault injection: phase 2 repeats ONE valid frame (counter 5, built from the DBC) every 100 ms.
Steps     : Phase 1: normal frames -> read 1 s.
            Phase 2: frozen counter 5 -> read 1.5 s.
            Phase 3: normal frames (counter restarts at 0) -> read 1.5 s.
Pass when : - speed shown in phase 1
            - phase 2: at least 10 COUNTER ERROR lines, at most one leading speed line, exactly
              one LOST at 301-350 ms, no RESTORED while still frozen
            - phase 3: resync error "expected 6, got 0", then RESTORED and "Speed = 50 km/h"
"""
import re
import time
import config
import frames
import pytest

pytestmark = pytest.mark.setup_a                           # Arduino #1 OFF, Python sends 0x123


def read_lines_for(dashboard, seconds):
    lines = []
    end = time.time() + seconds
    while time.time() < end:
        line = dashboard.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    return lines


def test_stuck_counter_detected_then_recovery(can_bus, dashboard):
    # Phase 1: good frames -> speed shown
    task = can_bus.send_periodic(frames.speed_frames(0x32), config.CYCLE_TIME_S)
    time.sleep(1)
    dashboard.reset_input_buffer()
    before = read_lines_for(dashboard, 1.0)

    # Phase 2: frozen sender - the SAME frame (counter 5, correct checksum) every 100 ms
    task.stop()
    task = can_bus.send_periodic(frames.speed_frame_dbc(0x32, 5), config.CYCLE_TIME_S)
    during = read_lines_for(dashboard, 1.5)

    # Phase 3: good frames again (counter starts at 0)
    task.stop()
    task = can_bus.send_periodic(frames.speed_frames(0x32), config.CYCLE_TIME_S)
    after = read_lines_for(dashboard, 1.5)
    task.stop()

    print("\nBEFORE:", before[:3], "\nDURING:", during, "\nAFTER:", after[:4])

    assert "Speed = 50 km/h" in before
    ctr_err = [i for i, l in enumerate(during) if "COUNTER ERROR" in l]
    speed = [i for i, l in enumerate(during) if l.startswith("Speed =")]
    lost = [l for l in during if "SPEED SIGNAL LOST" in l]
    assert len(ctr_err) >= 10, f"only {len(ctr_err)} COUNTER ERROR lines"
    assert len(speed) <= 1, f"stuck value displayed {len(speed)} times"
    if speed:
        assert speed[0] < ctr_err[0], "speed shown AFTER the counter froze"
    assert len(lost) == 1, f"expected 1 LOST line, got {lost}"
    m = re.search(r"no 0x123 for (\d+) ms", lost[0])
    assert m, f"LOST line has an unexpected format: {lost[0]}"
    lost_ms = int(m.group(1))
    assert config.TIMEOUT_MS < lost_ms <= config.TIMEOUT_MS + 50
    assert not any("RESTORED" in l for l in during), "restored while still stuck"
    assert any("expected 6, got 0" in l for l in after), "no resync COUNTER ERROR"
    assert any(l.startswith("SPEED SIGNAL RESTORED") for l in after)
    assert "Speed = 50 km/h" in after