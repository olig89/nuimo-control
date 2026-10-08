from custom_components.nuimo.core.rotation import RotationAccumulator


def test_batches_and_reports_first_step():
    acc = RotationAccumulator()
    assert acc.add(3) is True
    assert acc.add(4) is False
    batch = acc.flush()
    assert batch.delta == 7 and batch.notifications == 2
    assert batch.as_event_data() == {"delta": 7, "direction": "clockwise", "notifications": 2}
    assert acc.flush() is None
    assert acc.add(-2) is True


def test_back_and_forth_cancels():
    acc = RotationAccumulator()
    acc.add(5)
    acc.add(-5)
    assert acc.flush() is None
    assert not acc.pending


def test_direction():
    acc = RotationAccumulator()
    acc.add(-9)
    assert acc.flush().direction == "anticlockwise"
