"""TC-15 - Invalid or out-of-range speed is never displayed as a number

Requirement: REQ-010 - 0-250 valid; 251-253 out of range; 0xFE = error; 0xFF = not available
Purpose   : safety - a wrong value must never look like a real speed to the driver.
Setup     : A - Arduino #1 OFF; Python sends 0x123.
Data      : 251, 253, 0xFE, 0xFF (one test per value)
Fault injection: frames built with strict=False, because vehicle.dbc forbids 251-253
            (cantools would raise EncodeError and nothing would be sent).
Steps     : 1. Send the invalid value every 100 ms for 1 s.
            2. Clear the serial buffer, read 5 lines.
Pass when : - no line matches "Speed = <number> km/h"
            - at least one "SPEED SIGNAL INVALID" line
History   : Run 1 on Dashboard v0.2 failed 4/4 -> DEF-002 (0xFB-0xFF shown as real speeds);
            fixed in v0.3 (MAX_VALID_SPEED = 250).
"""
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
