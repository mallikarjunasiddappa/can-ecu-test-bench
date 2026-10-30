"""TC-08 - One terminator missing, bench powered (v2, 3-node bench)

Requirement: REQ-006 (bus terminated at both ends, 60 ohm), REQ-009 (no damage, recovery)
Purpose   : a terminator pulls the bus back to recessive and absorbs reflections. With only one,
            does the bus still work? On a short bench bus it probably does; on a long car bus
            it often gives intermittent errors.
Setup     : B (Arduino #1 ON, Dashboard COM6, CANable COM5). Run this test TWICE by hand:
            run 1 FAULT    - J1 jumper removed on MCP2515 #1 (power OFF first) -> about 120 ohm
            run 2 RECOVERY - J1 refitted (power OFF first)                     -> about 60 ohm
Steps     : measure 10 s at the tester (CANable) and the Dashboard at the same time.
Pass when : >= 90 valid 0x123, every gap 90-110 ms, Dashboard "Speed = 50" >= 80,
            no SIGNAL LOST / CHECKSUM ERROR / COUNTER ERROR.
            Run 1 = bench expectation only: REQ-009 does not say what happens DURING the fault.
History   : v1 (2026-10-09) steps 1, 2, 4 measured (118.6 / 59.7 ohm), step 3 never run.
"""
import time
import pytest
import config
import frames

pytestmark = pytest.mark.setup_b                           # Arduino #1 ON

MEASURE_S = 10.0


def test_tc08_bus_health_for_10_s(can_bus, dashboard):
    while can_bus.recv(timeout=0.01) is not None:          # drain old frames
        pass
    dashboard.reset_input_buffer()

    good, bad = [], 0
    end = time.time() + MEASURE_S
    while time.time() < end:
        msg = can_bus.recv(timeout=0.2)
        if msg is None or msg.arbitration_id != config.SPEED_MSG_ID:
            continue
        if msg.dlc == 8 and frames.decode_speed(msg.data)["Checksum"] == frames.checksum(msg.data):
            good.append(msg)
        else:
            bad += 1

    text = dashboard.read(dashboard.in_waiting).decode(errors="ignore")
    gaps = [(b.timestamp - a.timestamp) * 1000 for a, b in zip(good, good[1:])]
    outside = [round(g, 1) for g in gaps if not 90 <= g <= 110]

    gap_range = f"{min(gaps):.1f}-{max(gaps):.1f} ms" if gaps else "none"
    print(f"\ntester   : valid 0x123 {len(good)}, bad {bad}, gaps {gap_range}, outside {outside}")
    print(f"dashboard: Speed=50 x{text.count('Speed = 50')}, LOST {text.count('SIGNAL LOST')}, "
          f"CHECKSUM {text.count('CHECKSUM ERROR')}, COUNTER {text.count('COUNTER ERROR')}")

    assert len(good) >= 90, f"only {len(good)} valid 0x123 in {MEASURE_S} s"
    assert bad == 0, f"{bad} damaged 0x123 frames at the tester"
    assert outside == [], f"gaps outside 90-110 ms: {outside}"
    assert text.count("Speed = 50") >= 80, "Dashboard did not show 50 km/h continuously"
    assert text.count("SIGNAL LOST") == 0, "SIGNAL LOST at the Dashboard"
    assert text.count("CHECKSUM ERROR") + text.count("COUNTER ERROR") == 0, "E2E errors at the Dashboard"