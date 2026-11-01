"""Unit tests for bus_load.py - no hardware.

crc15        : the official CRC-15/CAN check value (0x059E for the ASCII bytes "123456789")
stuff bits   : known patterns (5 equal bits -> 1 stuff bit; the stuff bit starts the next run)
whole frame  : 0x123 with counter 0 = 98 stuffed-part bits + 10 stuff bits + 13 fixed = 121
"""
import pytest
import bus_load
import frames

pytestmark = pytest.mark.unit


def test_crc15_official_check_value():
    bits = "".join(bus_load.bits_of(c, 8) for c in b"123456789")
    assert bus_load.crc15(bits) == 0x059E


@pytest.mark.parametrize("bits, expected", [
    ("0000", 0),              # only 4 equal bits: no stuffing
    ("00000", 1),             # 5 zeros -> 1 stuff bit
    ("0000000000", 2),        # 10 zeros -> 2 (the stuff bit restarts the count)
    ("0101010101", 0),        # alternating: never 5 equal
    ("1111100000", 2),        # 5 ones -> stuff "0" which starts the zero run -> 4 more zeros -> stuff
])
def test_stuff_bit_count(bits, expected):
    assert bus_load.stuff_bit_count(bits) == expected


def test_frame_counter_0_is_121_bits():
    total, stuff = bus_load.frame_bits_on_wire(frames.speed_frame_dbc(50, 0))
    assert stuff == 10
    assert total == 121