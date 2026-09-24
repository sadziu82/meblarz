"""Rear ventilation path through a built-in refrigerator cabinet."""

from math import hypot

from parts.drawer import Board, Hole


def _opening(config, name, width_key, depth_key, defaults):
    values = config.get('openings', {}).get(name, {})
    return (float(values.get(width_key, config.get('width', defaults[0]))),
            float(values.get(depth_key, config.get(depth_key, defaults[1]))))


def _guide(config, board):
    guide = config.get('guide', {})
    width = float(guide.get('width', 3.2))
    depth = float(guide.get('depth', 2))
    if width <= 0 or depth <= 0 or depth >= min(board.width, board.height, board.depth):
        raise ValueError('fridge_ventilation.guide must fit the board thickness')
    return width, depth


def _outline(config, board, **geometry):
    guide = config.get('guide', {})
    groove_width, groove_depth = _guide(config, board)
    groove = dict(kind='ventilation_cut_guide', groove_width=groove_width,
                  depth=groove_depth,
                  max_edge_offset=float(guide.get('max_edge_offset', 50)),
                  marker_diameter=float(guide.get('marker_diameter', 3)),
                  marker_depth=float(guide.get('marker_depth', 2)),
                  marker_spacing=float(guide.get('marker_spacing', 20)),
                  marker_end_offset=float(guide.get('marker_end_offset', 5)),
                  **geometry)
    if (groove['max_edge_offset'] < 0 or groove['marker_diameter'] <= 0
            or not 0 < groove['marker_depth'] <= (board.depth if geometry['face'] == '-y' else board.height)
            or groove['marker_spacing'] <= 0 or groove['marker_end_offset'] < 0):
        raise ValueError('fridge_ventilation.guide marker settings are invalid')
    board.grooves.append(groove)
    for x, second in guide_marker_points(board, groove):
        if groove['face'] == '-y':
            board.holes.append(Hole(board.pos[0] + x, board.pos[1],
                                    board.pos[2] + second,
                                    groove['marker_diameter'], groove['marker_depth'],
                                    '-y', 'ventilation_cut_marker'))
        else:
            board.holes.append(Hole(board.pos[0] + x, board.pos[1] + second,
                                    board.pos[2] + board.height,
                                    groove['marker_diameter'], groove['marker_depth'],
                                    '+z', 'ventilation_cut_marker'))


def add_plinth_opening(board, config, column_x, column_width):
    width, height = _opening(config, 'plinth', 'width', 'height', (500, 40))
    local = config.get('openings', {}).get('plinth', {})
    bottom = float(local.get('bottom_offset', config.get('bottom_offset', (board.height-height)/2)))
    if width <= 0 or width > column_width or height <= 0 or bottom < 0 or bottom + height > board.height:
        raise ValueError('fridge_ventilation.openings.plinth must fit the left plinth front')
    x = column_x + (column_width - width) / 2 - board.pos[0]
    groove_width, groove_depth = _guide(config, board)
    half = groove_width / 2
    if x < half or x + width + half > board.width or bottom < half or bottom + height + half > board.height:
        raise ValueError('fridge_ventilation.openings.plinth leaves no room for the outline groove')
    _outline(config, board, face='-y', outline='rectangle',
             width=width, height=height, x=x, z=bottom,
             span_x=width, span_z=height)


def add_rear_notch(board, config, name, column_x, clear_width):
    width, depth = _opening(config, name, 'width', 'depth', (500, 40))
    if width <= 0 or width > clear_width or depth <= 0 or depth >= board.depth:
        raise ValueError(f'fridge_ventilation.openings.{name} must fit the left bay')
    x = column_x + (clear_width - width) / 2 - board.pos[0]
    if x < 0 or x + width > board.width:
        raise ValueError(f'fridge_ventilation.openings.{name} lies outside {board.name}')
    groove_width, groove_depth = _guide(config, board)
    half = groove_width / 2
    if x < half or x + width + half > board.width or depth + half >= board.depth:
        raise ValueError(f'fridge_ventilation.openings.{name} leaves no room for the outline groove')
    _outline(config, board, face='+z', outline='rear_u', width=width,
             height=depth, x=x, y=board.depth-depth,
             span_x=width, span_y=depth)


