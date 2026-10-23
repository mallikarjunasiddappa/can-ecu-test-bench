# test_bad_checksum.py - step 5d / REQ-012 + REQ-007: corrupted frames are rejected, count as "no frame", recovery after 2 good frames
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


def bad_checksum_frames(speed):
    msgs = frames.speed_frames(speed)
    for m in msgs:
        m.data[7] = (m.data[7] + 1) & 0xFF      # checksum off by one = "damaged on the way"
    return msgs


def test_bad_checksum_rejected_then_recovery(can_bus, dashboard):
    # Phase 1: good frames -> speed shown
    task = can_bus.send_periodic(frames.speed_frames(0x32), config.CYCLE_TIME_S)
    time.sleep(1)
    dashboard.reset_input_buffer()
    before = read_lines_for(dashboard, 1.0)

    # Phase 2: same sender, but every frame has a wrong checksum
    task.stop()
    task = can_bus.send_periodic(bad_checksum_frames(0x32), config.CYCLE_TIME_S)
    during = read_lines_for(dashboard, 1.5)

    # Phase 3: good frames again
    task.stop()
    task = can_bus.send_periodic(frames.speed_frames(0x32), config.CYCLE_TIME_S)
    after = read_lines_for(dashboard, 1.5)
    task.stop()

    print("\nBEFORE:", before[:3], "\nDURING:", during, "\nAFTER:", after[:4])

    assert "Speed = 50 km/h" in before
    cs_err = [l for l in during if "CHECKSUM ERROR" in l]
    lost = [l for l in during if "SPEED SIGNAL LOST" in l]
    assert len(cs_err) >= 10, f"only {len(cs_err)} CHECKSUM ERROR lines"
    assert not any(l.startswith("Speed =") for l in during), "corrupted value displayed"
    assert len(lost) == 1, f"expected 1 LOST line, got {lost}"
    m = re.search(r"no 0x123 for (\d+) ms", lost[0])
    assert m, f"LOST line has an unexpected format: {lost[0]}"
    lost_ms = int(m.group(1))
    assert config.TIMEOUT_MS < lost_ms <= config.TIMEOUT_MS + 50
    assert any(l.startswith("SPEED SIGNAL RESTORED") for l in after)
    assert "Speed = 50 km/h" in after