import can
import config 
import frames
import time
import re


def read_line_for(dashboard, seconds):
    lines = []
    end = time.time() + seconds
    while time.time() < end:
        line = dashboard.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    return lines

def test_signal_timeout(can_bus, dashboard):
    # Phase 1: sender alive
    # TODO 1: start sending frames.speed_frames(50) every config.CYCLE_TIME_S  -> save it as "task"

    task = can_bus.send_periodic(frames.speed_frames(50), config.CYCLE_TIME_S)
    time.sleep(1)
    dashboard.reset_input_buffer()
    before = read_line_for(dashboard, 1.0)

    # Phase 2: sender lost
    # TODO 2: stop the sender

    task.stop()
    during = read_line_for(dashboard, 1.0)

    # Criterion 1
    # TODO 3: assert that "Speed = 50 km/h" is in before

    speed_lines = [l for l in before if "Speed = 50 km/h" in l] 
    assert len(speed_lines) >= 8

    # or write like below
    assert len(speed_lines) >= 8, f"only {len(speed_lines)} Speed lines while sender alive"

    # Criterion 2
    lost = [l for l in during if "SPEED SIGNAL LOST" in l]
    # TODO 4: assert that there is exactly ONE lost line (add a message with the real list)
    assert len(lost) == 1, f"expected 1 LOST line, got {lost}"

    # Criterion 3
    m = re.search(r"no 0x123 for (\d+) ms", lost[0])
    assert m, f"LOST line has an unexpected format: {lost[0]}"
    lost_ms = int(m.group(1))
    # TODO 5: assert config.TIMEOUT_MS < lost_ms <= config.TIMEOUT_MS + 50  (add a message with lost_ms)
    assert config.TIMEOUT_MS < lost_ms <= config.TIMEOUT_MS + 50, f"LOST after {lost_ms} ms (allowed {config.TIMEOUT_MS + 1}–{config.TIMEOUT_MS + 50})"