def add_upper_back(boards, config, x, width, bottom, top, carcass_depth,
                   material_thickness, material_color):
    back = config.get('upper_back', {})
    if back.get('enabled', True) is False:
        return
    thickness = float(back.get('thickness', material_thickness))
    clearance = float(back.get('clearance', 10))
    depth = _opening(config, 'middle', 'width', 'depth', (500, 40))[1]
    back_y = carcass_depth - depth - clearance - thickness
    if thickness <= 0 or clearance < 0 or back_y < 0 or bottom >= top:
        raise ValueError('fridge_ventilation.upper_back must fit ahead of the channel')
    boards.append(Board('fridge_upper_back', width, top-bottom, thickness,
                        (x, back_y, bottom), material_color,
                        movable=False,
                        label='Plecy z płyty meblowej górnej szafki przed kanałem wentylacyjnym'))


def guide_rectangles(groove):
    """Local face rectangles for the scored perimeter of a later manual cut.

    The rear notch has no fourth groove along the open board edge.  Both the
    preview and DXF use these same rectangles, so neither implies a cutout.
    """
    x = float(groove['x'])
    y = float(groove['z'] if groove['outline'] == 'rectangle' else groove['y'])
    width = float(groove['width'])
    height = float(groove['height'])
    half = float(groove['groove_width']) / 2
    segments = [
        (x - half, y - half, x + width + half, y + half),
        (x - half, y + height - half, x + width + half, y + height + half),
        (x - half, y + half, x + half, y + height - half),
        (x + width - half, y + half, x + width + half, y + height - half),
    ]
    if groove['outline'] == 'rear_u':
        # The rear board edge is the fourth edge of the future opening.
        segments.pop(1)
        segments[1] = (x - half, y + half, x + half, y + height)
        segments[2] = (x + width - half, y + half, x + width + half, y + height)
    return segments


def _guide_lines(groove):
    x = float(groove['x'])
    y = float(groove['z'] if groove['face'] == '-y' else groove['y'])
    width, height = float(groove['width']), float(groove['height'])
    lines = [(x, y, x + width, y),
             (x, y + height, x + width, y + height),
             (x, y, x, y + height),
             (x + width, y, x + width, y + height)]
    if groove['outline'] == 'rear_u':
        lines.pop(1)
    return lines


def _guide_segments(board, groove):
    face_height = board.height if groove['face'] == '-y' else board.depth
    for line, rect in zip(_guide_lines(groove), guide_rectangles(groove)):
        x1, y1, x2, y2 = line
        axis_size = face_height if y1 == y2 else board.width
        axis_coord = y1 if y1 == y2 else x1
        distance = min(axis_coord, axis_size - axis_coord)
        yield line, rect, distance <= groove['max_edge_offset']


def routable_guide_rectangles(board, groove):
    """Groove segments that the selected edge-distance limit permits."""
    return [rect for _, rect, routable in _guide_segments(board, groove) if routable]


def guide_marker_points(board, groove):
    """Local face points replacing unreachable groove segments with Ø3 marks."""
    points = []
    margin = groove['marker_end_offset']
    spacing = groove['marker_spacing']
    for (x1, y1, x2, y2), _, routable in _guide_segments(board, groove):
        if routable:
            continue
        length = hypot(x2-x1, y2-y1)
        if 2 * margin >= length:
            raise ValueError(f'{board.name}: ventilation guide too short for marker end offsets')
        usable = length - 2 * margin
        intervals = max(1, round(usable / spacing))
        for i in range(intervals + 1):
            fraction = (margin + usable * i / intervals) / length
            x = x1 + (x2-x1) * fraction
            y = y1 + (y2-y1) * fraction
            if (x < groove['marker_diameter']/2 or x > board.width - groove['marker_diameter']/2
                    or y < groove['marker_diameter']/2
                    or y > (board.height if groove['face'] == '-y' else board.depth) - groove['marker_diameter']/2):
                raise ValueError(f'{board.name}: ventilation marker does not fit the board face')
            points.append((round(x * 2)/2, round(y * 2)/2))
    return points
