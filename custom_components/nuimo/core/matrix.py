"""The 9x9 LED matrix: pictures, numbers, level bars and the bytes the device expects."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

SIZE = 9
CELLS = SIZE * SIZE
OFF_CHARS = frozenset(" .0_-")
MAX_SECONDS = 25.5  # one byte of tenths of a second


class MatrixError(ValueError):
    """A picture that can't be shown."""


class Matrix:
    """81 LEDs, row by row from the top left."""

    __slots__ = ("leds",)

    def __init__(self, leds: Sequence[bool]) -> None:
        if len(leds) != CELLS:
            raise MatrixError(f"a matrix has {CELLS} LEDs, got {len(leds)}")
        self.leds: tuple[bool, ...] = tuple(bool(x) for x in leds)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Matrix) and other.leds == self.leds

    def __hash__(self) -> int:
        return hash(self.leds)

    def rows(self) -> list[str]:
        return ["".join("#" if self.leds[r * SIZE + c] else "." for c in range(SIZE)) for r in range(SIZE)]

    def __repr__(self) -> str:
        return "Matrix(" + "/".join(self.rows()) + ")"

    @classmethod
    def from_text(cls, text: str | Iterable[str]) -> Matrix:
        """Nine rows of nine characters, or one 81-character string.

        ``.``, space, ``0``, ``_`` and ``-`` are off; any other character is on.
        """
        rows = text.splitlines() if isinstance(text, str) else list(text)
        rows = [r.rstrip("\r") for r in rows if r.strip("\r") != ""]
        if len(rows) == 1 and len(rows[0]) == CELLS:
            rows = [rows[0][i : i + SIZE] for i in range(0, CELLS, SIZE)]
        if len(rows) != SIZE or any(len(r) != SIZE for r in rows):
            raise MatrixError("a picture needs 9 rows of 9 characters (or 81 characters in one line)")
        return cls([ch not in OFF_CHARS for row in rows for ch in row])

    def transposed(self) -> Matrix:
        return Matrix([self.leds[c * SIZE + r] for r in range(SIZE) for c in range(SIZE)])

    def flipped_vertically(self) -> Matrix:
        return Matrix([self.leds[(SIZE - 1 - r) * SIZE + c] for r in range(SIZE) for c in range(SIZE)])

    def flipped_horizontally(self) -> Matrix:
        return Matrix([self.leds[r * SIZE + (SIZE - 1 - c)] for r in range(SIZE) for c in range(SIZE)])


def blank() -> Matrix:
    return Matrix([False] * CELLS)


def level(percent: float) -> Matrix:
    """A bar filling from the bottom: 0 % is dark, anything above 0 lights at least one row."""
    if not 0 <= percent <= 100:
        raise MatrixError("a level is 0 to 100")
    lit = 0 if percent == 0 else max(1, min(SIZE, math.floor(percent * SIZE / 100 + 0.5)))
    return Matrix([r >= SIZE - lit for r in range(SIZE) for _ in range(SIZE)])


_DIGITS = {
    "0": ["###", "#.#", "#.#", "#.#", "###"],
    "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"],
    "3": ["###", "..#", "###", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"],
    "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"],
    "7": ["###", "..#", "..#", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"],
    "9": ["###", "#.#", "###", "..#", "###"],
}


def number(value: int) -> Matrix:
    """0 to 99 in a 3x5 font, centred."""
    if not 0 <= value <= 99:
        raise MatrixError("a number is 0 to 99")
    digits = str(value)
    grid = [["."] * SIZE for _ in range(SIZE)]
    left = 3 if len(digits) == 1 else 1
    for i, d in enumerate(digits):
        for r, row in enumerate(_DIGITS[d]):
            for c, ch in enumerate(row):
                grid[2 + r][left + i * 4 + c] = ch
    return Matrix.from_text(["".join(row) for row in grid])


