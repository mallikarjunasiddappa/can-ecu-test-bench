"""TC-03 (short) - The sender ECU transmits 0x123 every 100 ms +-10 %

Requirement: REQ-002 - VehicleSpeed cycle time 100 ms +-10 % (90-110 ms)
Purpose   : cycle time is one of the most common CAN tests. A late or drifting sender makes
            receivers time out or show stale values.
Setup     : B - Arduino #1 ON (data-grade cable - see ENV-003); Python only listens.
Steps     : 1. Drain old frames. 2. Listen 5 s, keep the timestamp of every 0x123.
Pass when : - at least 45 frames
            - every gap 90-110 ms
            - average gap 95-105 ms (ASSUMPTION: drift check; REQ-002 limits single gaps only)
History   : first run "0 frames" -> ENV-003 (sender silent on a charge-only cable); the
            3-minute version of TC-03 is cycle_check.py (manual).
"""
import time
import config

DURATION_S = 5
MIN_MS, MAX_MS = 90, 110          # REQ-002: 100 ms ± 10 %

def test_sender_cycle_time(can_bus):
    # Drain: frames buffered since the bus was opened have old timestamps
    drained = 0
    while can_bus.recv(timeout=0.01) is not None:
        drained += 1

    # Listen 5 s, keep only 0x123
    stamps = []
    end = time.time() + DURATION_S
    while time.time() < end:
        msg = can_bus.recv(timeout=0.5)
        if msg is not None and msg.arbitration_id == config.SPEED_MSG_ID:
            stamps.append(msg.timestamp)

    # Criterion 1: enough frames (also needed before min/max can work)
    assert len(stamps) >= 45, f"only {len(stamps)} frames of 0x123 in {DURATION_S} s"

    gaps_ms = [(b - a) * 1000 for a, b in zip(stamps, stamps[1:])]
    avg_ms = sum(gaps_ms) / len(gaps_ms)
    print(f"\ndrained {drained}, frames {len(stamps)}, gap min {min(gaps_ms):.1f}  "
          f"max {max(gaps_ms):.1f}  avg {avg_ms:.1f} ms")

    # Criterion 2: every gap inside REQ-002
    bad = [round(g, 1) for g in gaps_ms if not MIN_MS <= g <= MAX_MS]
    assert bad == [], f"{len(bad)} gaps outside {MIN_MS}–{MAX_MS} ms: {bad}"

    # Criterion 3: no drift
    # ASSUMPTION: REQ-002 limits each gap only; average 95–105 ms used as a drift check
    assert 95 <= avg_ms <= 105, f"average gap {avg_ms:.1f} ms (drift)"