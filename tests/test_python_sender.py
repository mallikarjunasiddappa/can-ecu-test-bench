# test_python_sender.py - Python (via CANable) is now the speed sender ECU
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
