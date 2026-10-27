"""Support test - the Dashboard displays a speed sent by Python

Test case : support (no workbook TC) - proves Python can act as the sender ECU
Requirement: REQ-003 (speed in byte 1), REQ-011 / REQ-012 (frames carry counter + checksum)
Purpose   : before Python-driven tests are trusted, show that a frame built by the framework
            (frames.speed_frames, from vehicle.dbc) is accepted and displayed by the Dashboard.
Setup     : A - Arduino #1 OFF; Python sends 0x123 through the CANable (COM5).
Steps     : 1. Send 100 km/h every 100 ms (16 frames, alive counter 0..15).
            2. Wait 1 s, clear the serial buffer, read 10 Dashboard lines.
Pass when : "Speed = 100 km/h" is among the lines.
"""
import time
import can
import config
import frames


def test_dashboard_shows_speed_sent_by_python(can_bus, dashboard):
    msg = frames.speed_frames(0x64)   # 100 km/h, counter + checksum (REQ-011/012)
    task = can_bus.send_periodic(msg, config.CYCLE_TIME_S)  # every 100 ms, in background
    time.sleep(1)                                           # let frames arrive
    dashboard.reset_input_buffer()                          # ignore start-up lines
    lines = [dashboard.readline().decode(errors="ignore").strip() for _ in range(10)]
    task.stop()
    print(lines)
    assert "Speed = 100 km/h" in lines
