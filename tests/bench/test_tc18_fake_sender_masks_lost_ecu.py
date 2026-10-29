"""TC-18 - A fake sender masks a dead speed ECU (REQ-007)

Requirement: REQ-007 (SIGNAL LOST within ~300 ms when no valid 0x123 arrives); REQ-011 / REQ-012 (E2E)
Purpose   : a CAN ID says WHAT, not WHO. If the real sender dies while another node still sends
            0x123, the timeout can be masked. Shows what E2E (v0.5) protects against, and what not.
Setup     : A - Arduino #1 OFF; Python plays the real ECU (50 km/h) AND the fake (100 km/h).
Steps     : 1. Real ECU alone for 2 s -> Dashboard shows 50.
            2. Start the fake, both on the bus for 1 s.
            3. Stop the real ECU ("ECU dies"), read the Dashboard: 2 s takeover + 3 s settled.
Pass when : naive fake (ctr 0, checksum 0): at least 1 LOST, 100 never shown  -> E2E protects
            smart fake (DBC-built, own counter): 100 shown and NO LOST in the settled 3 s
                                                 -> masking reproduced (E2E limit, OBS-002)
History   : Run 1 (2026-10-14) manual on v0.3, no E2E: masking seen, ms values not captured.
"""
import time
import can
import pytest
import config
import frames

pytestmark = pytest.mark.setup_a                           # Arduino #1 OFF, Python sends 0x123

FAKE_SPEED = 100


def read_lines_for(dashboard, seconds):
    lines = []
    end = time.time() + seconds
    while time.time() < end:
        line = dashboard.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    return lines


def count(lines, text):
    return len([l for l in lines if text in l])


def fake_frames(kind):
    if kind == "naive":                        # counter 0, checksum 0 (hand-built on purpose)
        return can.Message(arbitration_id=config.SPEED_MSG_ID,
                           data=[0, FAKE_SPEED, 0, 0, 0, 0, 0, 0], is_extended_id=False)
    return frames.speed_frames(FAKE_SPEED)     # smart: correct checksum + its own counter


@pytest.mark.parametrize("kind", ["naive", "smart"])
def test_tc18_fake_sender_after_real_ecu_dies(can_bus, dashboard, kind):
    real = can_bus.send_periodic(frames.speed_frames(50), config.CYCLE_TIME_S)
    dashboard.reset_input_buffer()
    before = read_lines_for(dashboard, 2)                  # phase 1: real ECU alone

    fake = can_bus.send_periodic(fake_frames(kind), config.CYCLE_TIME_S)
    both = read_lines_for(dashboard, 1)                    # phase 2: both on the bus (read, don't sleep)

    real.stop()                                            # phase 3: the real ECU dies
    takeover = read_lines_for(dashboard, 2)
    settled = read_lines_for(dashboard, 3)
    fake.stop()

    after = takeover + settled
    print(f"\n[{kind}] before: 50 x{count(before, 'Speed = 50')} | "
           f"both: {len(both)} lines | "
          f"takeover: LOST {count(takeover, 'SIGNAL LOST')}, 100 x{count(takeover, 'Speed = 100')} | "
          f"settled: LOST {count(settled, 'SIGNAL LOST')}, 100 x{count(settled, 'Speed = 100')}")
    print("first takeover lines:", takeover[:6])

    assert count(before, "Speed = 50") >= 10, "real ECU not displayed before the test - is Arduino #1 OFF?"
    if kind == "naive":
        assert count(after, "SIGNAL LOST") >= 1, "dead ECU NOT detected - naive fake masked it"
        assert count(after, "Speed = 100") == 0, "naive fake value DISPLAYED"
    else:
        assert count(settled, "Speed = 100") >= 20, "smart fake not accepted - masking not reproduced"
        assert count(settled, "SIGNAL LOST") == 0, "LOST in the settled phase - masking not reproduced"