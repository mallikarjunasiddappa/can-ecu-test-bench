"""TC-23 - ONE damaged frame must not cause a false "signal lost"

Requirement: REQ-007 (timeout) vs REQ-011 v3 (+1 or +2 once, right after a CHECKSUM ERROR)
Purpose   : a single bit error is normal on a real bus. The receiver must tolerate it - a false
            LOST warning would alarm the driver for no reason.
Setup     : A - Arduino #1 OFF; Python sends 0x123.
Fault injection: in every 16-frame cycle only the counter-5 frame has checksum + 1
            (one damaged frame every 1.6 s). One send task from the start, so the counter
            never jumps.
Steps     : 1. Warm-up 1 s, clear buffer. 2. Read 16 s (about 10 damaged frames).
Pass when : - at least 8 CHECKSUM ERROR lines (the fault really happened)
            - 0 COUNTER ERROR lines
            - 0 LOST lines
History   : the 160 s long run (test_tc23_single_damaged_frame_long_run.py) found DEF-003 on
            v0.4 (false LOST 2/100) -> REQ-011 revised to v3 -> fixed in Dashboard v0.5.
"""
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


def one_bad_in_16(speed):
    msgs = frames.speed_frames(speed)
    return [frames.damage_checksum(m) if frames.decode_speed(m.data)["AliveCounter"] == 5 else m
        for m in msgs]                            # only the frame with AliveCounter 5 is damaged


def test_single_corrupt_frame_no_false_lost(can_bus, dashboard):
    # One task from the start: no restart = no counter jump (ctr keeps cycling 0..15)
    task = can_bus.send_periodic(one_bad_in_16(0x32), config.CYCLE_TIME_S)
    time.sleep(1)                      # warm-up: Dashboard takes its reference
    dashboard.reset_input_buffer()     # throw away warm-up lines
    # Test: one damaged frame every 1.6 s, for 16 s (~10 damaged frames)
    lines = read_lines_for(dashboard, 16.0)
    task.stop()

    cs_err = [l for l in lines if "CHECKSUM ERROR" in l]
    ctr_err = [l for l in lines if "COUNTER ERROR" in l]
    lost = [l for l in lines if "SPEED SIGNAL LOST" in l]
    restored = [l for l in lines if "RESTORED" in l]
    speed = [l for l in lines if l.startswith("Speed = 50")]

    print(f"\nDamaged frames seen: {len(cs_err)}")
    print(f"COUNTER ERRORs (v0.5 expects 0): {len(ctr_err)}")
    print(f"Speed lines: {len(speed)}")
    print(f"LOST: {len(lost)}   RESTORED: {len(restored)}")
    for l in lost:
        print("  ", l)

    # 1) Sanity: did we really inject the fault?
    assert len(cs_err) >= 8, f"only {len(cs_err)} damaged frames seen - fault not injected"
    # 2) v0.5 / REQ-011 v3: a single damaged frame must NOT cause any COUNTER ERROR
    assert len(ctr_err) == 0, f"{len(ctr_err)} COUNTER ERRORs after single damaged frames"
    # 3) Requirement: one damaged frame must NOT cause a timeout
    assert len(lost) == 0, f"false LOST {len(lost)} times out of {len(cs_err)} damaged frames"