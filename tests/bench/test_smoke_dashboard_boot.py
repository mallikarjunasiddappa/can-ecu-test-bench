"""Smoke test - Dashboard ECU boots with the expected software version

Test case : smoke (bench check, run first in every session)
Purpose   : prove the bench is alive and the device under test runs the expected firmware
            before any other test is trusted. A wrong or missing version means every later
            result would be about the wrong software.
Setup     : A or B. Dashboard ECU on COM6. No CAN traffic needed.
Steps     : 1. The `dashboard` fixture opens the serial port (this resets the Arduino).
            2. The boot text printed in the first 2 s is captured.
Pass when : the boot text contains "Dashboard ECU <config.DASHBOARD_SW_VERSION>: MCP2515 ready".
Notes     : "MCP2515 init FAILED" instead = SPI wiring problem (ENV-002 type).
"""
import pytest
import config

pytestmark = [pytest.mark.setup_a, pytest.mark.smoke]         # bench check, Setup A

def test_dashboard_boots_with_expected_version(dashboard):
    print(dashboard.boot_text)
    assert f"Dashboard ECU {config.DASHBOARD_SW_VERSION}: MCP2515 ready" in dashboard.boot_text
