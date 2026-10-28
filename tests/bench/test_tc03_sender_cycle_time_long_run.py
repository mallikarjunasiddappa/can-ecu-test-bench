"""TC-03 (long run) - The sender ECU keeps its 100 ms cycle for 3 minutes

Requirement: REQ-002 - VehicleSpeed cycle time 100 ms +-10 % (90-110 ms)
Purpose   : the 5 s test finds a sender that is always too slow or too fast. Rare outliers - one
            late frame every minute or two - only show up over many frames (about 1800 here).
Setup     : B - Arduino #1 ON (data-grade cable, ENV-003); Python only listens. About 3 min.
Warm-up   : 1 s is skipped first. When the CANable starts listening, the sender's 3 queued frames
            (sent while nobody ACKed) come out back to back - that start-up burst is TC-12, not TC-03.
Steps     : 1. Drain old frames, skip 1 s. 2. Listen 180 s, keep the timestamp of every 0x123.
Pass when : - at least 1700 frames
            - every gap 90-110 ms (outliers are listed in the message)
History   : replaces the manual script cycle_check.py (Run 4 2026-10-09: 1791 frames,
            98.0-103.1 ms, 0 outside). Automated 2026-10-28.
"""
import time
import pytest
import config

pytestmark = [pytest.mark.setup_b, pytest.mark.long]       # Arduino #1 ON, 3 min - not in the quick regression

WARM_UP_S = 1.0
DURATION_S = 180.0
MIN_MS, MAX_MS = 90, 110                                   # REQ-002: 100 ms +-10 %


def test_tc03_cycle_time_over_3_minutes(can_bus):
    while can_bus.recv(timeout=0.01) is not None:          # drain frames queued before the test
        pass
    end_warm_up = time.time() + WARM_UP_S
    while time.time() < end_warm_up:                       # skip the start-up burst (TC-12)
        can_bus.recv(timeout=0.1)

    stamps = []
    end = time.time() + DURATION_S
    while time.time() < end:
        msg = can_bus.recv(timeout=0.5)
        if msg is not None and msg.arbitration_id == config.SPEED_MSG_ID:
            stamps.append(msg.timestamp)

    gaps_ms = [(b - a) * 1000 for a, b in zip(stamps, stamps[1:])]
    outside = [(round(t - stamps[0], 3), round(g, 1)) for t, g in zip(stamps[1:], gaps_ms) if not MIN_MS <= g <= MAX_MS]
    print(f"\n{len(stamps)} frames in {DURATION_S:.0f} s, gap min {min(gaps_ms):.1f}  max {max(gaps_ms):.1f}  "
          f"avg {sum(gaps_ms) / len(gaps_ms):.1f} ms, outside {MIN_MS}-{MAX_MS} ms: {len(outside)}")

    assert len(stamps) >= 1700, f"only {len(stamps)} frames in {DURATION_S:.0f} s"
    assert outside == [], f"{len(outside)} gaps outside {MIN_MS}-{MAX_MS} ms (time s, gap ms): {outside[:10]}"