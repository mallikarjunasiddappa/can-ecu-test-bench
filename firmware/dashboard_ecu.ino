// Dashboard ECU (node 3) — receives CAN ID 0x123 and shows vehicle speed
// Version: v0.5 (2026-10-16) — E2E protection: alive counter (REQ-011 v3) + checksum (REQ-012)
//   v0.1: receive + decode only (no reaction when 0x123 stops -> stale speed)  [backup: dashboard_ecu_v0_1_backup.txt]
//   v0.2: if no 0x123 for more than 300 ms -> "SPEED SIGNAL LOST"; back -> "SPEED SIGNAL RESTORED" (REQ-007)
//   v0.3: speed > 250 -> "SPEED SIGNAL INVALID", shown as "---" (REQ-010, DEF-002)
//   v0.4: byte 7 checksum + byte 0 alive counter checked; only E2E-valid frames reset the timeout clock;
//         first frame after start / LOST = reference; speed shown only after 2 consecutive good frames
//   v0.5: DEF-003 fix (REQ-011 v3): right after a CHECKSUM ERROR the next correct frame may be +1 OR +2
//         (the damaged frame used up one counter value); tolerance for that ONE frame only  [backup: dashboard_ecu_v0_4_backup.txt]
// Hardware: Arduino Uno clone #2 + MCP2515 module #2 (HW-184, 8 MHz crystal, J1 OPEN = no terminator)
// Wiring:   VCC-5V, GND-GND, CS-D10, SO-D12, SI-D11, SCK-D13, INT-D2
// Library:  mcp_can by coryjfowler
// Signal:   0x123 byte 0 = alive counter 0..15, byte 1 = speed km/h, byte 7 = checksum (sum of bytes 0..6)
#include <SPI.h>
#include <mcp_can.h>

const int CAN_INT_PIN = 2;                    // MCP2515 pulls INT LOW when a received frame is waiting
const unsigned long SPEED_MSG_ID = 0x123;
const unsigned long TIMEOUT_MS = 300;         // REQ-007: 3 x 100 ms cycle time
const int MAX_VALID_SPEED = 250;              // REQ-010: 0-250 valid, above = invalid
MCP_CAN CAN0(10);                             // CS on pin 10

unsigned long lastSpeedRxMs = 0;              // time of the last E2E-VALID 0x123 frame (v0.4)
unsigned long lossStartMs = 0;                // NEW v0.4: time of the last valid frame before LOST
bool signalLost = false;                      // true while we are in the "timeout" state
bool haveRef = false;                         // NEW v0.4 (REQ-011): do we have a reference counter?
byte lastCounter = 0;                         // NEW v0.4: counter of the last accepted frame
byte goodInRow = 0;                           // NEW v0.4: consecutive E2E-good frames (display needs 2)
bool afterCsError = false;                    // NEW v0.5 (REQ-011 v3): last frame was a CHECKSUM ERROR -> allow +2 once

void setup() {
  Serial.begin(115200);
  if (CAN0.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) == CAN_OK) {
    Serial.println("Dashboard ECU v0.5: MCP2515 ready");
  } else {
    Serial.println("Dashboard ECU v0.5: MCP2515 init FAILED");   // = SPI wiring problem
    while (1);
  }
  CAN0.setMode(MCP_NORMAL);
  pinMode(CAN_INT_PIN, INPUT);
  lastSpeedRxMs = millis();                   // start the timeout clock now
}

void loop() {
  // 1) Receive
  if (digitalRead(CAN_INT_PIN) == LOW) {
    unsigned long id;
    byte len;
    byte data[8];
    CAN0.readMsgBuf(&id, &len, data);

    if ((id & 0x1FFFFFFF) == SPEED_MSG_ID && len == 8) {
      byte sum = 0;                           // REQ-012: checksum = sum of bytes 0..6
      for (int i = 0; i < 7; i++) {
        sum += data[i];
      }
      byte counter = data[0];                 // REQ-011: alive counter 0..15
      byte expected = (lastCounter + 1) % 16;
      byte expected2 = (lastCounter + 2) % 16;   // NEW v0.5: allowed only right after a CHECKSUM ERROR
      bool counterOk = (counter == expected) || (afterCsError && counter == expected2);   // NEW v0.5

      if (sum != data[7]) {                   // corrupted -> NOT a valid reception
        Serial.print("SPEED SIGNAL CHECKSUM ERROR (byte 7 = 0x");
        Serial.print(data[7], HEX);
        Serial.print(", expected 0x");
        Serial.print(sum, HEX);
        Serial.println(") -> Speed = --- km/h");
        goodInRow = 0;
        afterCsError = true;                  // NEW v0.5: next correct frame may be +1 or +2
      } else if (haveRef && !counterOk) {    // wrong sequence -> NOT valid (v0.5: uses counterOk)
        Serial.print("SPEED SIGNAL COUNTER ERROR (expected ");
        Serial.print(expected);
        if (afterCsError) {                   // NEW v0.5: show both allowed values
          Serial.print(" or ");
          Serial.print(expected2);
        }
        Serial.print(", got ");
        Serial.print(counter);
        Serial.println(") -> Speed = --- km/h");
        lastCounter = counter;                // resync: this frame is the new reference
        goodInRow = 0;
        afterCsError = false;                 // NEW v0.5: tolerance used up
      } else {                                // E2E OK (or first frame = reference)
        afterCsError = false;                 // NEW v0.5: tolerance used up
        lastSpeedRxMs = millis();             // only VALID frames reset the timeout clock
        haveRef = true;
        lastCounter = counter;
        if (goodInRow < 2) {
          goodInRow++;
        }
        if (goodInRow >= 2) {                 // 2 consecutive good frames -> trust the value
          if (signalLost) {
            Serial.print("SPEED SIGNAL RESTORED (signal was missing for ");
            Serial.print(millis() - lossStartMs);
            Serial.println(" ms)");
            signalLost = false;
          }
          int speed = data[1];                // decode: raw byte -> km/h (factor 1, offset 0)
          if (speed > MAX_VALID_SPEED) {      // REQ-010
            Serial.print("SPEED SIGNAL INVALID (raw 0x");
            Serial.print(speed, HEX);
            Serial.println(") -> Speed = --- km/h");
          } else {
            Serial.print("Speed = ");
            Serial.print(speed);
            Serial.println(" km/h");
          }
        }
      }
    }
  }

  // 2) Monitor: no VALID 0x123 for more than 300 ms -> LOST (REQ-007)
  if (!signalLost && (millis() - lastSpeedRxMs > TIMEOUT_MS)) {
    signalLost = true;
    lossStartMs = lastSpeedRxMs;
    haveRef = false;                          // NEW v0.4: after LOST, next frame = new reference
    goodInRow = 0;
    afterCsError = false;                     // NEW v0.5
    Serial.print("SPEED SIGNAL LOST (no 0x123 for ");
    Serial.print(millis() - lastSpeedRxMs);
    Serial.println(" ms) -> Speed = --- km/h");
  }
}
