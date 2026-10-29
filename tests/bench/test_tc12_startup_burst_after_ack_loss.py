"""TC-12 - Start-up burst: queued frames after a period with no ACK

Requirement: none yet - requirement gap (raise with the requirement owner)
Purpose   : when no node ACKs, the sender's frames stay in the MCP2515's 3 transmit buffers. When a
            receiver joins, those OLD frames go out back to back, then the normal 100 ms rhythm
            resumes. In a car, stale data after a recovery can be a defect, so we measure it.
Setup     : SPECIAL - Arduino #1 ON (PSU, data cable), Dashboard UNPLUGGED (it would ACK),
            CANable plugged in but not opened before the test (no can_bus fixture).
Steps     : 1. Wait 10 s with the CANable closed: nobody ACKs, the 3 TX buffers fill up.
            2. Open the CANable (it starts ACKing) and record 0x123 for 2 s.
Pass when : (bench expectation from the workbook, until a requirement exists)
            - at least 15 frames in 2 s
            - at most 3 frames arrive in the burst (gap < 10 ms to the previous one, + the first)
            - after the burst and one re-sync gap, every gap is 90-110 ms
Evidence  : the alive counters of the first frames are printed - the queued frames carry OLD
            counters, so a receiver sees a counter jump right after the burst.
"""
import time
import can
import pytest
import config
import frames

pytestmark = pytest.mark.special                           # Arduino #1 ON, Dashboard UNPLUGGED

QUIET_S = 10.0          # no ACK for this long -> all 3 TX buffers are full
BURST_GAP_MS = 10       # frames closer than this came out of the queue, not from the 100 ms timer


def test_tc12_burst_after_ack_loss_is_at_most_3_frames():
    time.sleep(QUIET_S)                                    # CANable closed: nobody ACKs

    bus = can.Bus(interface=config.CAN_INTERFACE, channel=config.CAN_CHANNEL, bitrate=config.CAN_BITRATE)
    try:
        received = []
        end = time.time() + 2.0
        while time.time() < end:
            msg = bus.recv(timeout=0.5)
            if msg is not None and msg.arbitration_id == config.SPEED_MSG_ID:
                received.append(msg)
    finally:
        bus.shutdown()

    stamps = [m.timestamp for m in received]
    gaps_ms = [(b - a) * 1000 for a, b in zip(stamps, stamps[1:])]
    counters = [frames.decode_speed(m.data)["AliveCounter"] for m in received]
    burst = 1                                            # the first frame
    for i, g in enumerate(gaps_ms):
        backwards = counters[i + 1] == (counters[i] - 1) % 16    # queued frames come out in reverse
        if g < BURST_GAP_MS and backwards:
            burst += 1                                   # still the queued burst
        else:
            break                                        # fresh frame: burst is over
    steady = gaps_ms[burst:]                                         # skip the burst and the re-sync gap

    print(f"\n{len(received)} frames; first gaps (ms): {[round(g, 1) for g in gaps_ms[:6]]}")
    print(f"first counters: {counters[:8]}  -> burst of {burst} frame(s)")

    assert len(received) >= 15, f"only {len(received)} frames in 2 s - is Arduino #1 ON and the Dashboard unplugged?"
    assert burst <= 3, f"burst of {burst} queued frames (bench expectation: at most 3 = MCP2515 TX buffers)"
    bad = [round(g, 1) for g in steady if not 90 <= g <= 110]
    assert bad == [], f"gaps outside 90-110 ms after the burst: {bad}"