import re
import config
import frames
import time

def read_line_for(dashboard, seconds):
    lines = []
    end = time.time() + seconds
    while time.time() < end:
      line = dashboard.readline().decode(errors="ignore").strip()
      if line:
        lines.append(line)
    return lines

def test_signal_recovery(can_bus, dashboard):
     # Phase 1: sender alive (1 s), then clear the buffer
    task = can_bus.send_periodic(frames.speed_frames(50), config.CYCLE_TIME_S)
    time.sleep(1)
    dashboard.reset_input_buffer()

    # Phase 2: stop the sender, read 2.0 s  -> "during"
    task.stop()
    stop_time = time.time()
    during = read_line_for(dashboard, 2.0)
    lost = [l for l in during if "SPEED SIGNAL LOST" in l]
    assert len(lost) == 1, f"expected 1 LOST line, got {lost}"

    # Phase 3: sender back, read 1.5 s -> "after"
    gap_ms = (time.time() - stop_time) * 1000     #calculate the real gap in ms:
    task = can_bus.send_periodic(frames.speed_frames(0x32), config.CYCLE_TIME_S)
    after = read_line_for(dashboard, 1.5)
    # Criterion 2: exactly one RESTORED in after
    restored = [l for l in after if "SPEED SIGNAL RESTORED" in l]
    assert len(restored) == 1, f"expected 1 RESTORED line, got {restored}"

    # Criterion 4: Speed = 50 km/h lines >= 10
    speed_lines = [l for l in after if "Speed = 50 km/h" in l] 
    assert len(speed_lines) >= 10, f"expected >= 10, got {speed_lines}"

    # Criterion 3: RESTORED index < first Speed index   (new idea, see below)
    restored_pos = after.index(restored[0])           # where is the RESTORED line?  → 0
    first_speed_pos = after.index(speed_lines[0])     # where is the first Speed line? → 1
    assert restored_pos < first_speed_pos, f"Speed shown before RESTORED: {after[:3]}"

    # Criterion 5: no COUNTER ERROR in after
    ctr = [l for l in after if "COUNTER ERROR" in l] 
    assert len(ctr) == 0, f"expected 0, got {ctr}"
    # Criterion 6: N from the RESTORED line inside your range
    # test 1:  lost_ms     = int(re.search(r"no 0x123 for (\d+) ms",  lost[0]).group(1))
    m = re.search(r"missing for (\d+) ms", restored[0])
    assert m, f"RESTORED line has an unexpected format: {restored[0]}"
    restored_ms = int(m.group(1))
    print(f"\ngap {gap_ms:.0f} ms, RESTORED after {restored_ms} ms, margin {restored_ms - gap_ms:.0f} ms")
    assert gap_ms < restored_ms <= gap_ms + 300, f"RESTORED after {restored_ms} ms, gap was {gap_ms:.0f} ms (allowed up to {gap_ms + 300:.0f})"
    task.stop()

    
    

