# frames.py - builds 0x123 VehicleSpeed frames with alive counter (REQ-011) + checksum (REQ-012)
import can
import config


def checksum(data):
    """REQ-012: sum of bytes 0..6, keep only the last byte."""
    return sum(data[0:7]) & 0xFF


def speed_frame(speed, counter):
    """One 0x123 frame: byte 0 = counter 0..15, byte 1 = speed, byte 7 = checksum."""
    data = [counter % 16, speed, 0, 0, 0, 0, 0, 0]
    data[7] = checksum(data)
    return can.Message(arbitration_id=config.SPEED_MSG_ID, data=data, is_extended_id=False)


def speed_frames(speed):
    """16 frames with counter 0..15 - send_periodic sends them one by one, in a loop."""
    return [speed_frame(speed, c) for c in range(16)]