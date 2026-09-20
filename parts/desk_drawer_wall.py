"""Parametric desk wall with a drawer tower, storage and overhead shelves."""

from pathlib import Path
import math

import yaml

from parts.drawer import (Board, DrawerModel, Hole, JointHole, _build_drawer, _center_model,
                          _load_slides_db, _shift_boards, _joint_positions, _select_nl, _mount_holes_y)
from parts.dresser import _rename_drawer
from parts.drawer import _require_side_slide, _resolve_handle
from parts.monitor_setup import append_monitor_setup
from parts.lighting_controls import append_lighting_controls


_C_MAIN = (0.82, 0.67, 0.47, 1.0)
_C_SHELF = (0.72, 0.57, 0.38, 1.0)
_C_BACK = (0.95, 0.95, 0.95, 1.0)


def _add_led_groove(board: Board, cfg: dict | None) -> None:
    """Store milling metadata; exporters turn it into production documentation."""
    if cfg and cfg.get('enabled', False):
        margin = float(cfg.get('end_margin', 0))
        left_margin = float(cfg.get('end_margin_left', margin))
        right_margin = float(cfg.get('end_margin_right', margin))
        if min(margin, left_margin, right_margin) < 0:
            raise ValueError('LED groove end_margin must be nonnegative')
        x1, x2 = left_margin, board.width-right_margin
        if board.corner_radius:
            radius = min(board.corner_radius, board.width/2, board.depth)
            near_y = float(cfg.get('offset', 20))-float(cfg.get('width', 12))/2
            # Stop inside the rounded outline, including the full groove width.
            if near_y < radius:
                inset = radius-math.sqrt(max(0, radius**2-(radius-max(0, near_y))**2))
                if board.rounded_front_corners[0]:
                    x1 = math.ceil(inset+left_margin)
                if board.rounded_front_corners[1]:
                    x2 = math.floor(board.width-inset-right_margin)
        if x2 <= x1:
            raise ValueError('LED groove end margins leave no room for the groove')
        board.grooves.append({
            'kind': 'led', 'face': cfg.get('face', '-z'),
            'width': float(cfg.get('width', 12)), 'depth': float(cfg.get('depth', 4)),
            'offset': float(cfg.get('offset', 20)), 'edge': cfg.get('edge', 'front'),
            'x': x1, 'span_x': x2-x1, 'end_margin': margin,
        })
        cable = cfg.get('wire_groove', {})
        if cable.get('enabled', False):
            face = cfg.get('face', '-z')
            side = cable.get('side', 'left')
            width = float(cable.get('width', 3.2))
            depth = float(cable.get('depth', 3))
            offset = float(cfg.get('offset', 20))
            if face not in ('-z', '+z') or side not in ('left', 'right'):
                raise ValueError('LED wire groove requires a horizontal face and left/right side')
            if not 0 < width <= x2-x1 or not 0 < depth < board.height:
                raise ValueError('LED wire groove must fit board thickness and LED groove span')
            if not 0 <= offset < board.depth:
                raise ValueError('LED wire groove must start inside board depth')
            # Follow the side; on stopped LED grooves move in to their endpoint.
            inset = float(cable.get('edge_offset', x1 if side == 'left' else board.width-x2))
            x = inset if side == 'left' else board.width-inset-width
            if inset < 0 or x < x1 or x+width > x2:
                raise ValueError('LED wire groove edge_offset must keep channel inside LED span')
            board.grooves.append(dict(kind='led_wire', face=face, width=width,
                depth=depth, x=x, y=offset, span_x=width,
                span_y=board.depth-offset, side=side))
        entry = cfg.get('wire_entry', {})
        if entry.get('enabled', False):
            if cfg.get('face', '-z') not in ('-z', '+z'):
                raise ValueError('LED wire entry requires a horizontal groove face')
            edge = entry.get('edge', 'rear')
            offset = float(cfg.get('offset', 20))
            local_x = float(entry.get('x', min(x1+20, (x1+x2)/2)))
            if edge == 'rear':
                px, py, direction = local_x, board.depth, '+y'
                distance = board.depth-offset
                if not x1+2 <= local_x <= x2-2:
                    raise ValueError('LED wire entry x must be inside groove ends')
            elif edge in ('left', 'right'):
                px, py = (0 if edge == 'left' else board.width), offset
                direction = '-x' if edge == 'left' else '+x'
                distance = x1 if edge == 'left' else board.width-x2
                if not 2 <= py <= board.depth-2:
                    raise ValueError('LED wire entry must fit board depth')
            else:
                raise ValueError('LED wire entry edge must be rear, left or right')
            if board.height < 4 or (board.depth if edge == 'rear' else board.width) <= 35:
                raise ValueError('LED wire entry Ø4 × 35 must fit the board')
            board.holes.append(Hole(board.pos[0]+px, board.pos[1]+py,
                                    board.pos[2]+board.height/2, 4, 35, direction,
                                    'led_wire_entry', False))
            board.grooves[-1]['wire_entry'] = dict(edge=edge, distance=distance,
                axis=board.height/2, bridge=max(0, board.height/2-2-float(cfg.get('depth', 4))))


def _horizontal_joint(panel, side, joints, offset=0):
    """Dowel a horizontal panel to the top/bottom end of a vertical side."""
    above = abs(panel.pos[2] - side.pos[2] - side.height) < 1e-6
    z = panel.pos[2] if above else panel.pos[2] + panel.height
    x = side.pos[0] + side.width / 2
    start = max(panel.pos[1], side.pos[1])
    length = min(panel.pos[1] + panel.depth, side.pos[1] + side.depth) - start
    for y in _joint_positions(start, length):
        y += offset
        panel.joint_holes.append(JointHole(x, y, z, '-z' if above else '+z', 1, side.name, 'dowel'))
        side.joint_holes.append(JointHole(x, y, z, '+z' if above else '-z', 2, panel.name, 'dowel'))
    joints.append((panel.name, side.name))


def _shelf_side_joint(shelf, side, joints):
    """Dowel a shelf end into the inner face of an adjacent side."""
    left = abs(side.pos[0] + side.width - shelf.pos[0]) < 1e-6
    x = shelf.pos[0] if left else shelf.pos[0] + shelf.width
    z = shelf.pos[2] + shelf.height / 2
    start = max(shelf.pos[1], side.pos[1])
    length = min(shelf.pos[1] + shelf.depth, side.pos[1] + side.depth) - start
    for y in _joint_positions(start, length):
        side.joint_holes.append(JointHole(x, y, z, '+x' if left else '-x', 1, shelf.name, 'dowel'))
        shelf.joint_holes.append(JointHole(x, y, z, '-x' if left else '+x', 2, side.name, 'dowel'))
    joints.append((side.name, shelf.name))


