"""TC-09 - Bitrate mismatch at the tester (v2, 3-node bench)

Requirement: REQ-005 (all nodes 500 kbit/s), REQ-009 (wiring/config faults: no damage, recovery)
Purpose   : a node at the wrong bitrate reads every bit at the wrong moment. Shows what the
            tester receives, what the other nodes notice, and that the bus recovers.
Setup     : B - Arduino #1 ON (PSU), Dashboard COM6, CANable COM5 (opened by the test itself).
Steps     : 1. CANable closed, read the Dashboard 1 s.
            2. CANable at 250 kbit/s (WRONG) for 5 s: count valid 0x123, read the Dashboard.
            3. CANable at 500 kbit/s for 3 s: count valid 0x123, read the Dashboard.
Pass when : before: Dashboard shows 50 | fault: 0 valid 0x123 at the tester
            recovery: >= 25 valid 0x123, Dashboard shows 50, no SIGNAL LOST
Observed  : the Dashboard during the fault is printed, not asserted (no requirement for it).
History   : v1 (2026-10-09) assumed a 2-node bench ("Send error" at the sender) - outdated.
"""
import time
import can
import pytest
import config
import frames

pytestmark = pytest.mark.setup_b                           # Arduino #1 ON

WRONG_BITRATE = 250000
FAULT_S = 5.0
RECOVER_S = 3.0


def valid_speed_frames(bitrate, seconds):
    """Open the CANable at 'bitrate', return (valid 0x123 frames, number of all other frames)."""
    bus = can.Bus(interface=config.CAN_INTERFACE, channel=config.CAN_CHANNEL, bitrate=bitrate)
    good, other = [], 0
    try:
        end = time.time() + seconds
        while time.time() < end:
            msg = bus.recv(timeout=0.2)
            if msg is None:
                continue
            if (msg.arbitration_id == config.SPEED_MSG_ID and msg.dlc == 8
                    and frames.decode_speed(msg.data)["Checksum"] == frames.checksum(msg.data)):
                good.append(msg)
            else:
                other += 1
    finally:
        bus.shutdown()
    return good, other


def dashboard_text(dashboard):
    """Everything the Dashboard printed since the last reset_input_buffer()."""
    return dashboard.read(dashboard.in_waiting).decode(errors="ignore")


def test_tc09_wrong_bitrate_then_recovery(dashboard):
    dashboard.reset_input_buffer()
    time.sleep(1)
    before = dashboard_text(dashboard)                     # step 1: CANable closed

    dashboard.reset_input_buffer()
    fault_good, fault_other = valid_speed_frames(WRONG_BITRATE, FAULT_S)
    fault = dashboard_text(dashboard)                      # step 2: wrong bitrate

    dashboard.reset_input_buffer()
    rec_good, rec_other = valid_speed_frames(config.CAN_BITRATE, RECOVER_S)
    rec = dashboard_text(dashboard)                        # step 3: back to 500k

    print(f"\nbefore  : Speed=50 x{before.count('Speed = 50')}")
    print(f"fault   : tester valid 0x123 {len(fault_good)}, other frames {fault_other} | Dashboard: "
          f"Speed=50 x{fault.count('Speed = 50')}, LOST {fault.count('SIGNAL LOST')}, "
          f"CHECKSUM {fault.count('CHECKSUM ERROR')}, COUNTER {fault.count('COUNTER ERROR')}")
    print(f"recovery: tester valid 0x123 {len(rec_good)}, other frames {rec_other} | Dashboard: "
          f"Speed=50 x{rec.count('Speed = 50')}, LOST {rec.count('SIGNAL LOST')}")

    assert before.count("Speed = 50") >= 5, "Dashboard not showing 50 before the test - is Arduino #1 ON?"
    assert len(fault_good) == 0, f"{len(fault_good)} valid 0x123 received at the WRONG bitrate"
    assert len(rec_good) >= 25, f"only {len(rec_good)} valid 0x123 after going back to 500 kbit/s"
    assert rec.count("Speed = 50") >= 20, "Dashboard not showing 50 after recovery"
    assert rec.count("SIGNAL LOST") == 0, "SIGNAL LOST after recovery"