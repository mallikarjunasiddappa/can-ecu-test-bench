"""TC-02 - The sender ECU transmits VehicleSpeed as ID 0x123, DLC 8, standard 11-bit ID

Requirement: REQ-001 - VehicleSpeed on standard (11-bit) ID 0x123 with DLC 8
Purpose   : the most basic message check - right ID, right length, right ID format. Every other
            test (decoding, timing, E2E) assumes this is true.
Setup     : B - Arduino #1 ON (sends 0x123); Python only listens; the Dashboard is not needed.
Expected  : taken from vehicle.dbc (VehicleSpeed_Msg), not typed into the test.
Steps     : 1. Drain old frames. 2. Listen 1 s and keep every frame.
Pass when : - at least 8 frames received
            - every frame has the DBC ID 0x123 (the sender sends nothing else)
            - every frame has DLC 8 and a standard (not extended) ID
History   : manual runs 2026-09-30 and 2026-10-08 with can.viewer (PASS) -> automated 2026-10-28.
"""
import time
import pytest
import frames

pytestmark = pytest.mark.setup_b                           # Arduino #1 ON

MSG = frames.DB.get_message_by_name("VehicleSpeed_Msg")    # the expected values come from the DBC

def test_tc02_id_dlc_and_standard_id(can_bus):
    while can_bus.recv(timeout=0.01) is not None:          # drain frames queued before the test
        pass

    received = []
    end = time.time() + 1.0
    while time.time() < end:
        msg = can_bus.recv(timeout=0.5)
        if msg is not None:
            received.append(msg)

    ids = sorted({m.arbitration_id for m in received})
    print(f"\n{len(received)} frames, IDs seen: {[hex(i) for i in ids]}, "
          f"DLCs: {sorted({m.dlc for m in received})}, extended: {sorted({m.is_extended_id for m in received})}")

    assert len(received) >= 8, f"only {len(received)} frames in 1 s - is Arduino #1 ON?"
    assert ids == [MSG.frame_id], f"expected only ID {MSG.frame_id:#05x}, saw {[hex(i) for i in ids]}"
    assert all(m.dlc == MSG.length for m in received), f"DLC not {MSG.length} in every frame"
    assert all(m.is_extended_id == MSG.is_extended_frame for m in received), "extended ID used - REQ-001 needs 11-bit"