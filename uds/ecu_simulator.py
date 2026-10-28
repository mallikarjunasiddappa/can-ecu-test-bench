# ecu_simulator.py - a tiny UDS ECU (ISO 14229) for testing - logic only, no CAN yet

class EcuSimulator:
    def __init__(self):
        self.dids = {
            0xF189: b"0.5",                    # ECU software version (ASCII)
            0xF190: b"YV1ABCD1234567890",      # VIN, 17 characters (ASCII)
        }

    def handle(self, request: bytes) -> bytes:
        """Answer one UDS request (bytes in) with one UDS response (bytes out)."""
        sid = request[0]
        if sid == 0x22:
            return self.read_data(request)
        return bytes([0x7F, sid, 0x11])        # NRC 0x11 serviceNotSupported

    def read_data(self, request: bytes) -> bytes:
        """0x22 ReadDataByIdentifier: 22 <DID high> <DID low>."""
        if len(request) != 3:
            return bytes([0x7F, 0x22, 0x13])   # NRC 0x13 incorrectMessageLength
        did = request[1] * 256 + request[2]    # two bytes -> one number, e.g. F1 89 -> 0xF189
        if did not in self.dids:
            return bytes([0x7F, 0x22, 0x31])   # NRC 0x31 requestOutOfRange
        return bytes([0x62, request[1], request[2]]) + self.dids[did]