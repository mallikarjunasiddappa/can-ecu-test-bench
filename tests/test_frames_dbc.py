# test_frames_dbc.py - equivalence test: DBC-built frames == hand-built frames (no hardware)
import pytest
import frames


@pytest.mark.parametrize("speed", [0, 1, 50, 249, 250, 254, 255])
@pytest.mark.parametrize("counter", [0, 1, 15, 16])
def test_dbc_frame_equals_old_frame(speed, counter):
    new = frames.speed_frame_dbc(speed, counter)
    old = frames.speed_frame(speed, counter)
    assert new.arbitration_id == old.arbitration_id
    assert new.data == old.data, f"speed {speed}, counter {counter}: DBC {new.data.hex(' ')} != old {old.data.hex(' ')}"