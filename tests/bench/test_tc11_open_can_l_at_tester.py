"""TC-11 - Open CAN-L wire at the tester (v2, 3-node bench)

Requirement: REQ-009 (wiring faults: no damage, recovery)
Purpose   : high-speed CAN reads the DIFFERENCE between CAN-H and CAN-L. With CAN-L open at the
            CANable, its L follows H through its own terminator -> difference ~0 V -> it sees an
            idle bus. The other two nodes still have both wires and one terminator (as TC-08).
Setup     : B. Two tests, run by hand:
            fault    (special) - black CAN-L wire removed from the CANable terminal (power OFF first)
            recovery (setup_b) - wire reconnected (power OFF first) = normal wiring
Pass when : fault    - tester 0 valid and 0 damaged 0x123; Dashboard Speed = 50 >= 80, no errors
            recovery - tester >= 90 valid, 0 damaged; Dashboard Speed = 50 >= 80, no errors
History   : v1 (2026-10-09) assumed a 2-node bench ("Send error" at the sender) - outdated.
"""
import time
import pytest
import config
import frames

MEASURE_S = 10.0


def measure(can_bus, dashboard, seconds):
    """Listen at the tester and the Dashboard at the same time; return (valid, damaged, dashboard text)."""
    while can_bus.recv(timeout=0.01) is not None:          # drain old frames
        pass
    dashboard.reset_input_buffer()
    good, bad = [], 0
    end = time.time() + seconds
    while time.time() < end:
        msg = can_bus.recv(timeout=0.2)
        if msg is None or msg.arbitration_id != config.SPEED_MSG_ID:
            continue
        if msg.dlc == 8 and frames.decode_speed(msg.data)["Checksum"] == frames.checksum(msg.data):
            good.append(msg)
        else:
            bad += 1
    text = dashboard.read(dashboard.in_waiting).decode(errors="ignore")
    print(f"\ntester   : valid 0x123 {len(good)}, damaged {bad}")
    print(f"dashboard: Speed=50 x{text.count('Speed = 50')}, LOST {text.count('SIGNAL LOST')}, "
          f"CHECKSUM {text.count('CHECKSUM ERROR')}, COUNTER {text.count('COUNTER ERROR')}")
    return good, bad, text


def dashboard_ok(text):
    assert text.count("Speed = 50") >= 80, "Dashboard did not show 50 km/h continuously"
    assert text.count("SIGNAL LOST") == 0, "SIGNAL LOST at the Dashboard"
    assert text.count("CHECKSUM ERROR") + text.count("COUNTER ERROR") == 0, "E2E errors at the Dashboard"


@pytest.mark.special                                       # CAN-L wire OPEN at the CANable
def test_tc11_fault_can_l_open(can_bus, dashboard):
    good, bad, text = measure(can_bus, dashboard, MEASURE_S)
    assert len(good) == 0, f"tester received {len(good)} valid 0x123 - is CAN-L really open?"
    assert bad == 0, f"tester received {bad} damaged 0x123"
    dashboard_ok(text)


@pytest.mark.setup_b                                       # normal wiring
def test_tc11_recovery_can_l_reconnected(can_bus, dashboard):
    good, bad, text = measure(can_bus, dashboard, MEASURE_S)
    assert len(good) >= 90, f"only {len(good)} valid 0x123 in {MEASURE_S} s"
    assert bad == 0, f"tester received {bad} damaged 0x123"
    dashboard_ok(text)