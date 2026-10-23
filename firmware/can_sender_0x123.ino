// Fake ECU #1 — sends CAN ID 0x123 every 100 ms — v0.2 (2026-10-14): alive counter byte 0 + checksum byte 7 (REQ-011/012)
// Hardware: Arduino Uno clone + MCP2515 module (HW-184, 8 MHz crystal)
// Wiring: VCC-5V, GND-GND, CS-D10, SO-D12, SI-D11, SCK-D13, INT-D2
// Library: mcp_can by coryjfowler (v1.5.1)
#include <SPI.h>
#include <mcp_can.h>

MCP_CAN CAN0(10);   // MCP2515 CS pin is on Arduino pin 10
byte aliveCounter = 0;   // REQ-011: 0..15, +1 per frame
void setup() {
  Serial.begin(115200);
  // 500 kbps bus speed, 8 MHz crystal (what we read on the module)
  if (CAN0.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) == CAN_OK) {
    Serial.println("MCP2515 ready");
  } else {
    Serial.println("MCP2515 init FAILED");
    while (1);   // stop here if the chip didn't start
  }
  CAN0.setMode(MCP_NORMAL);
}

void loop() {
  // Byte 0 = alive counter, byte 1 = 0x32 = 50 km/h, byte 7 = checksum
  byte data[8] = {aliveCounter, 0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};

  byte sum = 0;                          // REQ-012: checksum = sum of bytes 0..6
  for (int i = 0; i < 7; i++) {
    sum += data[i];                      // a 'byte' wraps at 256 automatically = & 0xFF
  }
  data[7] = sum;

  if (CAN0.sendMsgBuf(0x123, 0, 8, data) == CAN_OK) {
    Serial.print("Sent 0x123 ctr=");
    Serial.print(aliveCounter);
    Serial.print(" cs=0x");
    Serial.println(data[7], HEX);
  } else {
    Serial.println("Send error");
  }
  aliveCounter = (aliveCounter + 1) % 16;   // 0..15, then back to 0
  delay(100);
}
