import functools

import pytest

from custom_components.nuimo.core import matrix as m


def senic_reference_bytes(leds, brightness, interval, fading):
    """Copied logic from getsenic/nuimo-linux-python _LedMatrixWriter.write_now."""
    out = list(
        map(
            lambda chunk: functools.reduce(
                lambda acc, i: acc + (1 << i if chunk[i] else 0), range(len(chunk)), 0
            ),
            [leds[i : i + 8] for i in range(0, 81, 8)],
        )
    )
    out += [max(0, min(255, int(brightness * 255.0))), max(0, min(255, int(interval * 10.0)))]
    if fading:
        out[10] ^= 1 << 4
    return bytes(out)


@pytest.mark.parametrize("name", sorted(m.ICONS))
def test_every_icon_matches_senic_encoding(name):
    mx = m.ICONS[name]
    assert m.encode(mx, 1.0, 2.0, True) == senic_reference_bytes(list(mx.leds), 1.0, 2.0, True)


def test_encode_layout():
    data = m.encode(m.ICONS["full"], brightness=0.5, seconds=3.0)
    assert len(data) == 13
    assert data[:10] == b"\xff" * 10
    assert data[10] == 0x01  # LED 81 only
    assert data[11] == 128
    assert data[12] == 30
    assert m.encode(m.blank(), fade=True)[10] == 0x10


def test_encode_limits():
    with pytest.raises(m.MatrixError):
        m.encode(m.blank(), brightness=1.5)
    with pytest.raises(m.MatrixError):
        m.encode(m.blank(), seconds=30)
    assert m.encode(m.blank(), seconds=25.5)[12] == 255


def test_from_text_forms():
    rows = ["#........"] + ["........."] * 8
    a = m.Matrix.from_text(rows)
    b = m.Matrix.from_text("\n".join(rows))
    c = m.Matrix.from_text("".join(rows))
    assert a == b == c
    assert a.leds[0] and sum(a.leds) == 1
    assert m.Matrix.from_text(" " * 81) == m.blank()
    with pytest.raises(m.MatrixError):
        m.Matrix.from_text("###")


def test_level():
    assert m.level(0) == m.blank()
    assert m.level(100) == m.ICONS["full"]
    assert sum(m.level(1).leds) == 9  # anything above 0 shows one row
    fifty = m.level(50)
    assert fifty.rows()[-1] == "#########" and fifty.rows()[0] == "........."
    with pytest.raises(m.MatrixError):
        m.level(101)


def test_number():
    assert m.number(7).rows()[2] == "...###..."
    assert m.number(42).rows()[2] == ".#.#.###."
    with pytest.raises(m.MatrixError):
        m.number(100)


def test_derived_icons():
    up = m.ICONS["up"].rows()
    assert up[0] == "....#...."
    assert m.ICONS["down"].rows()[8] == "....#...."
    assert m.ICONS["left"].rows()[4][0] == "#"
    assert m.ICONS["right"].rows()[4][8] == "#"
    assert m.ICONS["previous"].rows()[4] == "########."
