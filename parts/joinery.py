"""Generate paired bores from contacts between rectangular structural panels.

No part names or furniture dimensions are encoded here. The generator supplies
the structural assembly (excluding doors and bought equipment); YAML supplies
the joint policy. Separate assemblies, e.g. a clipped plinth, are passed separately.
"""
from math import ceil, floor

from parts.drawer import Hole, JointHole


def _near(a, b):
    return abs(a - b) < 1e-6


def _positions(start, end, config, shift=0):
    length = end - start
    margin = min(float(config.get('edge_distance', 50)), length / 4)
    spacing = float(config.get('max_spacing', 300))
    if margin < 10 or spacing <= 0:
        raise ValueError('Joinery requires edge distance >= 10 mm and positive max_spacing')
    count = max(2, ceil((length - 2 * margin) / spacing) + 1)
    points = [round((start + margin + i * (length - 2 * margin) / (count - 1)) * 2) / 2
              for i in range(count)]
    if shift:
        # Opposed dowels are offset along the edge, never drilled into a screw.
        points = [p + shift if p + shift <= end - 10 else p - shift for p in points]
    return points


def add_panel_joints(panels, config=None):
    config = config or {}
    if not config.get('enabled', True):
        return []
    hidden = config.get('hidden', 'confirmat')
    visible = config.get('visible', 'dowel')
    end_kind = config.get('end_panels', hidden)
    dowel_gap = float(config.get('dowel_between_confirmats_above', 200))
    if dowel_gap <= 0:
        raise ValueError('dowel_between_confirmats_above must be positive')
    if any(kind not in ('confirmat', 'dowel') for kind in (hidden, visible, end_kind)):
        raise ValueError('Joinery types must be confirmat or dowel')
    panels = [b for b in panels if b.fabrication and not b.movable]
    if not panels:
        return []
    lo = [min(b.pos[i] for b in panels) for i in range(3)]
    hi = [max(b.pos[i] + (b.width, b.depth, b.height)[i] for b in panels) for i in range(3)]
    joints, contacts = [], []
    # A face board receives a broad-face hole; its partner receives an edge hole.
    for face in panels:
        fs = (face.width, face.depth, face.height)
        face_axis = min(range(3), key=lambda i: fs[i])
        for edge in panels:
            if edge is face:
                continue
            es = (edge.width, edge.depth, edge.height)
            edge_axis = min(range(3), key=lambda i: es[i])
            if edge_axis == face_axis:
                continue
            long_axis = next(i for i in range(3) if i not in (face_axis, edge_axis))
            if edge.pos[edge_axis] < face.pos[edge_axis] - 1e-6 or (
                edge.pos[edge_axis] + es[edge_axis] > face.pos[edge_axis] + fs[edge_axis] + 1e-6):
                continue
            start = max(face.pos[long_axis], edge.pos[long_axis])
            end = min(face.pos[long_axis] + fs[long_axis], edge.pos[long_axis] + es[long_axis])
            if end - start < 40:
                continue
            if _near(face.pos[face_axis] + fs[face_axis], edge.pos[face_axis]):
                normal, contact = 1, edge.pos[face_axis]
            elif _near(face.pos[face_axis], edge.pos[face_axis] + es[face_axis]):
                normal, contact = -1, face.pos[face_axis]
            else:
                continue
            outside = face.pos[face_axis] + (0 if normal == 1 else fs[face_axis])
            exposed = _near(outside, lo[face_axis]) or _near(outside, hi[face_axis])
            kind = end_kind if face_axis == 2 else visible if exposed else hidden
            contacts.append(dict(face=face, edge=edge, axis=face_axis, short=edge_axis,
                                 long=long_axis, start=start, end=end, normal=normal,
                                 contact=contact, outside=outside, kind=kind, shift=0))
    for i, contact in enumerate(contacts):
        for other in contacts[:i]:
            if (contact['face'] is other['face'] and contact['normal'] == -other['normal']
                and contact['short'] == other['short']
                and _near(contact['edge'].pos[contact['short']], other['edge'].pos[other['short']])):
                other['kind'], contact['kind'], contact['shift'] = hidden, 'dowel', 20
        # Defer creation until policies for all opposed contacts have been resolved.
    for c in contacts:
        face, edge, axis = c['face'], c['edge'], c['axis']
        fs, es = (face.width, face.depth, face.height), (edge.width, edge.depth, edge.height)
        if fs[axis] < 12 or es[c['short']] < 12:
            raise ValueError('Standard Ø8 dowels/confirmats require panels at least 12 mm thick')
        centre = edge.pos[c['short']] + es[c['short']] / 2
        positions = _positions(c['start'], c['end'], config, c['shift'])
        fasteners = [(along, c['kind']) for along in positions]
        if c['kind'] == 'confirmat':
            ordered = sorted(positions)
            fasteners += [(round(a + b) / 2, 'dowel')
                          for a, b in zip(ordered, ordered[1:]) if b - a > dowel_gap]
        for along, kind in sorted(fasteners):
            xyz = [0., 0., 0.]
            xyz[c['short']], xyz[c['long']] = centre, along
            xyz[axis] = c['outside'] if kind == 'confirmat' else c['contact']
            sign = -c['normal'] if kind == 'confirmat' else c['normal']
            direction = ('+' if sign == 1 else '-') + 'xyz'[axis]
            face.joint_holes.append(JointHole(*xyz, direction, 1, edge.name, kind))
            xyz[axis] = c['contact']
            direction = ('-' if c['normal'] == 1 else '+') + 'xyz'[axis]
            edge.joint_holes.append(JointHole(*xyz, direction, 2, face.name, kind))
        joints.append((face.name, edge.name))
    return joints


