# demo_vin_over_isotp.py - tester reads the VIN from the ECU simulator over ISO-TP on a virtual CAN bus
import time
import can
import isotp
from uds.ecu_server import EcuServer, REQUEST_ID, RESPONSE_ID

ecu_bus = can.Bus(interface="virtual", channel="uds_demo")      # the ECU's connection
tester_bus = can.Bus(interface="virtual", channel="uds_demo")   # the tester's connection
spy_bus = can.Bus(interface="virtual", channel="uds_demo")      # only listens, sees every frame

server = EcuServer(ecu_bus)
server.start()                                                  # ECU "powered on"

address = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=RESPONSE_ID, txid=REQUEST_ID)   # reversed!
tester = isotp.CanStack(tester_bus, address=address, params={"tx_padding": 0x00})
tester.start()

tester.send(bytes.fromhex("22 F1 90"))                          # UDS request: read the VIN
answer = tester.recv(block=True, timeout=2)                     # complete UDS answer, glued by ISO-TP
print("UDS answer:", answer.hex(" ") if answer else None)

time.sleep(0.1)
print("\nCAN frames on the bus:")
while (frame := spy_bus.recv(timeout=0.05)) is not None:
    print(f"  {frame.arbitration_id:03X}   {frame.data.hex(' ')}")

tester.stop()
server.stop()
for bus in (ecu_bus, tester_bus, spy_bus):
    bus.shutdown()