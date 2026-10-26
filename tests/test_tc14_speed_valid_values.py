"""TC-14 - Speed decoding: every valid value is displayed exactly as sent

Requirement: REQ-003 - byte 1 of 0x123 = vehicle speed, 1 km/h per bit (valid 0-250, REQ-010)
Purpose   : boundary-value test of the decoding - the smallest values, typical values and the
            last valid value must all reach the display unchanged.
Setup     : A - Arduino #1 OFF; Python sends 0x123.
Data      : 0, 1, 50, 100, 249, 250 (one test per value, parametrize)
Steps     : 1. Send the value every 100 ms for 1 s.
            2. Clear the serial buffer, read 5 lines.
Pass when : "Speed = <value> km/h" is among the lines (expected value calculated from the input).
History   : 254/255 were in the list until REQ-010 made them special values -> changed to 249/250.
"""
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
