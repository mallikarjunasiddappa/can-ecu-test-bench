"""TC-06 - Sender ECU lost: timeout seen on the bus side (v2, automated)

Requirement: REQ-007 (no 0x123 for > 300 ms = timeout), REQ-004 (start-up <= 2 s)
Purpose   : the TEST SYSTEM detects the loss of 0x123 on its own - a message timeout monitor,
            as a CANoe test module would run - independent of the ECU under test.
            The Dashboard is the second, independent witness.
Setup     : B with the hub - Arduino #1 on config.SENDER_PORT (COM4), Dashboard COM6, CANable COM5.
            "ECU lost" = opening SENDER_PORT resets Arduino #1 (DTR); it is silent until its
            bootloader has finished (~1.5 s, measured in TC-05).
Steps     : 1. listen 1 s   2. open SENDER_PORT (reset)   3. listen 4 s   4. analyse timestamps
Pass when : - >= 8 frames before the reset
            - exactly ONE gap > 300 ms (the timeout), shorter than 2.5 s (sender restarts)
            - first frame after the gap has AliveCounter 0 (a fresh start, not just a delay)
            - Dashboard: exactly 1 SIGNAL LOST and 1 RESTORED
            - Dashboard "missing for N ms" within 250 ms of the tester's gap
History   : v1 (2026-10-08) manual with the viewer, never run.
"""
import re
import time
import serial
import pytest
import config
import frames
import helpers

pytestmark = pytest.mark.setup_b                           # needs the hub: Arduino #1 on SENDER_PORT


def collect(can_bus, seconds, received):
    end = time.time() + seconds
    while time.time() < end:
        msg = can_bus.recv(timeout=0.2)
        if msg is not None and msg.arbitration_id == config.SPEED_MSG_ID:
            received.append(msg)


def test_tc06_sender_lost_timeout_seen_by_tester(can_bus, dashboard):
    helpers.drain(can_bus)          # drain old frames
    dashboard.reset_input_buffer()

    received = []
    collect(can_bus, 1.0, received)                        # step 1: normal
    before = len(received)

    sender = serial.Serial(config.SENDER_PORT, config.SENDER_BAUD)   # step 2: reset = ECU lost
    try:
        collect(can_bus, 4.0, received)                    # step 3: gap + restart
    finally:
        sender.close()

    text = helpers.dashboard_text(dashboard)

    # step 4: the tester's own timeout monitor
    stamps = [m.timestamp for m in received]
    gaps_ms = [(b - a) * 1000 for a, b in zip(stamps, stamps[1:])]
    timeouts = [i for i, g in enumerate(gaps_ms) if g > config.TIMEOUT_MS]
    gap_ms = gaps_ms[timeouts[0]] if timeouts else 0.0
    first_after = frames.decode_speed(received[timeouts[0] + 1].data)["AliveCounter"] if timeouts else None

    lost, restored = text.count("SIGNAL LOST"), text.count("RESTORED")
    found = re.search(r"missing for (\d+) ms", text)
    dash_ms = int(found.group(1)) if found else None

    print(f"\ntester   : {before} frames before, {len(received)} total, gaps > {config.TIMEOUT_MS} ms: "
          f"{[round(gaps_ms[i]) for i in timeouts]}, first counter after the gap: {first_after}")
    print(f"dashboard: LOST {lost}, RESTORED {restored}, missing for {dash_ms} ms, "
          f"COUNTER ERROR {text.count('COUNTER ERROR')}")

    assert before >= 8, f"only {before} frames before the reset - is Arduino #1 sending?"
    assert len(timeouts) == 1, f"{len(timeouts)} gaps > {config.TIMEOUT_MS} ms, expected exactly 1"
    assert gap_ms < 2500, f"gap {gap_ms:.0f} ms - sender did not restart in time"
    assert first_after == 0, f"first counter after the gap is {first_after}, not 0 - no fresh start?"
    assert lost == 1, f"Dashboard printed SIGNAL LOST {lost} times, expected 1"
    assert restored == 1, f"Dashboard printed RESTORED {restored} times, expected 1"
    assert dash_ms is not None and abs(dash_ms - gap_ms) <= 250, \
        f"Dashboard says missing {dash_ms} ms, tester measured {gap_ms:.0f} ms"