"""bus_load.py - CAN bus load of the bench, calculated from frame transmission time.

Builds each 0x123 frame (counters 0..15, from vehicle.dbc) bit by bit as it appears on the
wire: standard data frame, CRC-15, stuff bits, fixed tail and interframe space.
Bus load = bits per second on the bus / bitrate.
"""
import config
import frames

CRC15_POLY = 0x4599                           # CAN CRC-15 polynomial (ISO 11898-1)


def bits_of(value, width):
    return format(value, f"0{width}b")        # bits_of(5, 4) -> "0101"


def crc15(bits):
    crc = 0
    for b in bits:
        top = ((crc >> 14) & 1) ^ int(b)
        crc = (crc << 1) & 0x7FFF
        if top:
            crc ^= CRC15_POLY
    return crc


def stuff_bit_count(bits):
    count, run, last = 0, 0, None
    for b in bits:
        if b == last:
            run += 1
        else:
            last, run = b, 1
        if run == 5:                          # 5 equal bits -> the sender inserts the opposite bit
            count += 1
            last, run = ("1" if b == "0" else "0"), 1    # the stuff bit starts the next run
    return count


def frame_bits_on_wire(msg):
    """Bit times of one standard data frame: stuffed part + stuff bits + fixed tail."""
    head = "0" + bits_of(msg.arbitration_id, 11) + "0" + "0" + "0" + bits_of(msg.dlc, 4)
    #      SOF   identifier                     RTR   IDE   r0    DLC
    stuffed = head + "".join(bits_of(b, 8) for b in msg.data)
    stuffed += bits_of(crc15(stuffed), 15)    # SOF .. CRC = the part that gets stuffed
    stuff = stuff_bit_count(stuffed)
    tail = 1 + 1 + 1 + 7 + 3                  # CRC delimiter, ACK slot, ACK delimiter, EOF, interframe space
    return len(stuffed) + stuff + tail, stuff


if __name__ == "__main__":
    msgs = frames.speed_frames(50)            # the 16 frames Arduino #1 sends (counter 0..15)
    totals = []
    for m in msgs:
        total, stuff = frame_bits_on_wire(m)
        totals.append(total)
        print(f"{bytes(m.data).hex(' ')}   stuff bits {stuff:2}   bits on wire {total}")

    avg_bits = sum(totals) / len(totals)
    frames_per_s = 1 / config.CYCLE_TIME_S
    frame_us = avg_bits / config.CAN_BITRATE * 1e6
    load = avg_bits * frames_per_s / config.CAN_BITRATE * 100
    print(f"\naverage {avg_bits:.1f} bits = {frame_us:.0f} µs per frame; "
          f"{frames_per_s:.0f} frames/s -> bus load {load:.3f} %")