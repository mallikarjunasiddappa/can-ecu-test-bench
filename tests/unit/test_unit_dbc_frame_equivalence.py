"""Unit test (no hardware) - DBC-built frames are identical to the hand-built reference

Purpose   : the frame builder was switched to vehicle.dbc (speed_frame_dbc). Before trusting it,
            prove it produces exactly the same bytes as the old hand-built speed_frame().
Setup     : none - pure Python, about 0.1 s.
Data      : speeds 0, 1, 50, 249, 250, 254, 255 x counters 0, 1, 15, 16 = 28 combinations
            (two stacked parametrize lines). Counter 16 checks the rollover to 0.
Pass when : same ID and same 8 data bytes for every combination.
Red check : VehicleSpeed start bit 8 -> 16 in the DBC gave 24 failed / 4 passed - speed 0 cannot
            reveal a wrong signal position (zero looks the same in every byte).
"""
import pytest
import frames


@pytest.mark.parametrize("speed", [0, 1, 50, 249, 250, 254, 255])
@pytest.mark.parametrize("counter", [0, 1, 15, 16])
def test_dbc_frame_equals_old_frame(speed, counter):
    new = frames.speed_frame_dbc(speed, counter)
    old = frames.speed_frame(speed, counter)
    assert new.arbitration_id == old.arbitration_id
    assert new.data == old.data, f"speed {speed}, counter {counter}: DBC {new.data.hex(' ')} != old {old.data.hex(' ')}"