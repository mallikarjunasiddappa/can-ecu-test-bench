"""REQ-011 - A skipped frame (counter jump 6 -> 8) is detected, isolated and recovered (round 2, test 4)

Requirement: REQ-011 v3 (alive counter); REQ-007 (no LOST: valid frames keep arriving)
Purpose   : a lost frame on the bus shows up as a counter jump. The Dashboard must report it,
            blank the display briefly, and recover after 2 good frames - without a false LOST.
Setup     : A - Arduino #1 OFF; Python sends 0x123.
Fault injection: the counter-7 frame is removed from every 16-frame cycle (one jump per 1.5 s).
Steps     : 1. Start the skipping sender, settle 1 s, clear buffer.
            2. Read 3 s.
Pass when : - 1-3 COUNTER ERROR lines, all "expected 7, got 8" (15 -> 0 is NOT an error)
            - no LOST, no CHECKSUM ERROR
            - the line after each COUNTER ERROR is "Speed = 50 km/h" (frame 9 silent, 10 shown)
            - at least 20 speed lines (display not frozen)
"""
import config
import time
import re
import frames

# copy your read_line_for helper from test 3 here
def read_line_for(dashboard, seconds):
    lines = []
    end = time.time() + seconds
    while time.time() < end:
        line = dashboard.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    return lines

def test_counter_jump_detected(can_bus, dashboard):
    # Phase 1: skip sender from the start (no counter 7), let the Dashboard settle
    skip_frames = [m for m in frames.speed_frames(50) if frames.decode_speed(m.data)["AliveCounter"] != 7]
    # Red check (done 2026-10-23): "!= 99" removes nothing -> no jump -> 0 COUNTER ERROR -> criterion 1 FAILED as expected
    task = can_bus.send_periodic(skip_frames, config.CYCLE_TIME_S)
    time.sleep(1)
    dashboard.reset_input_buffer()

    # Phase 2: read 3.0 s
    lines = read_line_for(dashboard, 3.0)
    task.stop()

    print("\n" + "\n".join(lines))      # temporary: see the real lines first

        # Criterion 1: 1–3 COUNTER ERROR lines (one jump every 15 frames, window ~30 frames)
    ctr_err = [l for l in lines if "COUNTER ERROR" in l]
    assert 1 <= len(ctr_err) <= 3, f"expected 1–3 COUNTER ERROR lines, got {len(ctr_err)}: {ctr_err}"

    # Criterion 2: every error is the same jump 6 -> 8 (the 15 -> 0 wrap is NOT an error)
    assert all("expected 7, got 8" in l for l in ctr_err), f"unexpected counter error: {ctr_err}"

    # Criterion 3: no LOST (the sender never stops, frame 9 resets the clock after 200 ms)
    lost = [l for l in lines if "SPEED SIGNAL LOST" in l]
    assert lost == [], f"LOST should not appear: {lost}"

    # Criterion 4: no CHECKSUM ERROR (only the counter is wrong in this test)
    cs_err = [l for l in lines if "CHECKSUM ERROR" in l]
    assert cs_err == [], f"CHECKSUM ERROR should not appear: {cs_err}"

    # Criterion 5: right after every COUNTER ERROR the speed comes back (frame 9 silent, frame 10 shows)
    for i, line in enumerate(lines):
        if "COUNTER ERROR" in line and i + 1 < len(lines):
            assert lines[i + 1] == "Speed = 50 km/h", f"after '{line}' came '{lines[i + 1]}'"

    # Criterion 6: display not frozen
    speed_lines = [l for l in lines if l.startswith("Speed =")]
    assert len(speed_lines) >= 20, f"only {len(speed_lines)} Speed lines"