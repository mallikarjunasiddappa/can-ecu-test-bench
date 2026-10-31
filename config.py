# config.py - all bench settings in ONE place (change here, never inside tests)

# CAN interface: CANable 2.0 with slcan firmware
CAN_INTERFACE = "slcan"
CAN_CHANNEL = "COM5"
CAN_BITRATE = 500000          # 500 kbit/s

# Dashboard ECU (Arduino #2): USB serial port
DASHBOARD_PORT = "COM6"       # check in Device Manager if it changes
DASHBOARD_BAUD = 115200       # must match Serial.begin(115200) in the sketch

# Sender ECU (Arduino #1): USB serial port - only for tests that reset the sender (TC-05, TC-06)
SENDER_PORT = "COM4"          # hub port 4 (location 1-3.4); opening it RESETS Arduino #1
SENDER_BAUD = 115200

# Message and timing (REQ-003, REQ-007)
SPEED_MSG_ID = 0x123
CYCLE_TIME_S = 0.100          # sender cycle: 100 ms
TIMEOUT_MS = 300              # REQ-007: 3 missed cycles -> SIGNAL LOST
DASHBOARD_SW_VERSION = "v0.5"   # expected software after flashing
