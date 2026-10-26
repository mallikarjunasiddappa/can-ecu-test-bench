# analyze_trace.py - read a .asc trace of 0x123, decode with vehicle.dbc, check REQ-012 / REQ-011 / REQ-002
import sys
import can
import config
import frames

path = sys.argv[1]                                    # trace file given on the command line
frames_0x123 = [m for m in can.ASCReader(path) if m.arbitration_id == config.SPEED_MSG_ID]
decoded = [frames.decode_speed(m.data) for m in frames_0x123]
print(f"{path}: {len(frames_0x123)} frames of 0x123")

for m, d in list(zip(frames_0x123, decoded))[:5]:     # first 5, decoded by signal name
    print(f"{m.timestamp:9.6f}  {d}")

# --- checks ---
errors = []
for i, (m, d) in enumerate(zip(frames_0x123, decoded)):
    if d["Checksum"] != frames.checksum(m.data):                                   # REQ-012
        errors.append(f"{m.timestamp:9.6f}  CHECKSUM byte 7 = {d['Checksum']}, expected {frames.checksum(m.data)}")
    if i == 0:
        continue                                                                   # 1st frame has no previous
    expected = (decoded[i - 1]["AliveCounter"] + 1) % 16                           # REQ-011
    if d["AliveCounter"] != expected:
        errors.append(f"{m.timestamp:9.6f}  COUNTER expected {expected}, got {d['AliveCounter']}")
    gap_ms = (m.timestamp - frames_0x123[i - 1].timestamp) * 1000                 # REQ-002
    if not 90 <= gap_ms <= 110:
        errors.append(f"{m.timestamp:9.6f}  GAP {gap_ms:.1f} ms (allowed 90-110)")

print(f"checks: {len(errors)} errors")
for e in errors:
    print("  " + e)
sys.exit(1 if errors else 0)