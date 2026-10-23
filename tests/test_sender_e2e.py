# test_sender_e2e.py - Step 5: Arduino #1 (sender v0.2) follows REQ-011 (alive counter) + REQ-012 (checksum)
import time
import config

DURATION_S = 3      # ~30 frames = about 2 full counter cycles (0..15)


def test_sender_counter_and_checksum(can_bus):
    while can_bus.recv(timeout=0.01) is not None:          # drain old frames
        pass

    frames = []
    end = time.time() + DURATION_S
    while time.time() < end:
        msg = can_bus.recv(timeout=0.5)
        if msg is not None and msg.arbitration_id == config.SPEED_MSG_ID:
            frames.append(bytes(msg.data))

    counters = [f[0] for f in frames]
    bad_cs = [f.hex(" ") for f in frames if f[7] != (sum(f[0:7]) & 0xFF)]
    bad_seq = [(a, b) for a, b in zip(counters, counters[1:]) if b != (a + 1) % 16]
    rollovers = sum(1 for a, b in zip(counters, counters[1:]) if a == 15 and b == 0)

    print(f"\n{len(frames)} frames, counters: {counters}")
    print(f"example frame: {frames[0].hex(' ')}")
    print(f"checksum errors: {bad_cs}  counter errors: {bad_seq}  rollovers 15->0: {rollovers}")

    assert len(frames) >= DURATION_S * 9, "too few frames"
    assert not bad_cs, "REQ-012: checksum wrong"
    assert not bad_seq, "REQ-011: counter does not go +1"
    assert rollovers >= 1, "REQ-011: rollover 15 -> 0 not seen"