_ICON_TEXT: dict[str, list[str]] = {
    "power": [
        "....#....",
        "..#.#.#..",
        ".#..#..#.",
        "#...#...#",
        "#.......#",
        "#.......#",
        ".#.....#.",
        "..#...#..",
        "...###...",
    ],
    "bulb": [
        "...###...",
        "..#...#..",
        ".#.....#.",
        ".#.....#.",
        ".#.....#.",
        "..#...#..",
        "...###...",
        "...###...",
        "....#....",
    ],
    "plus": [
        ".........",
        "....#....",
        "....#....",
        "....#....",
        ".#######.",
        "....#....",
        "....#....",
        "....#....",
        ".........",
    ],
    "minus": [
        ".........",
        ".........",
        ".........",
        ".........",
        ".#######.",
        ".........",
        ".........",
        ".........",
        ".........",
    ],
    "check": [
        ".........",
        "........#",
        ".......#.",
        "......#..",
        "#....#...",
        ".#..#....",
        "..##.....",
        ".........",
        ".........",
    ],
    "cross": [
        "#.......#",
        ".#.....#.",
        "..#...#..",
        "...#.#...",
        "....#....",
        "...#.#...",
        "..#...#..",
        ".#.....#.",
        "#.......#",
    ],
    "play": [
        "..#......",
        "..##.....",
        "..###....",
        "..####...",
        "..#####..",
        "..####...",
        "..###....",
        "..##.....",
        "..#......",
    ],
    "pause": [
        ".........",
        ".##...##.",
        ".##...##.",
        ".##...##.",
        ".##...##.",
        ".##...##.",
        ".##...##.",
        ".##...##.",
        ".........",
    ],
    "next": [
        ".........",
        ".#...#...",
        ".##..##..",
        ".###.###.",
        ".########",
        ".###.###.",
        ".##..##..",
        ".#...#...",
        ".........",
    ],
    "up": [
        "....#....",
        "...###...",
        "..#.#.#..",
        ".#..#..#.",
        "....#....",
        "....#....",
        "....#....",
        "....#....",
        "....#....",
    ],
    "heart": [
        ".........",
        ".##...##.",
        "####.####",
        "#########",
        "#########",
        ".#######.",
        "..#####..",
        "...###...",
        "....#....",
    ],
    "sun": [
        "#...#...#",
        ".#.....#.",
        "...###...",
        "..#####..",
        "#.#####.#",
        "..#####..",
        "...###...",
        ".#.....#.",
        "#...#...#",
    ],
    "moon": [
        "...###...",
        "..##.....",
        ".##......",
        ".##......",
        ".##......",
        ".##......",
        ".##......",
        "..##.....",
        "...###...",
    ],
    "music": [
        "...######",
        "...#....#",
        "...#....#",
        "...#....#",
        "...#....#",
        ".###..###",
        "####.####",
        ".##...##.",
        ".........",
    ],
    "dot": [
        ".........",
        ".........",
        ".........",
        "...###...",
        "...###...",
        "...###...",
        ".........",
        ".........",
        ".........",
    ],
}


def _build_icons() -> dict[str, Matrix]:
    icons = {name: Matrix.from_text(rows) for name, rows in _ICON_TEXT.items()}
    icons["previous"] = icons["next"].flipped_horizontally()
    icons["down"] = icons["up"].flipped_vertically()
    icons["left"] = icons["up"].transposed()
    icons["right"] = icons["down"].transposed()
    icons["full"] = Matrix([True] * CELLS)
    icons["blank"] = blank()
    return icons


ICONS: dict[str, Matrix] = _build_icons()


def encode(matrix: Matrix, brightness: float = 1.0, seconds: float = 2.0, fade: bool = False) -> bytes:
    """The 13 bytes written to the LED characteristic.

    Bytes 0-10: the 81 LEDs, eight per byte, lowest bit first.
    Byte 10, bit 4: fade from the previous picture.
    Byte 11: brightness 0-255.
    Byte 12: how long to show it, in tenths of a second (0-25.5 s).
    """
    if not 0 <= brightness <= 1:
        raise MatrixError("brightness is 0 to 1")
    if not 0 <= seconds <= MAX_SECONDS:
        raise MatrixError(f"display time is 0 to {MAX_SECONDS} seconds")
    out = bytearray(11)
    for i, on in enumerate(matrix.leds):
        if on:
            out[i // 8] |= 1 << (i % 8)
    if fade:
        out[10] |= 1 << 4
    out.append(round(brightness * 255))
    out.append(round(seconds * 10))
    return bytes(out)
