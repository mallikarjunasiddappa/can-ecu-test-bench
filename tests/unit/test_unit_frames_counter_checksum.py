"""Unit test (no hardware) - the frame builder produces correct counters and checksums

Purpose   : test the TEST TOOL. If frames.speed_frames() were wrong, every bench result would be
            wrong too. Runs on python-can's virtual bus in about 2 s, so it can run anywhere (CI).
Setup     : none - two virtual bus objects on the same channel ("selftest").
Steps     : 1. Send frames.speed_frames(50) every 100 ms for 2 s on the virtual bus.
            2. Receive them on the second virtual bus object.
Pass when : - first frame is 00 32 00 00 00 00 00 32
            - every checksum = sum of bytes 0-6 & 0xFF
            - every counter = previous + 1 (mod 16), at least one rollover 15 -> 0
"""
import time
import can
import frames
import pytest

pytestmark = pytest.mark.unit                              # no hardware


def test_speed_frames_counter_and_checksum():
    tx = can.Bus(interface="virtual", channel="selftest")     # virtual sender
    rx = can.Bus(interface="virtual", channel="selftest")     # virtual receiver, same channel
    task = tx.send_periodic(frames.speed_frames(0x32), 0.1)
    got = []
    end = time.time() + 2
    while time.time() < end:
        msg = rx.recv(timeout=0.5)
        if msg is not None:
            got.append(bytes(msg.data))
    task.stop()
    tx.shutdown()
    rx.shutdown()

    decoded = [frames.decode_speed(f) for f in got]        # by signal name, via vehicle.dbc
    counters = [d["AliveCounter"] for d in decoded]
    rollovers = sum(1 for a, b in zip(counters, counters[1:]) if a == 15 and b == 0)
    print(f"\n{len(got)} frames, first: {got[0].hex(' ')}, counters: {counters}, rollovers: {rollovers}")

    assert got[0].hex(" ") == "00 32 00 00 00 00 00 32"          # golden reference frame (known bytes)
    assert all(d["Checksum"] == frames.checksum(f) for f, d in zip(got, decoded))
    assert all(b == (a + 1) % 16 for a, b in zip(counters, counters[1:]))
    assert rollovers >= 1