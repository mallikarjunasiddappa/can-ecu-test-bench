"""Unit test (no hardware) - a real UDS client (udsoncan) talks to the ECU simulator over ISO-TP

Purpose   : test the simulator the way a diagnostic tester does: udsoncan builds the requests,
            ISO-TP carries them as CAN frames on 0x7E0 / 0x7E8 (virtual bus), the ECU server answers.
            This checks all three layers together: UDS logic, ISO-TP transport, client decoding.
Setup     : none - python-can virtual bus; about 1 s.
Pass when : positive answers decode to the expected values; refused requests raise
            NegativeResponseException with the expected NRC.
"""
import can
import isotp
import pytest
import udsoncan
from udsoncan.client import Client
from udsoncan.configs import default_client_config
from udsoncan.connections import PythonIsoTpConnection
from udsoncan.exceptions import NegativeResponseException
from uds.ecu_server import EcuServer, REQUEST_ID, RESPONSE_ID


@pytest.fixture
def uds_client():
    ecu_bus = can.Bus(interface="virtual", channel="uds_test")
    tester_bus = can.Bus(interface="virtual", channel="uds_test")
    server = EcuServer(ecu_bus)
    server.start()                                                     # ECU powered on

    address = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=RESPONSE_ID, txid=REQUEST_ID)
    stack = isotp.CanStack(tester_bus, address=address, params={"tx_padding": 0x00})
    config = default_client_config.copy()                               # udsoncan defaults (timeouts etc.)
    config["data_identifiers"] = {
        0xF189: udsoncan.AsciiCodec(3),        # software version: 3 ASCII characters ("0.5")
        0xF190: udsoncan.AsciiCodec(17),       # VIN: 17 ASCII characters
    }
    with Client(PythonIsoTpConnection(stack), config=config) as client:
        yield client                                                   # the test runs here

    server.stop()
    ecu_bus.shutdown()
    tester_bus.shutdown()


def test_read_software_version(uds_client):
    response = uds_client.read_data_by_identifier(0xF189)
    assert response.service_data.values[0xF189] == "0.5"


def test_read_vin(uds_client):
    response = uds_client.read_data_by_identifier(0xF190)
    assert response.service_data.values[0xF190] == "YV1ABCD1234567890"


def test_write_in_default_session_is_refused(uds_client):
    with pytest.raises(NegativeResponseException) as error:
        uds_client.write_data_by_identifier(0xF189, "0.6")
    assert error.value.response.code == 0x7F          # serviceNotSupportedInActiveSession


def test_write_in_extended_session_and_read_back(uds_client):
    uds_client.change_session(0x03)                    # extended session
    uds_client.write_data_by_identifier(0xF189, "0.6")
    response = uds_client.read_data_by_identifier(0xF189)
    assert response.service_data.values[0xF189] == "0.6"