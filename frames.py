# frames.py - builds 0x123 VehicleSpeed frames with alive counter (REQ-011) + checksum (REQ-012)
import can
import cantools
import config
from pathlib import Path

DB = cantools.database.can.Database()
DB.add_dbc_file(Path(__file__).parent / "vehicle.dbc")

def checksum(data):
    """REQ-012: sum of bytes 0..6, keep only the last byte."""
    return sum(data[0:7]) & 0xFF


def speed_frame(speed, counter):
    """One 0x123 frame: byte 0 = counter 0..15, byte 1 = speed, byte 7 = checksum."""
    data = [counter % 16, speed, 0, 0, 0, 0, 0, 0]
    data[7] = checksum(data)
    return can.Message(arbitration_id=config.SPEED_MSG_ID, data=data, is_extended_id=False)

def speed_frames(speed, strict=True):
    """16 frames with counter 0..15, built from vehicle.dbc - send_periodic sends them one by one, in a loop."""
    return [speed_frame_dbc(speed, c, strict) for c in range(16)]

def speed_frame_dbc(speed, counter, strict=True):
    """Same frame as speed_frame(), but built from vehicle.dbc by signal name."""
    msg = DB.get_message_by_name("VehicleSpeed_Msg")
    signals = {"AliveCounter": counter % 16, "VehicleSpeed": speed, "Checksum": 0}
    data = msg.encode(signals, strict=strict)
    signals["Checksum"] = checksum(data)
    data = msg.encode(signals, strict=strict)
    return can.Message(arbitration_id=msg.frame_id, data=data, is_extended_id=False)

def decode_speed(data) -> dict[str, int]:
    """Decode one 0x123 payload with vehicle.dbc -> raw numbers by signal name (no VAL_ names)."""
    decoded = DB.get_message_by_name("VehicleSpeed_Msg").decode(bytes(data), decode_choices=False)
    assert isinstance(decoded, dict), "0x123 decoded to an unexpected type"
    result = {}
    for name, value in decoded.items():
        assert isinstance(value, (int, float)), f"{name} decoded to {value!r}, expected a number"
        result[name] = int(value)
    return result

def damage_checksum(frame):
    """Fault injection: a copy of a 0x123 frame with Checksum + 1, changed by signal name via vehicle.dbc."""
    signals = decode_speed(frame.data)
    signals["Checksum"] = (signals["Checksum"] + 1) & 0xFF
    data = DB.get_message_by_name("VehicleSpeed_Msg").encode(signals, strict=False)
    return can.Message(arbitration_id=frame.arbitration_id, data=data, is_extended_id=False)