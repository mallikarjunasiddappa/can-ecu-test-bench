"""TC-14 / TC-15 - The exact boundary between valid and invalid speed (round 2, test 6)

Requirement: REQ-010 - 0-250 valid, 251-253 out of range, 0xFE error, 0xFF not available
Purpose   : 250 / 251 is the pair that catches both off-by-one bugs (">= 250" and "> 251").
            Checks the EXACT line the Dashboard prints, not just "a number or not".
Setup     : A - Arduino #1 OFF; Python sends 0x123.
Data      : 249, 250 (valid) and 251, 253, 0xFE, 0xFF (invalid), each with its expected line.
Fault injection: strict=False, because vehicle.dbc forbids 251-253.
Steps     : send the value 1 s, clear buffer, read 1 s.
Pass when : - at least 8 lines, every line exactly the expected one
            - an invalid value is never shown as a number
Notes     : requirement review - REQ-010 names two meanings (error / not available) but defines
            one reaction.
"""
import re
import time
import pytest
import config
import frames

MAX_VALID_SPEED = 250                              # REQ-010: 0–250 valid
NUMBER_SHOWN = re.compile(r"Speed = \d+ km/h")     # a number, NOT "Speed = --- km/h"

CASES = [
    (249,  "Speed = 249 km/h"),
    (250,  "Speed = 250 km/h"),
    #(250,  "SPEED SIGNAL INVALID (raw 0xFA) -> Speed = --- km/h"),   # red check
    (251,  "SPEED SIGNAL INVALID (raw 0xFB) -> Speed = --- km/h"),
    (253,  "SPEED SIGNAL INVALID (raw 0xFD) -> Speed = --- km/h"),
    (0xFE, "SPEED SIGNAL INVALID (raw 0xFE) -> Speed = --- km/h"),
    (0xFF, "SPEED SIGNAL INVALID (raw 0xFF) -> Speed = --- km/h"),
]
IDS = ["249_valid", "250_last_valid", "251_first_invalid", "253_out_of_range", "FE_error", "FF_not_available"]

def read_line_for(dashboard, seconds):
    lines = []
    end = time.time() + seconds
    while time.time() < end:
        line = dashboard.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    return lines

@pytest.mark.parametrize("raw, expected", CASES, ids=IDS)
def test_speed_boundary(can_bus, dashboard, raw, expected):
    task = can_bus.send_periodic(frames.speed_frames(raw, strict=False), config.CYCLE_TIME_S)   # crosses the 250 boundary on purpose
    time.sleep(1)
    dashboard.reset_input_buffer()
    lines = read_line_for(dashboard, 1.0)
    task.stop()
    print(f"\nsent {raw} (0x{raw:02X}) -> {len(lines)} lines, first: {lines[:1]}")

    # Criterion 1: enough lines to trust the result
    assert len(lines) >= 8, f"only {len(lines)} lines for {raw}"

    # Criterion 2: every line is exactly the expected one
    wrong = [l for l in lines if l != expected]
    assert wrong == [], f"expected every line '{expected}', got: {wrong}"

    # Criterion 3 (safety): an invalid value is never shown as a number
    if raw > MAX_VALID_SPEED:
        shown = [l for l in lines if NUMBER_SHOWN.search(l)]
        assert shown == [], f"invalid 0x{raw:02X} displayed as a number: {shown}"