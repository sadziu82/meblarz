"""Validate bore locations and reject intersecting drilling envelopes."""
from math import sqrt


def _segments(board):
    sizes = (board.width, board.depth, board.height)
    for h in board.holes + board.joint_holes:
        axis = 'xyz'.index(h.direction[-1])
        p = [h.x, h.y, h.z]
        for i in range(3):
            if not board.pos[i] - 1e-6 <= p[i] <= board.pos[i] + sizes[i] + 1e-6:
                raise ValueError(f'{board.name}: hole outside board at {tuple(p)}')
        face = board.pos[axis] + (sizes[axis] if h.direction[0] == '+' else 0)
        if abs(p[axis] - face) > 1e-6:
            raise ValueError(f'{board.name}: hole does not start on face {h.direction}')
        if hasattr(h, 'kind'):
            label = h.kind
            steps = [(h.diameter / 2, sizes[axis] if h.through else h.depth)]
        else:
            label = f'{h.hole_type} → {h.partner}'
            if h.hole_type == 'dowel':
                steps = [(4, 11 if h.element == 1 else 27)]
            elif h.element == 1:
                steps = [(2.5, sizes[axis]), (5.5, 4.5)]
            else:
                steps = [(2.5, 35)]
        for radius, depth in steps:
            if radius <= 0 or depth <= 0 or depth > sizes[axis] + 1e-6:
                raise ValueError(f'{board.name}: invalid bore depth/diameter for {label}')
            q = list(p)
            q[axis] += depth * (-1 if h.direction[0] == '+' else 1)
            yield h, label, p, q, radius


def validate_drilling(boards):
    """Conservative capsule envelopes, including stepped confirmat head bores.

    Touching bore surfaces are allowed. Envelopes near the ends are conservative;
    an ambiguous case must be resolved in the design rather than silently drilled.
    """
    for board in boards:
        if not board.fabrication:
            continue
        for cutout in (g for g in board.grooves if g['kind'] == 'manual_cutout_guide'):
            y0 = board.pos[1] + cutout['y']
            y1 = y0 + cutout['span_y']
            z0 = board.pos[2] + cutout['z']
            z1 = z0 + cutout['span_z']
            for hole in board.holes + board.joint_holes:
                if getattr(hole, 'kind', '') == 'manual_cutout_marker':
                    continue
                radius = hole.diameter / 2 if hasattr(hole, 'diameter') else 5.5
                if y0-radius < hole.y < y1+radius and z0-radius < hole.z < z1+radius:
                    raise ValueError(f'Kolizja nawiertu z ręcznym wycięciem w {board.name}: '
                                     f'{getattr(hole, "kind", getattr(hole, "hole_type", "otwór"))} '
                                     f'Y={hole.y}, Z={hole.z}. Popraw układ w YAML.')
        segments = list(_segments(board))
        for i, (hole, label, a, b, radius) in enumerate(segments):
            for other, other_label, c, d, other_radius in segments[:i]:
                if hole is other:
                    continue
                distances = [max(0, min(a[k], b[k]) - max(c[k], d[k]),
                                 min(c[k], d[k]) - max(a[k], b[k])) for k in range(3)]
                distance = sqrt(sum(v * v for v in distances))
                if distance < radius + other_radius - 1e-6:
                    local = tuple(round(a[k] - board.pos[k], 2) for k in range(3))
                    other_local = tuple(round(c[k] - board.pos[k], 2) for k in range(3))
                    raise ValueError(f'Kolizja nawiertów w {board.name}: {label} {local} '
                                     f'oraz {other_label} {other_local}. Popraw układ w YAML.')
