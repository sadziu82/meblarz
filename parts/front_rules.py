"""Reveals of overlay furniture fronts, measured from the outer carcass."""

SIDE_REVEAL = 2.0
END_REVEAL = 3.0
VERTICAL_GAP = 3.0
DOUBLE_DOOR_GAP = 2.0


def split_front_heights(total, count):
    """Distribute available height in half-millimetres without losing the sum."""
    units = round(total * 2)
    if count < 1 or abs(units / 2 - total) > 1e-6 or units < count:
        raise ValueError('Front height budget must be positive and use 0.5 mm increments')
    base, extra = divmod(units, count)
    return [(base + (i < extra)) / 2 for i in range(count)]
