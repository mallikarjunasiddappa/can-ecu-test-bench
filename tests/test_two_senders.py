# test_two_senders.py - Step 4 / Exp A: two senders with different IDs share the bus
import time
import can
import pytest
import config

OTHER_ID = 0x200            # second sender (Python) - lower priority than 0x123
DURATION_S = 5


@pytest.mark.parametrize("second_sender", [False, True], ids=["baseline", "with_0x200"])
def test_two_senders_coexist(can_bus, dashboard, second_sender):
    # Drain old frames: CANable kept receiving while the dashboard fixture slept 2 s
    old = 0
    while can_bus.recv(timeout=0.01) is not None:
        old += 1
    print(f"\nDrained {old} old frames from the receive buffer")
    task = None
    if second_sender:                                  # only in the 2nd run: Python also sends 0x200
        other = can.Message(arbitration_id=OTHER_ID, data=[0xAA] * 8, is_extended_id=False)
        task = can_bus.send_periodic(other, config.CYCLE_TIME_S)

    stamps = []                                        # arrival times of 0x123 from Arduino #1
    end = time.time() + DURATION_S
    while time.time() < end:
        msg = can_bus.recv(timeout=0.5)
        if msg is not None and msg.arbitration_id == config.SPEED_MSG_ID:
            stamps.append(msg.timestamp)
    if task:
        task.stop()

    text = dashboard.read(dashboard.in_waiting).decode(errors="ignore")

    assert len(stamps) >= DURATION_S * 9, f"only {len(stamps)} frames of 0x123 received"
    gaps_ms = [(b - a) * 1000 for a, b in zip(stamps, stamps[1:])]
    bad = [round(g, 1) for g in gaps_ms[1:] if not 90 <= g <= 110]
    print(f"\n[{'with 0x200' if second_sender else 'baseline'}] 0x123 frames: {len(stamps)}  "
          f"gap min {min(gaps_ms[1:]):.1f}  max {max(gaps_ms[1:]):.1f} ms  outside 90-110: {bad}")
    print("Dashboard: LOST =", text.count("SPEED SIGNAL LOST"), " INVALID =", text.count("INVALID"))

    assert not bad, "0x123 cycle time outside 90-110 ms (REQ-002)"
    assert "SPEED SIGNAL LOST" not in text, "Dashboard lost 0x123 (REQ-007)"
    assert "Speed = 50 km/h" in text