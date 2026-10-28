"""Unit test (no hardware) - the UDS ECU simulator answers by the ISO 14229 rules

Purpose   : before any tester talks to the simulator over CAN, prove its "brain" (handle) gives
            the right positive and negative responses. Pure Python, no CAN, about 0.1 s.
Data      : one row per rule - request bytes in, expected response bytes out (fresh ECU each row),
            plus sequences for the session rules (the ECU remembers its session between requests).
Pass when : every response is exactly the expected one.
"""
import pytest
from uds.ecu_simulator import EcuSimulator

pytestmark = pytest.mark.unit                              # no hardware

CASES = [
    # request          expected response                                   rule
    ("22 F1 89",       "62 F1 89 30 2E 35"),                               # read software version "0.5"
    ("22 F1 90",       "62 F1 90 59 56 31 41 42 43 44 31 32 33 34 35 36 37 38 39 30"),   # read VIN
    ("22 12 34",       "7F 22 31"),                                        # unknown DID -> requestOutOfRange
    ("22 F1",          "7F 22 13"),                                        # too short -> incorrectMessageLength
    ("22 F1 89 00",    "7F 22 13"),                                        # too long  -> incorrectMessageLength
    ("11 01",          "7F 11 11"),                                        # ECUReset not implemented -> serviceNotSupported
    ("10 03",          "50 03 00 32 01 F4"),                               # switch to extended session
    ("10 09",          "7F 10 12"),                                        # session 09 does not exist -> subFunctionNotSupported
    ("2E F1 89 30 2E 36", "7F 2E 7F"),                                     # write in DEFAULT session -> not in this session
]
IDS = ["sw_version", "vin", "unknown_did", "too_short", "too_long", "unknown_service",
       "extended_session", "unknown_session", "write_in_default"]


@pytest.mark.parametrize("request_hex, expected_hex", CASES, ids=IDS)
def test_simulator_response(request_hex, expected_hex):
    ecu = EcuSimulator()                                   # fresh ECU = fresh power-on
    response = ecu.handle(bytes.fromhex(request_hex))
    assert response == bytes.fromhex(expected_hex), f"{request_hex} -> {response.hex(' ')}, expected {expected_hex}"


def send(ecu, request_hex):
    """One request to the same ECU, response as hex text (easy to compare)."""
    return ecu.handle(bytes.fromhex(request_hex)).hex(" ").upper()


def test_write_in_extended_session_is_stored():
    ecu = EcuSimulator()
    assert send(ecu, "10 03") == "50 03 00 32 01 F4"               # 1. switch to extended
    assert send(ecu, "2E F1 89 30 2E 36") == "6E F1 89"            # 2. write "0.6" -> accepted
    assert send(ecu, "22 F1 89") == "62 F1 89 30 2E 36"            # 3. read back -> "0.6"


def test_back_to_default_blocks_writing_again():
    ecu = EcuSimulator()
    send(ecu, "10 03")                                             # extended
    assert send(ecu, "10 01") == "50 01 00 32 01 F4"               # back to default
    assert send(ecu, "2E F1 89 30 2E 36") == "7F 2E 7F"            # writing refused again


def test_vin_is_not_writable():
    ecu = EcuSimulator()
    send(ecu, "10 03")
    assert send(ecu, "2E F1 90 59 56 31") == "7F 2E 31"            # VIN is read-only here