"""Pilot-hole outlines for openings that are cut manually after panel delivery."""

from parts.drawer import Hole


def rectangle_marker_points(y, z, width, height, count_per_edge=4, end_offset=5,
                            skip_rear_edge=False):
    """Y/Z marker centres on each edge, omitting an existing rear panel edge."""
    sides = ((y, z, y + width, z),
             (y + width, z, y + width, z + height),
             (y + width, z + height, y, z + height),
             (y, z + height, y, z))
    points = []
    for y1, z1, y2, z2 in sides:
        if skip_rear_edge and y1 == y2 == y + width:
            continue
        length = abs(y2-y1) + abs(z2-z1)
        if length <= 2 * end_offset:
            raise ValueError('Manual cutout edge is too short for marker end offsets')
        usable = length - 2 * end_offset
        for index in range(count_per_edge):
            fraction = (end_offset + usable * index / (count_per_edge-1)) / length
            points.append((round((y1 + (y2-y1) * fraction) * 2) / 2,
                           round((z1 + (z2-z1) * fraction) * 2) / 2))
    return points


def add_side_cutout_guide(board, config, y, z, width, height, face='-x'):
    """Trace an intended through-cut on the inner face of an outer cheek."""
    diameter = float(config.get('marker_diameter', 3))
    depth = float(config.get('marker_depth', 2))
    count_per_edge = int(config.get('marker_count_per_edge', 4))
    end_offset = float(config.get('marker_end_offset', 5))
    if (face not in ('-x', '+x') or width <= 0 or height <= 0
            or diameter <= 0 or not 2 <= count_per_edge <= 4
            or end_offset < diameter / 2 or depth <= 0 or depth >= board.width
            or y < board.pos[1] or y + width > board.pos[1] + board.depth
            or z < board.pos[2] or z + height > board.pos[2] + board.height):
        raise ValueError(f'{board.name}: microwave side cutout does not fit the board')
    local_y, local_z = y - board.pos[1], z - board.pos[2]
    skip_rear_edge = abs(local_y + width - board.depth) < 1e-6
    points = rectangle_marker_points(local_y, local_z, width, height,
                                     count_per_edge, end_offset, skip_rear_edge)
    for local_y_point, local_z_point in points:
        board.holes.append(Hole(board.pos[0] + (board.width if face == '+x' else 0),
                                board.pos[1] + local_y_point,
                                board.pos[2] + local_z_point,
                                diameter, depth, face, 'manual_cutout_marker'))
    board.grooves.append(dict(kind='manual_cutout_guide', face=face,
                              y=local_y, z=local_z, span_y=width, span_z=height,
                              marker_diameter=diameter, marker_depth=depth,
                              marker_count_per_edge=count_per_edge,
                              marker_end_offset=end_offset,
                              rear_edge_marked=not skip_rear_edge))
