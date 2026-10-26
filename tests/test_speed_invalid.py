# test_speed_invalid.py - TC-15 / REQ-010: invalid or out-of-range speed must not be displayed as a number
import re
import time
import can
import pytest
import config
import frames

INVALID_SPEEDS = [251, 253, 0xFE, 0xFF]          # out of range (251-253), error (0xFE), not available (0xFF)
NUMBER_SHOWN = re.compile(r"Speed = \d+ km/h")   # matches e.g. "Speed = 255 km/h", NOT "Speed = --- km/h"


@pytest.mark.parametrize("raw", INVALID_SPEEDS)
def test_dashboard_rejects_invalid_speed(can_bus, dashboard, raw):
    msg = frames.speed_frames(raw, strict=False)   # fault injection: invalid values on purpose (REQ-010)
    task = can_bus.send_periodic(msg, config.CYCLE_TIME_S)
    time.sleep(1)
    dashboard.reset_input_buffer()
    lines = [dashboard.readline().decode(errors="ignore").strip() for _ in range(5)]
    task.stop()
    print(f"sent 0x{raw:02X} ({raw}) -> {lines}")

    # Expected 1: no number is displayed for an invalid value
    shown = [l for l in lines if NUMBER_SHOWN.search(l)]
    assert not shown, f"invalid value 0x{raw:02X} displayed as a number: {shown[0]}"

    # Expected 2: the ECU reports the invalid signal
    assert any("SPEED SIGNAL INVALID" in l for l in lines), "no 'SPEED SIGNAL INVALID' message"
