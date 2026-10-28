# ecu_simulator.py - a tiny UDS ECU (ISO 14229) for testing - logic only, no CAN yet

DEFAULT_SESSION = 0x01                                                    # NEW
EXTENDED_SESSION = 0x03                                                   # NEW


class EcuSimulator:
    def __init__(self):
        self.session = DEFAULT_SESSION         # every power-on starts in the default session   NEW
        self.dids = {
            0xF189: b"0.5",                    # ECU software version (ASCII)
            0xF190: b"YV1ABCD1234567890",      # VIN, 17 characters (ASCII)
        }
        self.writable = {0xF189}               # DIDs the tester may write (extended session only)   NEW

    def handle(self, request: bytes) -> bytes:
        """Answer one UDS request (bytes in) with one UDS response (bytes out)."""
        sid = request[0]
        if sid == 0x10:                                                   # NEW
            return self.session_control(request)                          # NEW
        if sid == 0x22:
            return self.read_data(request)
        if sid == 0x2E:                                                   # NEW
            return self.write_data(request)                               # NEW
        return bytes([0x7F, sid, 0x11])        # NRC 0x11 serviceNotSupported

    def session_control(self, request: bytes) -> bytes:                   # NEW method
        """0x10 DiagnosticSessionControl: 10 <session>."""
        if len(request) != 2:
            return bytes([0x7F, 0x10, 0x13])   # NRC 0x13 incorrectMessageLength
        session = request[1]
        if session not in (DEFAULT_SESSION, EXTENDED_SESSION):
            return bytes([0x7F, 0x10, 0x12])   # NRC 0x12 subFunctionNotSupported
        self.session = session
        return bytes([0x50, session, 0x00, 0x32, 0x01, 0xF4])   # + timing: P2 = 50 ms, P2* = 5000 ms

    def read_data(self, request: bytes) -> bytes:
        """0x22 ReadDataByIdentifier: 22 <DID high> <DID low>."""
        if len(request) != 3:
            return bytes([0x7F, 0x22, 0x13])   # NRC 0x13 incorrectMessageLength
        did = request[1] * 256 + request[2]    # two bytes -> one number, e.g. F1 89 -> 0xF189
        if did not in self.dids:
            return bytes([0x7F, 0x22, 0x31])   # NRC 0x31 requestOutOfRange
        return bytes([0x62, request[1], request[2]]) + self.dids[did]

    def write_data(self, request: bytes) -> bytes:                        # NEW method
        """0x2E WriteDataByIdentifier: 2E <DID high> <DID low> <data ...>."""
        if self.session != EXTENDED_SESSION:
            return bytes([0x7F, 0x2E, 0x7F])   # NRC 0x7F serviceNotSupportedInActiveSession
        if len(request) < 4:
            return bytes([0x7F, 0x2E, 0x13])   # NRC 0x13 incorrectMessageLength (no data)
        did = request[1] * 256 + request[2]
        if did not in self.writable:
            return bytes([0x7F, 0x2E, 0x31])   # NRC 0x31 requestOutOfRange (not writable)
        self.dids[did] = request[3:]           # store the new value
        return bytes([0x6E, request[1], request[2]])