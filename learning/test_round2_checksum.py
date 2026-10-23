import config
import time
import re
import frames

def read_line_for(dashboard, seconds):
    lines = []
    end = time.time() + seconds
    while time.time() < end:
        line = dashboard.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    return lines

def bad_checksum_frames(speed):
    messages = frames.speed_frames(speed)
    for msg in messages:
        msg.data[7] = (msg.data[7] + 1) & 0xFF
    return messages

def test_checksum_rejected(can_bus, dashboard):
    # Phase 1: good frames -> speed shown
    task = can_bus.send_periodic(frames.speed_frames(0x32), config.CYCLE_TIME_S)
    time.sleep(1)
    dashboard.reset_input_buffer()
    task.stop()
    # Phase 2: same sender, but every frame has a wrong checksum
    task = can_bus.send_periodic(bad_checksum_frames(0x32), config.CYCLE_TIME_S)
    bad_checksum = read_line_for(dashboard, 1.5)
    task.stop()

    checksum_err = [l for l in bad_checksum if "CHECKSUM ERROR" in l]
    assert len(checksum_err)>=10, f"only {len(checksum_err)} CHECKSUM ERROR lines"

    print("\n" + "\n".join(bad_checksum))

    # Criterion 2: no speed shown after the first CHECKSUM ERROR
    first_err = bad_checksum.index(checksum_err[0])
    late_speed = [l for l in bad_checksum[first_err:] if l.startswith("Speed =")]
    assert late_speed == [], f"speed shown after a damaged frame: {late_speed}"

        # Criterion 3: exactly one LOST, about 300 ms after the last GOOD frame
    lost = [l for l in bad_checksum if "SPEED SIGNAL LOST" in l]
    assert len(lost) == 1, f"expected 1 LOST line, got {lost}"
    m = re.search(r"no 0x123 for (\d+) ms", lost[0])
    assert m, f"LOST line has an unexpected format: {lost[0]}"
    lost_ms = int(m.group(1))
    assert config.TIMEOUT_MS < lost_ms <= config.TIMEOUT_MS + 50, f"LOST after {lost_ms} ms (allowed {config.TIMEOUT_MS + 1}–{config.TIMEOUT_MS + 50})"

    # Criterion 4: the Dashboard saw exactly the damage we made (+1)
    m = re.search(r"byte 7 = 0x([0-9A-F]+), expected 0x([0-9A-F]+)", checksum_err[0])
    assert m, f"CHECKSUM ERROR line has an unexpected format: {checksum_err[0]}"
    got = int(m.group(1), 16)
    expected = int(m.group(2), 16)
    assert got == (expected + 1) & 0xFF, f"byte 7 = {got:#04x}, expected {expected:#04x} + 1"

