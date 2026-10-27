"""TC-24, TC-25, TC-26 - Limits of the DEF-003 fix (REQ-011 v3 tolerance)

Requirement: REQ-011 v3 - right after a CHECKSUM ERROR the next frame may be +1 OR +2 (once);
             REQ-012; REQ-007
Purpose   : the DEF-003 fix relaxed the counter check. These tests prove the relaxation is
            not a hole: it tolerates exactly one damaged frame and nothing more.
Setup     : A - Arduino #1 OFF; Python plays the real ECU (50 km/h) AND the fake (100 km/h).
            The fake is a second send task (one frame per 1.6 s, built from the DBC), started
            0.55 s after the real one so it lands between counter 5 and 6.
TC-24     : two damaged frames in a row (counters 5 and 6) -> one LOST per event, recovery.
TC-25     : one damaged frame + fake with a wrong counter (13) -> fake rejected
            ("expected 5 or 6, got 13"), never displayed.
TC-26     : one damaged frame + "lucky" fake with counter 6 -> accepted as reference once,
            the real frame 6 is rejected, the fake value is still never displayed, no LOST.
Pass when : see the asserts in each test; in all three, "Speed = 100" never appears.
"""
# TC-24 two damaged in a row -> LOST (option A) | TC-25 damaged + fake wrong ctr | TC-26 damaged + lucky fake
# Setup A: Arduino #1 OFF - Python plays the real ECU AND the fake
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


def real_frames(damaged):
    msgs = frames.speed_frames(0x32)                 # real ECU: 50 km/h, ctr 0..15
    return [frames.damage_checksum(m) if frames.decode_speed(m.data)["AliveCounter"] in damaged else m
            for m in msgs]                            # damage the frames whose AliveCounter is in 'damaged'


def run(can_bus, dashboard, damaged, fake_ctr=None, seconds=16.0):
    real = can_bus.send_periodic(real_frames(damaged), config.CYCLE_TIME_S)
    fake = None
    if fake_ctr is not None:
        time.sleep(0.55)                             # ctr 5 leaves at 0.5 s, ctr 6 at 0.6 s -> fake lands between
        fake = can_bus.send_periodic(frames.speed_frame_dbc(100, fake_ctr), 1.6)   # one fake per 16-frame loop
    time.sleep(1)                                    # warm-up
    dashboard.reset_input_buffer()
    lines = read_lines_for(dashboard, seconds)
    if fake:
        fake.stop()
    real.stop()
    return lines


def count(lines, text):
    return len([l for l in lines if text in l])


def test_tc24_two_damaged_in_a_row_gives_lost(can_bus, dashboard):
    lines = run(can_bus, dashboard, damaged=[5, 6])
    cs, lost, rest = count(lines, "CHECKSUM ERROR"), count(lines, "SIGNAL LOST"), count(lines, "RESTORED")
    print(f"\n[TC-24] CHECKSUM ERROR {cs}  LOST {lost}  RESTORED {rest}")
    assert cs >= 16, "fault not injected"
    assert abs(lost - cs / 2) <= 1, "expected one LOST per double-damage event (REQ-011 v3, option A)"
    assert rest >= lost - 1, "no recovery after LOST"


def test_tc25_damaged_plus_fake_wrong_counter(can_bus, dashboard):
    lines = run(can_bus, dashboard, damaged=[5], fake_ctr=13)
    used = count(lines, "expected 5 or 6, got 13")
    print(f"\n[TC-25] fake rejected ('expected 5 or 6, got 13') {used}  fake shown {count(lines, 'Speed = 100')}")
    assert count(lines, "Speed = 100") == 0, "fake value DISPLAYED"
    assert used >= 8, "fake did not use up the tolerance as designed"


def test_tc26_damaged_plus_lucky_fake(can_bus, dashboard):
    lines = run(can_bus, dashboard, damaged=[5], fake_ctr=6)
    kicked = count(lines, "expected 7, got 6")
    print(f"\n[TC-26] real ctr 6 rejected after lucky fake {kicked}  fake shown {count(lines, 'Speed = 100')}"
          f"  LOST {count(lines, 'SIGNAL LOST')}")
    assert count(lines, "Speed = 100") == 0, "lucky fake DISPLAYED"
    assert kicked >= 8, "lucky fake was not accepted as expected"
    assert count(lines, "SIGNAL LOST") == 0
