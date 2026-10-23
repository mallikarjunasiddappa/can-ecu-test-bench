import time
import serial
import config
import frames

SENDER_PORT = "COM6"      # Arduino #1 on PC USB, socket 1-4, for THIS test only (not the Dashboard!)
LIMIT_S = 2.0             # REQ-004: first 0x123 within 2 s after power-up

def test_sender_startup_time(can_bus):
    # Bus is already open (fixture) -> CANable ACKs. Throw away old frames.
    while can_bus.recv(timeout=0.01) is not None:
        pass

    # "Power-on": opening the sender's COM port resets Arduino #1
    # ASSUMPTION: a reset via the COM port is not a true power-on (the bootloader waits first)
    #             -> the measured time is probably a bit LONGER than a real power-on
    t0 = time.time()
    sender = serial.Serial(SENDER_PORT, 115200)

    # Wait for the first 0x123 after the reset (give up after 5 s)
    first, t1 = None, None
    while time.time() < t0 + 5:
        msg = can_bus.recv(timeout=0.5)
        if msg is None or msg.arbitration_id != config.SPEED_MSG_ID:
            continue
        if time.time() - t0 < 0.05:          # was already on its way BEFORE the reset
            continue
        first, t1 = msg, time.time()
        break

    # Cyclic sending started? Count 0x123 frames in the next 1 s
    more = 0
    end = time.time() + 1.0
    while time.time() < end:
        msg = can_bus.recv(timeout=0.5)
        if msg is not None and msg.arbitration_id == config.SPEED_MSG_ID:
            more += 1
    sender.close()

    # Criterion 1: first frame within 2 s
    assert first is not None and t1 is not None, "no 0x123 within 5 s after the reset"
    startup_s = t1 - t0
    data = list(first.data)
    print(f"\nstart-up {startup_s:.3f} s, first frame {[hex(b) for b in data]}, then {more} frames in 1 s")
    assert startup_s <= LIMIT_S, f"first 0x123 after {startup_s:.3f} s (limit {LIMIT_S} s)"

    # Criterion 2: a fresh, valid frame
    assert data[0] == 0, f"first frame counter {data[0]}, expected 0 (not from the fresh start?)"
    assert data[1] == 0x32, f"speed byte {data[1]:#04x}, expected 0x32"
    assert data[7] == frames.checksum(data), f"checksum {data[7]:#04x}, expected {frames.checksum(data):#04x}"

    # Criterion 3: cyclic sending has begun
    assert more >= 8, f"only {more} frames in the 1 s after the first"