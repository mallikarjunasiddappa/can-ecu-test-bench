"""Unit tests (no hardware) - the shared bench helpers in helpers.py

Purpose   : the helpers are used by 28 bench tests; a bug here would break all of them. These tests
            check them without any hardware, so CI runs them on every push.
Doubles   : FakeDashboard - a small object with the same methods as the serial port (readline, read,
            in_waiting, reset_input_buffer) that hands out pre-written Dashboard output.
            python-can's virtual bus - a real CAN bus object that lives only in memory.
Pass when : every helper returns exactly what the bench tests rely on.
"""
import threading
import can
import pytest
import frames
import helpers

pytestmark = pytest.mark.unit                              # no hardware


class FakeDashboard:
    """Pretends to be the Dashboard's serial port: hands out pre-written output."""
    def __init__(self, text):
        self.data = text.encode()

    @property
    def in_waiting(self):                                   # bytes waiting to be read
        return len(self.data)

    def read(self, n):
        chunk, self.data = self.data[:n], self.data[n:]
        return chunk

    def readline(self):
        if not self.data:
            return b""                                      # like a serial timeout: nothing arrived
        line, sep, rest = self.data.partition(b"\n")
        self.data = rest
        return line + sep

    def reset_input_buffer(self):
        pass                                                # the pre-written text is "future" output: keep it


DASH = "Speed = 50 km/h\r\n\r\nSPEED SIGNAL LOST (no 0x123 for 301 ms) -> Speed = --- km/h\r\nSpeed = 50 km/h\r\n"


def test_read_lines_for_strips_and_skips_empty_lines():
    lines = helpers.read_lines_for(FakeDashboard(DASH), 0.1)
    assert lines == ["Speed = 50 km/h", "SPEED SIGNAL LOST (no 0x123 for 301 ms) -> Speed = --- km/h", "Speed = 50 km/h"]


def test_dashboard_text_returns_everything_waiting():
    assert helpers.dashboard_text(FakeDashboard(DASH)) == DASH


def test_count_counts_lines_containing_the_text():
    lines = ["Speed = 50 km/h", "SPEED SIGNAL LOST", "Speed = 50 km/h"]
    assert helpers.count(lines, "Speed = 50") == 2
    assert helpers.count(lines, "COUNTER ERROR") == 0


def test_drain_returns_how_many_old_frames_it_threw_away():
    rx = can.Bus(interface="virtual", channel="unit_helpers_drain")
    tx = can.Bus(interface="virtual", channel="unit_helpers_drain")
    try:
        for c in range(3):
            tx.send(frames.speed_frame_dbc(50, c))
        assert helpers.drain(rx) == 3
        assert helpers.drain(rx) == 0                       # nothing left the second time
    finally:
        rx.shutdown()
        tx.shutdown()


def test_measure_separates_valid_damaged_and_other_frames():
    rx = can.Bus(interface="virtual", channel="unit_helpers_measure")
    tx = can.Bus(interface="virtual", channel="unit_helpers_measure")

    def send_during_measure():                              # measure() drains first, so send a bit later
        for c in range(3):
            tx.send(frames.speed_frame_dbc(50, c))                          # 3 valid
        tx.send(frames.damage_checksum(frames.speed_frame_dbc(50, 3)))      # 1 damaged
        tx.send(can.Message(arbitration_id=0x200, data=[1, 2], is_extended_id=False))   # other ID: ignored

    timer = threading.Timer(0.1, send_during_measure)
    try:
        timer.start()
        good, bad, text = helpers.measure(rx, FakeDashboard(DASH), 0.5)
    finally:
        timer.join()
        rx.shutdown()
        tx.shutdown()
    assert len(good) == 3
    assert bad == 1
    assert text == DASH


def test_assert_dashboard_ok_passes_on_a_clean_dashboard():
    helpers.assert_dashboard_ok("Speed = 50 km/h\n" * 80)


@pytest.mark.parametrize("text, message", [
    ("Speed = 50 km/h\n" * 10, "did not show 50 km/h"),
    ("Speed = 50 km/h\n" * 80 + "SPEED SIGNAL LOST\n", "SIGNAL LOST"),
    ("Speed = 50 km/h\n" * 80 + "SPEED SIGNAL COUNTER ERROR\n", "E2E errors"),
], ids=["too_few_speed_lines", "lost", "counter_error"])
def test_assert_dashboard_ok_fails_with_a_clear_message(text, message):
    with pytest.raises(AssertionError, match=message):
        helpers.assert_dashboard_ok(text)