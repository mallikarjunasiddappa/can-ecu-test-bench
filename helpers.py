"""bench_helpers.py - shared helpers for the bench tests (CAN bus + Dashboard serial).

Fixtures that open and close the hardware live in conftest.py; these are plain functions
the tests import, like frames.py.
"""
import time
import config
import frames


def drain(can_bus):
    """Throw away frames that queued up in the CANable before the test starts listening.
    Returns how many were thrown away (some tests report it)."""
    thrown_away = 0
    while can_bus.recv(timeout=0.01) is not None:
        thrown_away += 1
    return thrown_away


def read_lines_for(dashboard, seconds):
    """Collect every line the Dashboard prints during 'seconds'."""
    lines = []
    end = time.time() + seconds
    while time.time() < end:
        line = dashboard.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    return lines


def dashboard_text(dashboard):
    """Everything the Dashboard printed since the last reset_input_buffer(), as one text."""
    return dashboard.read(dashboard.in_waiting).decode(errors="ignore")


def count(lines, text):
    """How many lines contain 'text'."""
    return len([line for line in lines if text in line])


def measure(can_bus, dashboard, seconds):
    """Listen at the tester and the Dashboard at the same time.
    Returns (valid 0x123 frames, number of damaged 0x123 frames, Dashboard text)."""
    drain(can_bus)
    dashboard.reset_input_buffer()
    good, bad = [], 0
    end = time.time() + seconds
    while time.time() < end:
        msg = can_bus.recv(timeout=0.2)
        if msg is None or msg.arbitration_id != config.SPEED_MSG_ID:
            continue
        if msg.dlc == 8 and frames.decode_speed(msg.data)["Checksum"] == frames.checksum(msg.data):
            good.append(msg)
        else:
            bad += 1
    return good, bad, dashboard_text(dashboard)


def assert_dashboard_ok(text, min_speed_lines=80):
    """The Dashboard showed 50 km/h continuously, with no LOST and no E2E errors."""
    assert text.count("Speed = 50") >= min_speed_lines, "Dashboard did not show 50 km/h continuously"
    assert text.count("SIGNAL LOST") == 0, "SIGNAL LOST at the Dashboard"
    assert text.count("CHECKSUM ERROR") + text.count("COUNTER ERROR") == 0, "E2E errors at the Dashboard"