def _append_keyboard_tray(boards: list[Board], desk: dict, thickness: float, front_y: float,
                          joints: list) -> None:
    cfg = desk.get('keyboard_tray', {})
    if not cfg.get('enabled', True):
        return
    slide = _load_slides_db()[cfg.get('slides', {}).get('model', 'GTV-H45')]
    _require_side_slide(slide)
    clearance = float(slide['side_clearance_mm'])
    clear_width = desk['width'] - thickness
    width = float(cfg.get('width', clear_width - 2 * (thickness + clearance)))
    depth = float(cfg.get('depth', 350))
    height = float(cfg.get('height', thickness))
    position = cfg.get('position', 'offset' if 'offset_left' in cfg else 'center')
    if position not in ('center', 'offset'):
        raise ValueError('keyboard_tray.position must be center or offset')
    # Offset is measured from the inner face of the left desk side to the tray edge.
    x = (thickness + (clear_width - width) / 2 if position == 'center'
         else thickness + float(cfg['offset_left']))
    y = front_y + float(cfg.get('offset_front', 0))
    z = float(desk['height']) - float(cfg.get('drop', 120)) - height
    if 'clear_height' in cfg:
        if float(cfg['clear_height']) <= 0:
            raise ValueError('Keyboard clear height must be positive')
        z = float(desk['height']) - thickness - float(cfg['clear_height']) - height
    nl = cfg.get('slides', {}).get('nl', _select_nl(slide['available_lengths_mm'], depth))
    if nl not in slide['available_lengths_mm'] or nl > depth:
        raise ValueError('Keyboard slide length must fit the tray and be available in the database')
    slide_offset = float(cfg.get('slides', {}).get('offset_front', 0))
    if slide_offset < 0 or slide_offset + nl > depth:
        raise ValueError('Keyboard slide offset and length must fit the tray')
    slide_y = y + slide_offset
    max_travel = float(slide.get('travel_mm', nl))
    travel = float(cfg.get('travel', max_travel))
    if not 0 <= travel <= max_travel:
        raise ValueError('Keyboard travel exceeds slide length')
    if width <= 0 or height <= 0 or x - clearance - thickness < thickness or x + width + clearance + thickness > desk['width']:
        raise ValueError('Keyboard tray, slides and hangers must fit between desk sides')
    if y < front_y or y + depth > front_y + desk['depth'] or z <= 0:
        raise ValueError('Keyboard tray exceeds desk dimensions')
    desk_top = next(b for b in boards if b.name == 'desk_top')
    axis_z = z + height / 2
    slide_h = float(slide['height_mm'])
    if axis_z + slide_h / 2 > desk_top.pos[2]:
        raise ValueError('keyboard_tray.drop leaves no space for the slides')
    tray = Board('keyboard_tray', width=width, height=height, depth=depth,
                 pos=(x, y, z), color=_C_MAIN, movable=True,
                 travel=travel)
    _add_led_groove(tray, cfg.get('led_groove'))
    boards.append(tray)
    mount = slide['inner_drawer_mount']
    hanger_bottom = min(z, axis_z - slide_h / 2)
    if desk.get('whole_mm', False):
        hanger_bottom = math.floor(hanger_bottom)
    hanger_depth = float(cfg.get('hanger_depth', depth - slide_offset))
    if not nl <= hanger_depth <= depth - slide_offset:
        raise ValueError('Keyboard hanger depth must fit slides and tray')
    under_top = desk.get('stiffeners', {}).get('under_top', {})
    if under_top.get('enabled', False):
        stiffener_front = front_y + desk['depth'] - float(under_top.get('rear_offset', 50)) - thickness
        stiffener_bottom = desk_top.pos[2] - float(under_top.get('height', 100))
        if z + height > stiffener_bottom + 1e-6 and y + depth > stiffener_front:
            raise ValueError('Keyboard tray overlaps the stiffener below the desktop')
        hanger_depth = min(hanger_depth, stiffener_front - slide_y)
        if hanger_depth < nl:
            raise ValueError('Desktop stiffener leaves insufficient length for keyboard slides')
    for side, hanger_x, slide_x, tray_x, direction in (
        ('left', x - clearance - thickness, x - clearance, x, '-x'),
        ('right', x + width + clearance, x + width, x + width, '+x'),
    ):
        hanger = Board(f'keyboard_hanger_{side}', thickness, desk_top.pos[2] - hanger_bottom,
                       hanger_depth, (hanger_x, slide_y, hanger_bottom), _C_MAIN, movable=False)
        boards.append(hanger)
        _horizontal_joint(desk_top, hanger, joints)
        inner_x = hanger_x + thickness if side == 'left' else hanger_x
        for hy in _mount_holes_y(slide, nl, slide_y):
            tray.holes.append(Hole(tray_x, hy, axis_z, mount['box_hole_diameter_mm'],
                                   mount['hole_depth_mm'], direction))
        carcass_ys = ([slide_y + p for p in mount['carcass_positions_mm']]
                      if 'carcass_positions_mm' in mount else _mount_holes_y(slide, nl, slide_y))
        for hy in carcass_ys:
            hanger.holes.append(Hole(inner_x, hy, axis_z, mount['carcass_hole_diameter_mm'],
                                     mount['hole_depth_mm'], '+x' if side == 'left' else '-x'))
        for k, part in enumerate(('outer', 'middle', 'inner')):
            fraction = k / 2
            part_x = slide_x + (k if side == 'left' else 2 - k) * clearance / 3
            boards.append(Board(f'keyboard_tray_slide_{side}_{part}', clearance / 3, slide_h, nl,
                                (part_x, slide_y, axis_z - slide_h / 2), tuple(slide.get('color', (0.6, 0.63, 0.68, 1))),
                                movable=k > 0, move_fraction=fraction, travel=travel))


