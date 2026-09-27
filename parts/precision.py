"""Production dimensions use a 0.1 mm grid; calculations keep full precision."""
from decimal import Decimal, ROUND_HALF_UP


def mm(value):
    # Remove binary arithmetic noise before decimal rounding (80.249999999 -> 80.3).
    return float(Decimal(str(round(float(value), 8))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def round_panel(board):
    """Round machining in panel-local coordinates, then restore world positions."""
    old_pos = board.pos
    board.pos = tuple(mm(v) for v in old_pos)
    for name in ('width', 'height', 'depth', 'corner_radius'):
        setattr(board, name, mm(getattr(board, name)))
    for hole in (*board.holes, *board.joint_holes):
        for axis, name in enumerate(('x', 'y', 'z')):
            setattr(hole, name, board.pos[axis] + mm(getattr(hole, name) - old_pos[axis]))
        if hasattr(hole, 'diameter'):
            hole.diameter, hole.depth = mm(hole.diameter), mm(hole.depth)
    dimensions = {'x', 'y', 'z', 'width', 'height', 'depth', 'span_x', 'span_y', 'span_z',
                  'groove_width', 'marker_depth', 'marker_diameter', 'marker_spacing',
                  'marker_end_offset', 'max_edge_offset'}
    for groove in board.grooves:
        for key in dimensions & groove.keys():
            groove[key] = mm(groove[key])
