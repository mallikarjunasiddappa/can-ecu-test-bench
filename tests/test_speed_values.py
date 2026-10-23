# test_speed_values.py - REQ-003: byte 1 of 0x123 = vehicle speed, 1 km/h per bit
import time
import can
import pytest
import config
import frames

SPEEDS = [0, 1, 50, 100, 249, 250]   # boundary values of one byte (0x00..0xFF) + typical values


@pytest.mark.parametrize("speed", SPEEDS)
def test_dashboard_shows_sent_speed(can_bus, dashboard, speed):
    msg = frames.speed_frames(speed)   # counter + checksum (REQ-011/012)
    task = can_bus.send_periodic(msg, config.CYCLE_TIME_S)
    time.sleep(1)                                  # let frames arrive
    dashboard.reset_input_buffer()                 # ignore start-up / RESTORED lines
    lines = [dashboard.readline().decode(errors="ignore").strip() for _ in range(5)]
    task.stop()
    expected = f"Speed = {speed} km/h"             # expected value CALCULATED from the input
    print(f"sent 0x{speed:02X} -> {lines}")
    assert expected in lines