def load_desk_drawer_wall(path: str) -> DrawerModel:
    with open(path) as source:
        root = yaml.safe_load(source)
    cfg = root['desk_drawer_wall']
    material = root['material']
    thick = float(material['thickness'])
    back_thick = float(material.get('back_thickness', 3))

    desk = dict(cfg['desk'])
    whole_mm = cfg.get('whole_mm', False)
    mm = round if whole_mm else lambda value: value
    desk['whole_mm'] = whole_mm
    if 'underside_height' in desk:
        desk['height'] = float(desk['underside_height']) + thick
    if desk.get('width_mode') == 'desktop':
        desk['width'] = float(desk['width']) + thick
    desk_w = float(desk['width'])
    desk_d = float(desk['depth'])
    desk_h = float(desk['height'])
    tower = cfg['drawer_tower']
    tower_w = float(tower['width'])
    tower_d = float(tower.get('depth', desk_d))
    tower_x = desk_w
    total_w = desk_w + tower_w
    desk_front_y = tower_d - desk_d
    desk_clear_w = desk_w - thick
    overhead = cfg.get('overhead', {})
    bridge_cfg = overhead.get('bridge', {})
    bridge_z = (float(bridge_cfg['top']) - thick if 'top' in bridge_cfg
                else float(bridge_cfg.get('bottom', 1400)))
    upper_z = bridge_z + thick
    total_h = (upper_z + float(overhead['height']) if 'height' in overhead else float(cfg['height']))
    upper_height = total_h - thick - upper_z
    if not desk_h < bridge_z or upper_height <= 0:
        raise ValueError('Bridge must be above desk and below the upper module top')
    boards: list[Board] = []
    joints: list[tuple[str, str]] = []
    drawers = tower['drawers']
    section_h = desk_h - thick if drawers.get('align_top_to_desk') else float(drawers['section_height'])

    # Desk: left support reaches the same depth as the drawer tower by default.
    left_depth = float(desk.get('left_side', {}).get('depth', tower_d))
    boards.append(Board('desk_left_side', width=thick, height=bridge_z, depth=left_depth,
                        pos=(0, tower_d - left_depth, 0), color=_C_MAIN, movable=False))
    top = Board('desk_top', width=desk_clear_w, height=thick, depth=desk_d,
                pos=(thick, desk_front_y, desk_h - thick), color=_C_MAIN, movable=False,
                corner_radius=float(desk.get('corner_rounding', {}).get('radius', 0)),
                rounded_front_corners=(
                    desk.get('corner_rounding', {}).get('sides', 'none') in ('left', 'both'),
                    desk.get('corner_rounding', {}).get('sides', 'none') in ('right', 'both'),
                ))
    _add_led_groove(top, desk.get('led_groove'))
    boards.append(top)
    _append_keyboard_tray(boards, desk, thick, desk_front_y, joints)

    low_shelf = desk.get('low_shelf', {})
    if low_shelf.get('enabled', False):
        shelf_width = desk_clear_w if low_shelf.get('span', 'full') == 'full' else float(low_shelf['width'])
        shelf_x = thick if low_shelf.get('side', 'left') == 'left' else desk_w - shelf_width
        shelf_depth = float(low_shelf.get('depth', 180))
        above_top = desk.get('stiffeners', {}).get('above_top', {})
        shelf_rear = tower_d
        if above_top.get('enabled', False):
            shelf_rear -= thick + float(above_top.get('rear_offset', 0))
        support_height = float(low_shelf['height'])
        supports = low_shelf.get('supports', 2)
        if supports not in (1, 2) or isinstance(supports, bool):
            raise ValueError('desk.low_shelf.supports must be 1 or 2')
        if not thick < shelf_width <= desk_clear_w or not 0 < shelf_depth <= desk_d or support_height <= 0:
            raise ValueError('Invalid low shelf dimensions')
        boards.append(Board('desk_low_shelf', width=shelf_width, height=thick,
                            depth=shelf_depth,
                            pos=(shelf_x, shelf_rear - shelf_depth, desk_h + support_height),
                            color=_C_SHELF, movable=False))
        _add_led_groove(boards[-1], low_shelf.get('led_groove'))
        support_xs = ([shelf_x + (shelf_width - thick) / 2] if supports == 1
                     else [shelf_x + shelf_width / 3 - thick / 2,
                           shelf_x + 2 * shelf_width / 3 - thick / 2])
        support_xs = [mm(x) for x in support_xs]
        for index, support_x in enumerate(support_xs):
            boards.append(Board(f'desk_low_shelf_support_{index}', thick, support_height,
                                shelf_depth, (support_x, shelf_rear - shelf_depth, desk_h),
                                _C_MAIN, movable=False))

    if desk.get('back', {}).get('enabled', False):
        boards.append(Board('desk_back', width=desk_clear_w, height=desk_h - thick, depth=back_thick,
                            pos=(thick, tower_d - back_thick, 0), color=_C_BACK, movable=False))

    # Full-height right tower.
    boards.extend([
        Board('tower_left_side', width=thick, height=bridge_z - thick, depth=tower_d,
              pos=(tower_x, 0, thick), color=_C_MAIN, movable=False),
        Board('tower_right_side', width=thick, height=bridge_z - thick, depth=tower_d,
              pos=(tower_x + tower_w - thick, 0, thick), color=_C_MAIN, movable=False),
        Board('tower_bottom', width=tower_w, height=thick, depth=tower_d,
              pos=(tower_x, 0, 0), color=_C_MAIN, movable=False),
        Board('module_bridge', total_w, thick, max(left_depth, tower_d),
              (0, tower_d - max(left_depth, tower_d), bridge_z), _C_MAIN, movable=False),
        Board('upper_left_side', thick, upper_height, left_depth,
              (0, tower_d - left_depth, upper_z), _C_MAIN, movable=False),
        Board('upper_divider', thick, upper_height, tower_d,
              (tower_x, 0, upper_z), _C_MAIN, movable=False),
        Board('upper_right_side', thick, upper_height, tower_d,
              (total_w - thick, 0, upper_z), _C_MAIN, movable=False),
        Board('upper_top', total_w, thick, max(left_depth, tower_d),
              (0, tower_d - max(left_depth, tower_d), total_h - thick), _C_MAIN, movable=False),
    ])
    if tower.get('back', {}).get('enabled', False):
        back_bottom = thick if tower['back'].get('behind_drawers', True) else section_h + thick
        boards.append(Board('tower_back', width=tower_w - 2 * thick, height=bridge_z - back_bottom,
                            depth=back_thick, pos=(tower_x + thick, tower_d - back_thick, back_bottom),
                            color=_C_BACK, movable=False))
        boards.append(Board('upper_tower_back', tower_w - 2 * thick, upper_height, back_thick,
                            (tower_x + thick, tower_d - back_thick, upper_z), _C_BACK, movable=False))

    bd = {b.name: b for b in boards}
    for side in (bd['desk_left_side'], bd['tower_left_side']):
        _shelf_side_joint(top, side, joints)
    upper_bays = [(bd['upper_left_side'], bd['upper_divider']),
                  (bd['upper_divider'], bd['upper_right_side'])]
    if overhead.get('desk_columns') == 'two_equal_tower_and_remainder':
        equal_width = tower_w - 2 * thick
        remainder = desk_clear_w - 2 * equal_width - 2 * thick
        if remainder <= 0:
            raise ValueError('Desk too narrow for two tower-width bays and a remainder bay')
        # Narrow bay at the left, then two equal bays next to the tower.
        x = thick + remainder
        dividers = []
        for index in range(2):
            divider = Board(f'upper_desk_divider_{index}', thick, upper_height, tower_d,
                            (x, 0, upper_z), _C_MAIN, movable=False)
            boards.append(divider)
            bd[divider.name] = divider
            dividers.append(divider)
            x += thick + equal_width
        upper_bays = list(zip([bd['upper_left_side'], *dividers], [*dividers, bd['upper_divider']])) + [upper_bays[-1]]
    # One continuous run on this edge, including across the inner dividers.
    _add_led_groove(bd['upper_top'], overhead.get('top_led_groove'))

    desk_back_cfg = overhead.get('desk_back', {})
    desk_back_frames = []
    if desk_back_cfg.get('enabled', False):
        for index, (left, right) in enumerate(upper_bays[:-1]):
            name = f'upper_desk_back_{index}'
            boards.append(Board(name, right.pos[0]-left.pos[0]-left.width,
                                upper_height, back_thick,
                                (left.pos[0]+left.width, tower_d-back_thick, upper_z),
                                _C_BACK, movable=False))
            desk_back_frames.append((name, left.name, right.name, 'module_bridge', 'upper_top'))
    bridge = bd['module_bridge']
    _add_led_groove(bridge, bridge_cfg.get('led_groove'))
    support_cfg = bridge_cfg.get('support', {})
    if support_cfg.get('enabled', False):
        height = float(support_cfg.get('height', 200))
        rear_offset = float(support_cfg.get('rear_offset', 50))
        support_y = tower_d - rear_offset - thick
        support_z = bridge_z - height
        if height <= 0 or rear_offset < 0 or support_z < desk_h or support_y < max(0, tower_d - left_depth):
            raise ValueError('Bridge support must fit above the desk and within both side depths')
        support = Board('desk_bridge_support', desk_clear_w, height, thick,
                        (thick, support_y, support_z), _C_MAIN, movable=False)
        boards.append(support)
        # Dowels along the upper edge and at two heights on each end.
        axis_y = support_y + thick / 2
        for x in _joint_positions(thick, desk_clear_w):
            bridge.joint_holes.append(JointHole(x, axis_y, bridge_z, '-z', 1, support.name, 'dowel'))
            support.joint_holes.append(JointHole(x, axis_y, bridge_z, '+z', 2, bridge.name, 'dowel'))
        joints.append((bridge.name, support.name))
        for side, x, direction in ((bd['desk_left_side'], thick, '+x'),
                                    (bd['tower_left_side'], desk_w, '-x')):
            for z in _joint_positions(support_z, height):
                side.joint_holes.append(JointHole(x, axis_y, z, direction, 1, support.name, 'dowel'))
                support.joint_holes.append(JointHole(x, axis_y, z, '-x' if direction == '+x' else '+x',
                                                    2, side.name, 'dowel'))
            joints.append((side.name, support.name))
    for name in ('desk_left_side', 'tower_left_side', 'tower_right_side'):
        _horizontal_joint(bridge, bd[name], joints)
    for key, default_offset in (('under_top', 50), ('above_top', 0), ('floor', 100)):
        stiffener_cfg = desk.get('stiffeners', {}).get(key, {})
        if not stiffener_cfg.get('enabled', False):
            continue
        height = float(stiffener_cfg.get('height', 100))
        offset = float(stiffener_cfg.get('rear_offset', default_offset))
        y = tower_d - offset - thick
        z = desk_h if key == 'above_top' else (top.pos[2] - height if key == 'under_top' else 0)
        limit = bridge_z if key == 'above_top' else top.pos[2]
        if height <= 0 or offset < 0 or z < 0 or z + height > limit or y < max(0, tower_d-left_depth):
            raise ValueError('Desk stiffener must fit between the floor, desktop and side panels')
        panel = Board(f'desk_stiffener_{key}', desk_clear_w, height, thick,
                      (thick, y, z), _C_MAIN, movable=False)
        boards.append(panel)
        axis_y = y + thick / 2
        if key in ('under_top', 'above_top'):
            joint_z = desk_h if key == 'above_top' else top.pos[2]
            top_direction = '+z' if key == 'above_top' else '-z'
            panel_direction = '-z' if key == 'above_top' else '+z'
            for x in _joint_positions(thick, desk_clear_w):
                top.joint_holes.append(JointHole(x, axis_y, joint_z, top_direction, 1, panel.name, 'dowel'))
                panel.joint_holes.append(JointHole(x, axis_y, joint_z, panel_direction, 2, top.name, 'dowel'))
            joints.append((top.name, panel.name))
        for side, x, direction in ((bd['desk_left_side'], thick, '+x'),
                                    (bd['tower_left_side'], desk_w, '-x')):
            start = max(z, side.pos[2])
            end = min(z + height, side.pos[2] + side.height)
            if end - start < 40:
                raise ValueError('Desk stiffener has insufficient side overlap for mounting')
            for hole_z in _joint_positions(start, end-start):
                side.joint_holes.append(JointHole(x, axis_y, hole_z, direction, 1, panel.name, 'dowel'))
                panel.joint_holes.append(JointHole(x, axis_y, hole_z, '-x' if direction == '+x' else '+x',
                                                  2, side.name, 'dowel'))
            joints.append((side.name, panel.name))
    for name in ('upper_left_side', 'upper_divider', 'upper_right_side',
                 *[b.name for b in boards if b.name.startswith('upper_desk_divider_')]):
        _horizontal_joint(bridge, bd[name], joints, offset=20)
        _horizontal_joint(bd['upper_top'], bd[name], joints)
    rear_fixing = overhead.get('rear_confirmats', {})
    if rear_fixing.get('enabled', False):
        support = bd.get('desk_bridge_support')
        if support is None:
            # The support is appended after bd is built.
            support = next((b for b in boards if b.name == 'desk_bridge_support'), None)
        if support is None:
            raise ValueError('Upper rear confirmats require the bridge support')
        y = tower_d - float(rear_fixing.get('rear_offset', 30))
        if not support.pos[1] + support.depth + 5.5 < y < tower_d - 12:
            raise ValueError('Upper rear confirmats must clear support and rear rebates')
        for side in (b for b in boards if b.name.startswith('upper_desk_divider_')):
            x = side.pos[0] + side.width / 2
            if not support.pos[0] + 5.5 < x < support.pos[0] + support.width - 5.5:
                raise ValueError('Upper rear confirmat is outside the hidden support span')
            for h in bridge.joint_holes:
                if h.partner == side.name and abs(h.y-y) < 10:
                    raise ValueError('Upper rear confirmat conflicts with a locating dowel')
            bridge.joint_holes.append(JointHole(x, y, bridge.pos[2], '-z', 1, side.name, 'confirmat'))
            side.joint_holes.append(JointHole(x, y, side.pos[2], '-z', 2, bridge.name, 'confirmat'))

    if 'desk_low_shelf' in bd:
        shelf = bd['desk_low_shelf']
        for side in (bd['desk_left_side'], bd['tower_left_side']):
            if (abs(shelf.pos[0] - side.pos[0] - side.width) < 1e-6 or
                    abs(shelf.pos[0] + shelf.width - side.pos[0]) < 1e-6):
                _shelf_side_joint(shelf, side, joints)
        for support in (b for b in boards if b.name.startswith('desk_low_shelf_support_')):
            _horizontal_joint(shelf, support, joints)
            _horizontal_joint(top, support, joints)

    # Lower drawer section reuses the established drawer and slide calculations.
    drawers = tower['drawers']
    drawer_count = int(drawers['count'])
    section_h = desk_h - thick if drawers.get('align_top_to_desk') else float(drawers['section_height'])
    if section_h + thick >= bridge_z:
        raise ValueError('Drawer section must fit below the module bridge')
    rail_thick = float(drawers.get('rail_thickness', thick))
    front = drawers['front']
    overlay = front.get('mount', 'inset') == 'overlay'
    gap = float(front.get('gap', 3))
    if overlay:
        bottom_overlay = float(front.get('bottom_overlay', thick - gap))
        top_overlay = float(front.get('top_overlay', -gap))
        front_bottom = thick - bottom_overlay
        front_top = section_h + top_overlay
        if not 0 <= bottom_overlay <= thick or not -thick <= top_overlay <= thick:
            raise ValueError('Front overlays must fit the bottom and top panel thickness')
        if drawer_count < 1 or gap < 0 or front_top - front_bottom <= gap * (drawer_count - 1):
            raise ValueError('Drawer fronts and gaps must fit the drawer section')
        front_heights = [(front_top - front_bottom - gap * (drawer_count - 1)) / drawer_count] * drawer_count
        if whole_mm:
            available = round(front_top - front_bottom - gap * (drawer_count - 1))
            base, remainder = divmod(available, drawer_count)
            front_heights = [base + (index < remainder) for index in range(drawer_count)]
    else:
        available_h = section_h - thick - (drawer_count - 1) * rail_thick - drawer_count * (
            float(front['top_gap']) + float(front['bottom_gap']))
        front_h = int(available_h // drawer_count)
        front_heights = [front_h] * drawer_count
        front_heights[0] += int(round(available_h - front_h * drawer_count))
    slide_cfg = _load_slides_db()[drawers['slides']['model']]
    nl_used = 0
    bottom_type = drawers.get('bottom', {}).get('type')
    # Compatibility for projects saved before the material naming correction.
    if bottom_type == 'mdf_3':
        bottom_type = 'hdf_3'
    if bottom_type not in (None, 'hdf_3', 'board_18'):
        raise ValueError('drawers.bottom.type must be hdf_3 or board_18')
    bottom_thickness = ({'hdf_3': 3, 'board_18': 18}[bottom_type] if bottom_type
                        else float(material.get('drawer_bottom', thick)))
    z = front_bottom if overlay else thick
    tower_left = next(board for board in boards if board.name == 'tower_left_side')
    tower_right = next(board for board in boards if board.name == 'tower_right_side')
    for index, height in enumerate(front_heights):
        drawer_boards, drawer_joints, nl = _build_drawer(
            nw=tower_w - 2 * thick, front_H=height, nd=tower_d,
            board_thickness=float(material.get('drawer_thickness', thick)),
            bot=bottom_thickness, slide_cfg=slide_cfg,
            inset=-(float(material.get('drawer_thickness', thick)) + float(front.get('carcass_gap', 2))) if overlay else float(front['inset']),
            side_gap=gap - thick if overlay else float(front['side_gap']),
            bot_gap=0 if overlay else float(front['bottom_gap']), target_nl=drawers['slides'].get('nl'),
            handle=front.get('handle'),
            box_bottom_offset=thick + 2 if overlay else 2,
        )
        nl_used = nl
        if whole_mm:
            for board in drawer_boards:
                for hole in board.holes:
                    if hole.kind == 'handle':
                        hole.z = board.pos[2] + round(hole.z - board.pos[2])
        for board in drawer_boards:
            board.movable = True
        _append_handle_preview(drawer_boards, front.get('handle'))
        drawer_boards = _shift_boards(drawer_boards, tower_x + thick, 0, z)
        drawer_boards, drawer_joints = _rename_drawer(drawer_boards, drawer_joints, f'tower_drawer_{index}_')
        for board in drawer_boards:
            if board.name == f'tower_drawer_{index}_side_left':
                mount = slide_cfg['inner_drawer_mount']
                ys = ([board.pos[1] + p for p in mount['carcass_positions_mm']]
                      if 'carcass_positions_mm' in mount else [h.y for h in board.holes])
                for y in ys:
                    tower_left.holes.append(Hole(tower_x + thick, y, board.holes[0].z,
                                                 mount['carcass_hole_diameter_mm'], mount['hole_depth_mm'], '+x'))
                    tower_right.holes.append(Hole(tower_x + tower_w - thick, y, board.holes[0].z,
                                                  mount['carcass_hole_diameter_mm'], mount['hole_depth_mm'], '-x'))
        boards.extend(drawer_boards)
        joints.extend(drawer_joints)
        z += height + gap if overlay else float(front['bottom_gap']) + height + float(front['top_gap'])
        if index < drawer_count - 1:
            rail = Board(f'tower_drawer_rail_{index}', width=tower_w - 2 * thick,
                         height=rail_thick, depth=float(drawers.get('rail_depth', 100)),
                         pos=(tower_x + thick, 0, z - gap - rail_thick if overlay else z), color=_C_SHELF, movable=False)
            _add_led_groove(rail, drawers.get('led_groove'))
            boards.append(rail)
            if not overlay:
                z += rail_thick

    shelves = tower.get('upper_shelves', {})
    boards.append(Board('tower_drawer_top', tower_w - 2 * thick, thick,
                        tower_d - (back_thick if tower.get('back', {}).get('enabled', False) else 0),
                        (tower_x + thick, 0, section_h), _C_SHELF, movable=False))
    _add_led_groove(boards[-1], drawers.get('led_groove'))
    count = int(shelves.get('count', 0))
    rear_gap = back_thick if tower.get('back', {}).get('enabled', False) else 0
    shelf_depth = (tower_d - rear_gap - float(shelves['front_setback'])
                   if 'front_setback' in shelves else float(shelves.get('depth', tower_d)))
    for index in range(count):
        shelf_z = section_h + thick + (index + 1) * (bridge_z - section_h - 2 * thick) / (count + 1)
        shelf_z = mm(shelf_z)
        shelf = Board(f'tower_shelf_{index}', width=tower_w - 2 * thick, height=thick,
                      depth=shelf_depth,
                      pos=(tower_x + thick, tower_d - shelf_depth
                           - (back_thick if tower.get('back', {}).get('enabled', False) else 0), shelf_z),
                      color=_C_SHELF, movable=False)
        _add_led_groove(shelf, shelves.get('led_groove'))
        boards.append(shelf)
    if 'secondary' in shelves:
        secondary = shelves['secondary']
        main_shelves = [b for b in boards if b.name.startswith('tower_shelf_')]
        bounds = [section_h + thick] + [b.pos[2] + thick for b in main_shelves]
        tops = [b.pos[2] for b in main_shelves] + [bridge_z]
        for index, (bottom, ceiling) in enumerate(zip(bounds, tops)):
            # Divide the remaining clear height in ratio 2:1, allowing for shelf thickness.
            z_shelf = bottom + float(secondary.get('fraction', 2 / 3)) * (ceiling - bottom - thick)
            z_shelf = mm(z_shelf)
            setback = float(secondary['front_setback'])
            shelf = Board(f'tower_secondary_shelf_{index}', tower_w - 2 * thick, thick,
                          tower_d - rear_gap - setback, (tower_x + thick, setback, z_shelf),
                          _C_SHELF, movable=False)
            _add_led_groove(shelf, secondary.get('led_groove', shelves.get('led_groove')))
            boards.append(shelf)
    for shelf in (b for b in boards if b.name.startswith(('tower_shelf_', 'tower_secondary_shelf_')) or b.name == 'tower_drawer_top'):
        _shelf_side_joint(shelf, tower_left, joints)
        _shelf_side_joint(shelf, tower_right, joints)

    # Optional wall cabinets above the desk, with individually configurable shelf counts.
    overhead = cfg.get('overhead', {})
    cabinets = overhead.get('cabinets', {})
    cabinet_count = int(cabinets.get('count', 0))
    if cabinet_count:
        cabinet_w = desk_clear_w / cabinet_count
        cabinet_h = float(cabinets['height'])
        cabinet_d = float(cabinets['depth'])
        cabinet_z = float(cabinets['bottom'])
        for index in range(cabinet_count):
            x = thick + mm(index * desk_clear_w / cabinet_count)
            cabinet_w = mm((index + 1) * desk_clear_w / cabinet_count) - mm(index * desk_clear_w / cabinet_count)
            prefix = f'overhead_cabinet_{index}'
            boards.extend([
                Board(f'{prefix}_left', thick, cabinet_h, cabinet_d, (x, 0, cabinet_z), _C_MAIN, movable=False),
                Board(f'{prefix}_right', thick, cabinet_h, cabinet_d, (x + cabinet_w - thick, 0, cabinet_z), _C_MAIN, movable=False),
                Board(f'{prefix}_top', cabinet_w, thick, cabinet_d, (x, 0, cabinet_z + cabinet_h - thick), _C_MAIN, movable=False),
                Board(f'{prefix}_bottom', cabinet_w, thick, cabinet_d, (x, 0, cabinet_z), _C_MAIN, movable=False),
            ])
            for shelf_index in range(int(cabinets.get('shelf_count', 0))):
                shelf_z = cabinet_z + (shelf_index + 1) * (cabinet_h - 2 * thick) / (int(cabinets['shelf_count']) + 1)
                shelf_z = mm(shelf_z)
                boards.append(Board(f'{prefix}_shelf_{shelf_index}', cabinet_w - 2 * thick, thick,
                                    cabinet_d, (x + thick, 0, shelf_z), _C_SHELF, movable=False))
            # Align cabinets with the same rear plane as the tower.
            for board in boards:
                if board.name.startswith(prefix + '_'):
                    board.pos = (board.pos[0], tower_d - cabinet_d, board.pos[2])
                    if board.name.endswith(('_top', '_bottom')):
                        board.width -= 2 * thick
                        board.pos = (board.pos[0] + thick, board.pos[1], board.pos[2])

    groups = overhead.get('shelf_groups', [])
    if overhead.get('middle_shelf', False):
        groups = [{'count': 1, 'width': total_w, 'depth': tower_d - back_thick,
                   'bottom': mm(upper_z + (upper_height - thick) / 2)}]
        if 'middle_shelf_front_setback' in overhead:
            groups[0]['front_setback'] = float(overhead['middle_shelf_front_setback'])
    for group_index, group in enumerate(groups):
        for shelf_index in range(int(group['count'])):
            # Shelves span bays, never pass through the full-height tower sides.
            start = float(group.get('left', 0))
            end = start + float(group.get('width', desk_w))
            depth = float(group['depth'])
            shelf_z = float(group['bottom']) + shelf_index * float(group.get('spacing', 300))
            if depth <= 0 or depth > min(left_depth, tower_d) or not upper_z <= shelf_z <= total_h - 2 * thick:
                raise ValueError('Overhead shelf exceeds side depth or furniture height')
            for bay, (left_side, right_side) in enumerate(upper_bays):
                lo, hi = left_side.pos[0] + left_side.width, right_side.pos[0]
                lo, hi = max(lo, start), min(hi, end)
                if hi <= lo:
                    continue
                is_tower = right_side.name == 'upper_right_side'
                has_back = (tower.get('back', {}).get('enabled', False) if is_tower
                            else desk_back_cfg.get('enabled', False))
                back_gap = back_thick if has_back else 0
                bay_depth = depth
                if has_back:
                    bay_depth = min(bay_depth, tower_d-back_gap)
                if 'front_setback' in group:
                    setback = float(group['front_setback'])
                    bay_depth = tower_d - back_gap - setback
                    if setback < 0 or not 0 < bay_depth <= min(left_side.depth, right_side.depth):
                        raise ValueError('Overhead shelf front setback exceeds bay depth')
                suffix = '_tower' if is_tower else (f'_bay{bay}' if bay else '')
                shelf = Board(f'overhead_shelf_{group_index}_{shelf_index}' + suffix,
                              hi - lo, thick, bay_depth,
                              (lo, tower_d - back_gap - bay_depth, shelf_z), _C_SHELF, movable=False)
                _add_led_groove(shelf, group.get('led_groove', overhead.get('led_groove')))
                boards.append(shelf)
                bay_sides = (left_side, right_side)
                for side in bay_sides:
                    if (abs(shelf.pos[0] - side.pos[0] - side.width) < 1e-6 or
                            abs(shelf.pos[0] + shelf.width - side.pos[0]) < 1e-6):
                        _shelf_side_joint(shelf, side, joints)

    _fit_back_rabbets(boards, tower, thick, back_thick, peers=desk_back_frames)
    if desk_back_frames:
        _fit_back_rabbets(boards, {'back': desk_back_cfg}, thick, back_thick, desk_back_frames,
                          peers=[('upper_tower_back', 'upper_divider', 'upper_right_side', 'module_bridge', 'upper_top'),
                                 ('tower_back', 'tower_left_side', 'tower_right_side',
                                  'tower_bottom' if tower.get('back', {}).get('behind_drawers', True)
                                  else 'tower_drawer_top', 'module_bridge')]
                          if tower.get('back', {}).get('enabled') else [])
    _merge_back_rabbets(boards)
    _apply_hidden_confirmats(boards, cfg.get('joinery', {}))
    if cfg.get('joinery', {}).get('mixed_shared_sides', False):
        _mix_shared_side_joints(boards)
    notes = append_monitor_setup(boards, desk.get('monitor_setup', {}))
    notes.extend(append_lighting_controls(boards, cfg.get('lighting_controls', {})))
    if bottom_thickness == 3:
        notes.append('Dna szuflad: HDF 3 mm, wsunięty 3 mm we frez frontu; '
                     'wkręty do drewna 3 × 16 mm od spodu do boków i tyłu. '
                     'Otwory dna Ø3 przelotowe, pilotaż Ø2 × 13 mm; dobór wkrętów jest założeniem projektu.')
    handle = _resolve_handle(front.get('handle'))
    if handle and 'model' in handle:
        notes.append(f"Uchwyty: {handle['name']}, {drawer_count} szt.; rozstaw {handle['hole_spacing']} mm, "
                     f"otwory Ø{handle.get('hole_diameter', 5)} na wylot. Źródło: {handle['source']}")
    if 'source' in slide_cfg:
        notes.append(f"Prowadnice szuflad: {slide_cfg['name']}; wysuw {slide_cfg.get('travel_mm', nl_used)} mm. "
                     f"Źródło: {slide_cfg['source']}")
    keyboard_cfg = desk.get('keyboard_tray', {})
    if keyboard_cfg.get('enabled', True):
        keyboard_slide = _load_slides_db()[keyboard_cfg.get('slides', {}).get('model', 'GTV-H45')]
        notes.append('Półka klawiatury: ' + keyboard_slide['name'] + '.')
        if keyboard_slide.get('symbol') in ('PK-0H45500XP', 'PK-L-H45-450-B-20', 'PK-L-H45-400-B-20'):
            notes.extend([
                f"Luz prowadnic klawiatury: {keyboard_slide['side_clearance_mm']} mm na stronę.",
                'Nawierty Ø3 × 10 mm pod wkręty są założeniem projektu; dobrać do wkrętów i materiału płyty.',
                f"Dobór prowadnic do półki o szerokości {keyboard_cfg['width']} mm wymaga potwierdzenia; "
                f"udźwig katalogowy {keyboard_slide['load_capacity_kg']} kg nie potwierdza tej szerokości.",
                'Karta prowadnic: ' + keyboard_slide['source'],
            ])
    return DrawerModel(boards=_center_model(boards), max_travel=float(slide_cfg.get('travel_mm', nl_used)),
                       slide_model=drawers['slides']['model'], slide_nl=nl_used,
                       joints=joints, drawer_count=drawer_count, notes=notes)


def _append_handle_preview(boards, config):
    """Schematic flat pull, aligned with the final drilling positions."""
    handle = _resolve_handle(config)
    if not handle or not handle.get('preview', True):
        return
    front = next(b for b in boards if b.name == 'front')
    holes = [h for h in front.holes if h.kind == 'handle']
    if len(holes) != 2:
        return
    length = float(handle.get('length_mm', handle['hole_spacing'] + 20))
    height = float(handle.get('height_mm', 20))
    projection = float(handle.get('projection_mm', 25))
    metal = min(3, projection)
    center_x = sum(h.x for h in holes)/2
    center_z = sum(h.z for h in holes)/2
    color = (0.08, 0.08, 0.08, 1) if 'black' in handle.get('finish', '') else (0.65, 0.65, 0.67, 1)
    boards.append(Board('handle_bar', length, height, metal,
                        (center_x-length/2, front.pos[1]-projection, center_z-height/2),
                        color, movable=True, fabrication=False))
    for index, hole in enumerate(holes):
        boards.append(Board(f'handle_mount_{index}', 8, height, projection-metal,
                            (hole.x-4, front.pos[1]-projection+metal, center_z-height/2),
                            color, movable=True, fabrication=False))


def _fit_back_rabbets(boards, tower, thick, back_thick, frames=None, peers=()):
    back_cfg = tower.get('back', {})
    rabbet = back_cfg.get('rabbet')
    if not back_cfg.get('enabled') or not rabbet:
        return
    width, depth = float(rabbet['width']), float(rabbet['depth'])
    horizontal = rabbet.get('horizontal', False)
    shared_width = float(rabbet.get('shared_width', width))
    if not 0 < width < thick or not 0 < shared_width < thick or depth < back_thick or depth >= thick:
        raise ValueError('Back rabbet must fit board thickness and match back panel thickness')
    if horizontal and 2 * shared_width > thick:
        raise ValueError('Back rabbets must not exceed half the shared board thickness')
    bd = {b.name: b for b in boards}
    lower_bottom = 'tower_bottom' if back_cfg.get('behind_drawers', True) else 'tower_drawer_top'
    frames = frames if frames is not None else (
        ('tower_back', 'tower_left_side', 'tower_right_side', lower_bottom, 'module_bridge'),
        ('upper_tower_back', 'upper_divider', 'upper_right_side', 'module_bridge', 'upper_top'),
    )
    def overlap_for(frame, idx):
        if 'shared_width' not in rabbet:
            return width
        opposite = {1: 2, 2: 1, 3: 4, 4: 3}[idx]
        axis = 2 if idx in (1, 2) else 0
        dim = 'height' if axis == 2 else 'width'
        back = bd[frame[0]]
        for other in [*frames, *peers]:
            if other[0] == frame[0] or other[0] not in bd or frame[idx] != other[opposite]:
                continue
            peer = bd[other[0]]
            if min(back.pos[axis]+getattr(back, dim), peer.pos[axis]+getattr(peer, dim)) > max(back.pos[axis], peer.pos[axis]):
                return shared_width
        return width
    # Evaluate against unexpanded rectangles; adjacent outer corners must not
    # turn an otherwise external edge into a shared edge.
    overlaps = {frame[0]: [min(overlap_for(candidate, i)
                for candidate in [*frames, *peers]
                if candidate[0] in bd and candidate[i] == frame[i])
                for i in range(1, 5)] for frame in frames}
    for back_name, left, right, bottom, top in frames:
        back = bd[back_name]
        wl, wr, wb, wt = overlaps[back_name]
        back.width += wl + wr
        back.pos = (back.pos[0] - wl, back.pos[1], back.pos[2] - (wb if horizontal else 0))
        back.height += wb + wt if horizontal else 0
        edges = [(left, 'right', wl), (right, 'left', wr)]
        if horizontal:
            edges.extend([(bottom, 'top', wb), (top, 'bottom', wt)])
        for name, edge, edge_width in edges:
            board = bd[name]
            # The supporting horizontal panel must reach the common rear plane.
            if name == 'tower_drawer_top':
                board.depth = float(tower['depth'])
                for groove in board.grooves:
                    if groove['kind'] == 'led_wire':
                        groove['span_y'] = board.depth - groove['y']
            x = max(back.pos[0], board.pos[0]) - board.pos[0]
            z = max(back.pos[2], board.pos[2]) - board.pos[2]
            span_x = min(back.pos[0] + back.width, board.pos[0] + board.width) - board.pos[0] - x
            span_z = min(back.pos[2] + back.height, board.pos[2] + board.height) - board.pos[2] - z
            board.grooves.append(dict(kind='back_rabbet', face='+y', width=edge_width, depth=depth,
                                      edge=edge, x=x, z=z, span_x=span_x, span_z=span_z))


def _merge_back_rabbets(boards):
    """A machining edge has a single continuous rectangular back rebate."""
    for board in boards:
        grouped = {}
        other = []
        for groove in board.grooves:
            if groove['kind'] != 'back_rabbet':
                other.append(groove)
                continue
            key = (groove['face'], groove['edge'])
            if key not in grouped:
                grouped[key] = dict(groove)
                continue
            merged = grouped[key]
            if (merged['width'], merged['depth']) != (groove['width'], groove['depth']):
                raise ValueError(f'Incompatible back rebates on {board.name}: {key}')
            for axis in ('x', 'z'):
                end = max(merged[axis] + merged['span_' + axis],
                          groove[axis] + groove['span_' + axis])
                merged[axis] = min(merged[axis], groove[axis])
                merged['span_' + axis] = end - merged[axis]
        board.grooves = other + list(grouped.values())


def _apply_hidden_confirmats(boards, config):
    """Put screw heads on explicitly hidden faces; keep upper-module feet dowelled."""
    by_name = {board.name: board for board in boards}
    hidden = config.get('hidden_faces', {})
    for name, faces in hidden.items():
        if name not in by_name or any(f not in ('-x', '+x', '-y', '+y', '-z', '+z') for f in faces):
            raise ValueError(f'Invalid hidden joint face for {name}')
    for board in boards:
        for hole in board.joint_holes:
            if hole.element != 1 or hole.hole_type != 'dowel':
                continue
            # Upper module is removable from the common bridge; its feet stay dowelled.
            if board.name == 'module_bridge' and hole.partner.startswith('upper_'):
                continue
            if hole.partner in config.get('keep_dowels', {}).get(board.name, []):
                continue
            outside = ('-' if hole.direction[0] == '+' else '+') + hole.direction[1]
            if outside not in hidden.get(board.name, []):
                continue
            partner = by_name[hole.partner]
            matches = [other for other in partner.joint_holes
                       if other.element == 2 and other.partner == board.name
                       and (other.x, other.y, other.z) == (hole.x, hole.y, hole.z)
                       and other.hole_type == 'dowel']
            if len(matches) != 1:
                raise ValueError(f'Unpaired joint: {board.name} / {partner.name}')
            matches[0].hole_type = 'confirmat'
            hole.hole_type = 'confirmat'
            hole.direction = outside
            axis = 'xyz'.index(outside[-1])
            size = (board.width, board.depth, board.height)[axis]
            setattr(hole, outside[-1], board.pos[axis] + (size if outside[0] == '+' else 0))


def _mix_shared_side_joints(boards):
    """Opposing shelves conceal screw heads; offset the dowels to avoid their bores."""
    by_name = {board.name: board for board in boards}
    for board in boards:
        left = [h for h in board.joint_holes if h.element == 1
                and h.direction == '-x' and h.hole_type == 'dowel']
        for screw in left:
            opposing = [h for h in board.joint_holes if h.element == 1
                        and h.direction == '+x' and h.hole_type == 'dowel'
                        and h.z == screw.z and abs(h.y-screw.y) < 20]
            if not opposing:
                continue
            dowel, = opposing
            targets = []
            for hole in (screw, dowel):
                partner = by_name[hole.partner]
                mate, = [h for h in partner.joint_holes if h.element == 2
                         and h.partner == board.name
                         and (h.x, h.y, h.z) == (hole.x, hole.y, hole.z)]
                targets.append(mate)
            partner = by_name[dowel.partner]
            new_y = max(dowel.y, screw.y) + 20
            if new_y + 4 > min(board.pos[1]+board.depth, partner.pos[1]+partner.depth):
                raise ValueError(f'No room to offset opposed dowels on {board.name}')
            dowel.y = targets[1].y = new_y
            screw.hole_type = targets[0].hole_type = 'confirmat'
            screw.x = board.pos[0] + board.width
            screw.direction = '+x'
