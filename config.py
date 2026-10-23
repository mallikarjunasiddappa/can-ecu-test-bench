# config.py - all bench settings in ONE place (change here, never inside tests)

# CAN interface: CANable 2.0 with slcan firmware
CAN_INTERFACE = "slcan"
CAN_CHANNEL = "COM5"
CAN_BITRATE = 500000          # 500 kbit/s

# Dashboard ECU (Arduino #2): USB serial port
DASHBOARD_PORT = "COM6"       # check in Device Manager if it changes
DASHBOARD_BAUD = 115200       # must match Serial.begin(115200) in the sketch

# Message and timing (REQ-003, REQ-007)
SPEED_MSG_ID = 0x123
CYCLE_TIME_S = 0.100          # sender cycle: 100 ms
TIMEOUT_MS = 300              # REQ-007: 3 missed cycles -> SIGNAL LOST
DASHBOARD_SW_VERSION = "v0.5"   # expected software after flashing
