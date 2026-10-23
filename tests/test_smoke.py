# test_smoke.py - does the Dashboard ECU boot with the expected software version?
import config


def test_dashboard_boots_with_expected_version(dashboard):
    print(dashboard.boot_text)
    assert f"Dashboard ECU {config.DASHBOARD_SW_VERSION}: MCP2515 ready" in dashboard.boot_text
