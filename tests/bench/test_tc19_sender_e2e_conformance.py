"""TC-19 - The sender ECU (Arduino #1, v0.2) follows the E2E rules

Requirement: REQ-011 (alive counter +1 per frame, 15 -> 0) and REQ-012 (checksum in byte 7)
Purpose   : test the SENDER side - before testing how the Dashboard reacts to E2E errors, prove
            the real sender produces correct counters and checksums.
Setup     : B - Arduino #1 ON; Python only listens (no Dashboard needed).
Steps     : 1. Drain old frames, then record every 0x123 for 3 s (about 30 frames).
Pass when : - at least 27 frames
            - every checksum = (byte 0 + ... + byte 6) & 0xFF
            - every counter = previous + 1 (mod 16)
            - at least one rollover 15 -> 0 seen
"""
import time
import config
import frames
import pytest

pytestmark = pytest.mark.setup_b                           # Arduino #1 ON

DURATION_S = 3      # ~30 frames = about 2 full counter cycles (0..15)


def test_sender_counter_and_checksum(can_bus):
    while can_bus.recv(timeout=0.01) is not None:          # drain old frames
        pass

    received = []                                         # raw payloads of every 0x123
    end = time.time() + DURATION_S
    while time.time() < end:
        msg = can_bus.recv(timeout=0.5)
        if msg is not None and msg.arbitration_id == config.SPEED_MSG_ID:
            received.append(bytes(msg.data))

    decoded = [frames.decode_speed(f) for f in received]   # by signal name, via vehicle.dbc
    counters = [d["AliveCounter"] for d in decoded]
    bad_cs = [f.hex(" ") for f, d in zip(received, decoded) if d["Checksum"] != frames.checksum(f)]
    bad_seq = [(a, b) for a, b in zip(counters, counters[1:]) if b != (a + 1) % 16]
    rollovers = sum(1 for a, b in zip(counters, counters[1:]) if a == 15 and b == 0)

    print(f"\n{len(received)} frames, counters: {counters}")
    print(f"example frame: {received[0].hex(' ')}")
    print(f"checksum errors: {bad_cs}  counter errors: {bad_seq}  rollovers 15->0: {rollovers}")

    assert len(received) >= DURATION_S * 9, "too few frames"
    assert not bad_cs, "REQ-012: checksum wrong"
    assert not bad_seq, "REQ-011: counter does not go +1"
    assert rollovers >= 1, "REQ-011: rollover 15 -> 0 not seen"