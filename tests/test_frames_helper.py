# test_frames_helper.py - unit test of OUR test tool (frames.py) on a virtual bus - no hardware needed
import time
import can
import frames


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

    counters = [f[0] for f in got]
    rollovers = sum(1 for a, b in zip(counters, counters[1:]) if a == 15 and b == 0)
    print(f"\n{len(got)} frames, first: {got[0].hex(' ')}, counters: {counters}, rollovers: {rollovers}")

    assert got[0].hex(" ") == "00 32 00 00 00 00 00 32"
    assert all(f[7] == (sum(f[0:7]) & 0xFF) for f in got)
    assert all(b == (a + 1) % 16 for a, b in zip(counters, counters[1:]))
    assert rollovers >= 1