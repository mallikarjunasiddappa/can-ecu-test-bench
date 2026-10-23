import config
import time
import frames

def read_line_for(dashboard, seconds):
    lines = []
    end = time.time() + seconds
    while time.time() < end:
        line = dashboard.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    return lines

def test_speed_change_50_to_100(can_bus, dashboard):
    # Phase 1: 50 km/h, settle, then read 1.0 s
    task = can_bus.send_periodic(frames.speed_frames(50), config.CYCLE_TIME_S)
    time.sleep(1)
    dashboard.reset_input_buffer()
    before = read_line_for(dashboard, 1.0)

    # Change: same task, new data -> counter and timing continue (no COUNTER ERROR)
    task.modify_data(frames.speed_frames(100))

    # Phase 2: read 1.5 s
    after = read_line_for(dashboard, 1.5)
    task.stop()

    print("\nBEFORE:\n" + "\n".join(before) + "\nAFTER:\n" + "\n".join(after))

    # Criterion 1: before = 50 km/h, steady
    before_speed = [l for l in before if l.startswith("Speed =")]
    assert len(before_speed) >= 8, f"only {len(before_speed)} Speed lines before the change"
    assert all(l == "Speed = 50 km/h" for l in before_speed), f"unexpected value before: {before_speed}"

    # Criterion 3: 100 appears fast
    # ASSUMPTION: REQ-003 has no response time; 2 frames (200 ms) used -> raise with requirement owner
    after_speed = [l for l in after if l.startswith("Speed =")]
    assert "Speed = 100 km/h" in after_speed, f"100 never shown: {after_speed}"
    first_100 = after_speed.index("Speed = 100 km/h")
    assert first_100 <= 1, f"{first_100} old Speed lines before 100: {after_speed[:4]}"

    # Criterion 4: the change is not an error (before and after)
    bad = [l for l in before + after
           if "CHECKSUM ERROR" in l or "COUNTER ERROR" in l or "LOST" in l or "RESTORED" in l]
    assert bad == [], f"unexpected error lines: {bad}"

    # Criterion 5: once 100, always 100
    after_100 = after_speed[first_100:]
    assert all(l == "Speed = 100 km/h" for l in after_100), f"went back to another value: {after_100}"
    assert len(after_100) >= 10, f"only {len(after_100)} lines at 100 km/h"
