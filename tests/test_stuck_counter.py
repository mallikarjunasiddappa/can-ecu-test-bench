# test_stuck_counter.py - step 5d / REQ-011 + REQ-007: a stuck alive counter is detected, counts as "no frame", recovery afterwards
import re
import time
import config
import frames


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
    task = can_bus.send_periodic(frames.speed_frame(0x32, 5), config.CYCLE_TIME_S)
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