def _add_side_pair_ties(left_side, right_side, config):
    """Drill one touching pair of distinct cabinet cheeks on the shared area."""
    diameter = float(config.get('diameter', 3))
    front = float(config.get('front_offset', 100))
    rear = float(config.get('rear_offset', 100))
    min_spacing = float(config.get('min_spacing', 500))
    max_spacing = float(config.get('max_spacing', 800))
    y_front = max(left_side.pos[1], right_side.pos[1])
    y_back = min(left_side.pos[1] + left_side.depth,
                 right_side.pos[1] + right_side.depth)
    z_bottom = max(left_side.pos[2], right_side.pos[2])
    z_top = min(left_side.pos[2] + left_side.height,
                right_side.pos[2] + right_side.height)
    first = z_bottom + float(config.get('first_above_bottom', 100))
    last = z_top - float(config.get('last_below_top', 100))
    if (diameter <= 0 or min_spacing <= 0 or max_spacing < min_spacing
            or not _near(left_side.pos[0] + left_side.width, right_side.pos[0])
            or front < diameter / 2 or rear < diameter / 2
            or front + rear + diameter > y_back - y_front
            or first < z_bottom + diameter / 2
            or last > z_top - diameter / 2
            or last <= first):
        raise ValueError(f'joinery.column_ties must fit {left_side.name} and {right_side.name}')
    span = last - first
    low = max(1, ceil(span / max_spacing))
    high = floor(span / min_spacing)
    if low > high:
        raise ValueError('joinery.column_ties cannot meet the requested vertical spacing')
    target = float(config.get('preferred_spacing', (min_spacing + max_spacing) / 2))
    if not min_spacing <= target <= max_spacing:
        raise ValueError('joinery.column_ties.preferred_spacing must fit the spacing range')
    intervals = min(range(low, high + 1), key=lambda count: abs(span / count - target))
    levels = [first + round((span * index / intervals) * 2) / 2
              for index in range(intervals + 1)]
    levels[0], levels[-1] = first, last
    if any(not min_spacing <= b - a <= max_spacing
           for a, b in zip(levels, levels[1:])):
        raise ValueError('joinery.column_ties cannot meet the requested vertical spacing on a 0.5 mm grid')
    for z in levels:
        for y in (y_front + front, y_back - rear):
            left_side.holes.append(Hole(left_side.pos[0], y, z, diameter,
                                        left_side.width,
                                        '-x', 'column_tie_through', through=True))
            right_side.holes.append(Hole(right_side.pos[0], y, z, diameter,
                                         right_side.width, '-x', 'column_tie_through',
                                         through=True))


def add_adjacent_cabinet_ties(boards, config=None):
    """Join all touching, separately tagged carcasses; ignore internal dividers.

    Cabinet generators tag only their outer left/right cheeks with `cabinet_id`
    and `cabinet_side`. A shared board or a partition within one cabinet has no
    second cheek and therefore receives no inter-cabinet bore.
    """
    config = config or {}
    if not config.get('enabled', True):
        return []
    sides = [board for board in boards
             if board.fabrication and not board.movable and board.cabinet_id
             and board.cabinet_side in ('left', 'right')]
    joints = []
    for left in sides:
        if left.cabinet_side != 'right':
            continue
        for right in sides:
            if (right.cabinet_side != 'left' or right.cabinet_id == left.cabinet_id
                    or not _near(left.pos[0] + left.width, right.pos[0])):
                continue
            if (min(left.pos[1] + left.depth, right.pos[1] + right.depth)
                    <= max(left.pos[1], right.pos[1])
                    or min(left.pos[2] + left.height, right.pos[2] + right.height)
                    <= max(left.pos[2], right.pos[2])):
                continue
            _add_side_pair_ties(left, right, config)
            joints.append((left.name, right.name))
    return joints
