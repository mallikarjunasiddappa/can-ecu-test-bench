"""TC-23 (long run) - ONE damaged frame must not cause a false "signal lost", over 160 s

Requirement: REQ-007 vs REQ-011 v3
Purpose   : rare timing faults only show up over many events. Same test as TC-23, ten times
            longer (about 100 damaged frames) to catch a 1-2 % failure rate.
Setup     : A - Arduino #1 OFF; Python sends 0x123. Not part of the quick regression (about 165 s).
Fault injection: counter-5 frame with checksum + 1 in every 16-frame cycle.
Steps     : 1. Warm-up 1 s. 2. Read 160 s.
Pass when : at least 90 CHECKSUM ERROR lines, 0 COUNTER ERROR, 0 LOST.
History   : FAILED on Dashboard v0.4 with LOST 2/100 -> DEF-003 (valid-frame gap ~300 ms = the
            limit, decided by ~1 ms jitter). PASSES on v0.5 (0/100).
"""
import time
import config
import frames
import pytest

pytestmark = [pytest.mark.setup_a, pytest.mark.long]       # Setup A, 160 s - not in the quick regression


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
    lines = read_lines_for(dashboard, 160.0)
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
    assert len(cs_err) >= 90, f"only {len(cs_err)} damaged frames seen - fault not injected"
    # 2) v0.5 / REQ-011 v3: a single damaged frame must NOT cause any COUNTER ERROR
    assert len(ctr_err) == 0, f"{len(ctr_err)} COUNTER ERRORs after single damaged frames"
    # 3) Requirement: one damaged frame must NOT cause a timeout
    assert len(lost) == 0, f"false LOST {len(lost)} times out of {len(cs_err)} damaged frames"