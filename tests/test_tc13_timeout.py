# test_tc13_timeout.py - TC-13 / REQ-007: Dashboard must detect loss of 0x123
import re
import time
import can
import config
import frames


def read_lines_for(dashboard, seconds):
    """Collect every line the ECU prints during 'seconds'."""
    lines = []
    end = time.time() + seconds
    while time.time() < end:
        line = dashboard.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    return lines


def test_tc13_speed_signal_timeout(can_bus, dashboard):
    msg = frames.speed_frames(0x32)   # 50 km/h, counter + checksum (REQ-011/012)
    # Step 1: sender ECU alive -> Dashboard shows speed
    task = can_bus.send_periodic(msg, config.CYCLE_TIME_S)
    time.sleep(1)
    dashboard.reset_input_buffer()
    before = read_lines_for(dashboard, 1.0)

    # Step 2: sender ECU lost -> stop sending 0x123
    task.stop()
    during = read_lines_for(dashboard, 2.0)

    # Step 3: sender ECU back -> start sending again
    task = can_bus.send_periodic(msg, config.CYCLE_TIME_S)
    after = read_lines_for(dashboard, 1.0)
    task.stop()

    print("\nBEFORE:", before, "\nDURING:", during, "\nAFTER:", after)

    # Expected 1: speed shown while sender is alive
    assert "Speed = 50 km/h" in before

    # Expected 2: exactly ONE 'LOST' message, detected just after 300 ms
    lost = [l for l in during if l.startswith("SPEED SIGNAL LOST")]
    assert len(lost) == 1, f"expected 1 LOST line, got {lost}"
    m = re.search(r"no 0x123 for (\d+) ms", lost[0])
    assert m, f"LOST line has an unexpected format: {lost[0]}"
    lost_ms = int(m.group(1))
    assert config.TIMEOUT_MS < lost_ms <= config.TIMEOUT_MS + 50

    # Expected 3: no stale speed value after the LOST message
    after_lost = during[during.index(lost[0]) + 1:]
    assert not any(l.startswith("Speed =") for l in after_lost)

    # Expected 4: recovery - RESTORED message and speed shown again
    assert any(l.startswith("SPEED SIGNAL RESTORED") for l in after)
    assert "Speed = 50 km/h" in after
