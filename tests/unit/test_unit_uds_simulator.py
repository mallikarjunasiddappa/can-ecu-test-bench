"""Unit test (no hardware) - the UDS ECU simulator answers by the ISO 14229 rules

Purpose   : before any tester talks to the simulator over CAN, prove its "brain" (handle) gives
            the right positive and negative responses. Pure Python, no CAN, about 0.1 s.
Data      : one row per rule - request bytes in, expected response bytes out.
Pass when : every response is exactly the expected one.
"""
import pytest
from uds.ecu_simulator import EcuSimulator

CASES = [
    # request      expected response                                   rule
    ("22 F1 89",   "62 F1 89 30 2E 35"),                               # read software version "0.5"
    ("22 F1 90",   "62 F1 90 59 56 31 41 42 43 44 31 32 33 34 35 36 37 38 39 30"),   # read VIN
    ("22 12 34",   "7F 22 31"),                                        # unknown DID -> requestOutOfRange
    ("22 F1",      "7F 22 13"),                                        # too short -> incorrectMessageLength
    ("22 F1 89 00", "7F 22 13"),                                       # too long  -> incorrectMessageLength
    ("10 03",      "7F 10 11"),                                        # service not implemented yet
]
IDS = ["sw_version", "vin", "unknown_did", "too_short", "too_long", "unknown_service"]


@pytest.mark.parametrize("request_hex, expected_hex", CASES, ids=IDS)
def test_simulator_response(request_hex, expected_hex):
    ecu = EcuSimulator()
    response = ecu.handle(bytes.fromhex(request_hex))
    assert response == bytes.fromhex(expected_hex), f"{request_hex} -> {response.hex(' ')}, expected {expected_hex}"