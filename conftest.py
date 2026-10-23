# conftest.py - shared fixtures. pytest loads this file automatically.
import time
import pytest
import serial
import config
import can


@pytest.fixture
def dashboard():
    """Open the Dashboard ECU serial port before a test, close it after."""
    port = serial.Serial(config.DASHBOARD_PORT, config.DASHBOARD_BAUD, timeout=1)
    time.sleep(2)               # opening the port RESETS the Arduino -> wait for it to boot
    port.boot_text = port.read(port.in_waiting).decode(errors="ignore")  # keep start-up text (empties the buffer too)
    yield port                  # ----- the test runs here -----
    port.close()                # teardown: always runs, even if the test fails



@pytest.fixture
def can_bus():
    """Open the CANable (our test interface) before a test, close it after."""
    bus = can.Bus(interface=config.CAN_INTERFACE,
                  channel=config.CAN_CHANNEL,
                  bitrate=config.CAN_BITRATE)
    yield bus
    bus.shutdown()   # teardown: release COM port + stop any periodic sending
