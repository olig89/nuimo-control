"""Batching of rotation notifications.

The dial sends a notification for every few steps (tens per second while turning).
Firing an event for each would flood the state machine and anything listening, so steps
are summed over a short window and sent as one ``rotate`` event with the total.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RotationBatch:
    delta: int  # signed sum of steps; positive = clockwise (to confirm on the device)
    notifications: int  # how many raw notifications were summed

    @property
    def direction(self) -> str:
        return "clockwise" if self.delta > 0 else "anticlockwise"

    def as_event_data(self) -> dict[str, int | str]:
        return {"delta": self.delta, "direction": self.direction, "notifications": self.notifications}


class RotationAccumulator:
    """Sums steps until ``flush`` is called; the caller owns the timer.

    ``add`` returns True when this is the first step of a new batch, i.e. when the
    caller should start its flush timer.
    """

    def __init__(self) -> None:
        self._delta = 0
        self._count = 0

    @property
    def pending(self) -> bool:
        return self._count > 0

    def add(self, steps: int) -> bool:
        first = self._count == 0
        self._delta += steps
        self._count += 1
        return first

    def flush(self) -> RotationBatch | None:
        if self._count == 0:
            return None
        batch = RotationBatch(self._delta, self._count)
        self._delta = 0
        self._count = 0
        # Turning back and forth inside one window can cancel out: nothing to report.
        return batch if batch.delta else None
