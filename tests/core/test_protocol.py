from custom_components.nuimo.core import protocol as p


def test_button():
    assert p.decode_button(b"\x01").name == "press"
    assert p.decode_button(b"\x00").name == "release"
    assert p.decode_button(b"") is None


def test_touch_codes_follow_senic_reference():
    names = [p.decode_touch(bytes([i])).name for i in range(12)]
    assert names == [
        "swipe_left", "swipe_right", "swipe_up", "swipe_down",
        "touch_left", "touch_right", "touch_top", "touch_bottom",
        "long_touch_left", "long_touch_right", "long_touch_top", "long_touch_bottom",
    ]
    assert p.decode_touch(b"\x0c") is None
    assert p.decode_touch(b"") is None


def test_rotation_is_signed_little_endian():
    assert p.decode_rotation(b"\x05\x00") == 5
    assert p.decode_rotation(b"\xfb\xff") == -5
    assert p.decode_rotation(b"\x00\x01") == 256
    assert p.decode_rotation(b"\x00\x80") == -32768
    assert p.decode_rotation(b"\x00\x00") is None
    assert p.decode_rotation(b"\x01") is None


def test_fly():
    assert p.decode_fly(b"\x00\x00").name == "fly_left"
    assert p.decode_fly(b"\x01\x00").name == "fly_right"
    g = p.decode_fly(b"\x04\x7f")
    assert g.name == "proximity" and g.data == {"distance": 127}
    assert p.decode_fly(b"\x04") is None
    assert p.decode_fly(b"\x02\x00") is None


def test_battery():
    assert p.decode_battery(b"\x57") == 87
    assert p.decode_battery(b"\xff") == 100
    assert p.decode_battery(b"") is None


def test_event_types_keep_the_old_names():
    old = [
        "press", "release", "rotate", "swipe_left", "swipe_right", "swipe_up", "swipe_down",
        "touch_left", "touch_right", "touch_top", "touch_bottom", "long_touch_left",
        "long_touch_right", "long_touch_top", "long_touch_bottom", "fly_left", "fly_right", "proximity",
    ]
    assert p.EVENT_TYPES == old
