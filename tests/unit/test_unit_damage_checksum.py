"""Unit test (no hardware) - damage_checksum() breaks ONLY the checksum, found by signal name

Purpose   : the fault-injection helper used by TC-21, TC-23, TC-24..26. If it damaged the wrong
            byte, those tests would pass without testing what they claim (silent false pass).
Setup     : none - pure Python, about 0.1 s.
Data      : speeds 0, 50, 250, 251, 255 x counters 0, 5, 15 = 15 combinations
            (251 / 255 = invalid speeds, built with strict=False).
Pass when : same ID, bytes 0-6 unchanged, byte 7 = good checksum + 1 (wraps 255 -> 0),
            and the damaged frame really fails the checksum rule.
"""
import pytest
import frames

pytestmark = pytest.mark.unit                              # no hardware


@pytest.mark.parametrize("speed", [0, 50, 250, 251, 255])
@pytest.mark.parametrize("counter", [0, 5, 15])
def test_damage_checksum_changes_only_the_checksum(speed, counter):
    good = frames.speed_frame_dbc(speed, counter, strict=False)
    bad = frames.damage_checksum(good)
    assert bad.arbitration_id == good.arbitration_id
    assert bad.data[0:7] == good.data[0:7], "damage_checksum changed more than the checksum"
    assert bad.data[7] == (good.data[7] + 1) & 0xFF, "checksum not increased by exactly 1"
    assert frames.checksum(bad.data) != bad.data[7], "damaged frame still has a valid checksum"