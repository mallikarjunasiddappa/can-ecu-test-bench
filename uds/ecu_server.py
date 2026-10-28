# ecu_server.py - puts the UDS ECU simulator on a CAN bus: ISO-TP on 0x7E0 (requests) / 0x7E8 (responses)
import threading
import can
import isotp
from uds.ecu_simulator import EcuSimulator

REQUEST_ID = 0x7E0     # tester -> ECU
RESPONSE_ID = 0x7E8    # ECU -> tester


class EcuServer:
    def __init__(self, bus: can.BusABC):
        address = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=REQUEST_ID, txid=RESPONSE_ID)
        self.stack = isotp.CanStack(bus, address=address, params={"tx_padding": 0x00})
        self.ecu = EcuSimulator()
        self.running = False
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def start(self):
        self.stack.start()                     # ISO-TP's own background thread (frames, flow control)
        self.running = True
        self.thread.start()                    # our thread: whole UDS requests -> handle() -> response

    def serve(self):
        while self.running:
            request = self.stack.recv(block=True, timeout=0.1)    # a complete UDS message, or None
            if request is not None:
                self.stack.send(self.ecu.handle(bytes(request)))

    def stop(self):
        self.running = False
        self.thread.join()
        self.stack.stop()