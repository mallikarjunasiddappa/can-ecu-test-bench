"""TC-04 - A speed change (50 -> 100 km/h) is shown immediately, without errors

Requirement: REQ-003 (speed decoding)
Purpose   : a real speed changes constantly. A new value must replace the old one at once, and a
            value change must not be mistaken for an error.
Setup     : A - Arduino #1 OFF; Python sends 0x123.
Steps     : 1. Send 50 km/h, settle 1 s, clear buffer, read 1 s ("before").
            2. task.modify_data(100 km/h) - same task, so counter and timing continue.
            3. Read 1.5 s ("after").
Pass when : - at least 8 lines, all "Speed = 50 km/h" before
            - 100 km/h appears with at most 1 old line in between
            - no CHECKSUM / COUNTER ERROR, LOST or RESTORED
            - once 100, always 100 (at least 10 lines)
ASSUMPTION: REQ-003 has no response time -> 2 frames (200 ms) used; raised with the requirement owner.
"""
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
