"""Two-column kitchen tall unit with appliance niches and Axis Pro drawers."""

from pathlib import Path

import yaml

from parts.drawer import Board, DrawerModel, Hole, _center_model
from parts.front_rules import SIDE_REVEAL, END_REVEAL, VERTICAL_GAP, DOUBLE_DOOR_GAP
from parts.axis_pro import axis_spec, add_axis_drawer
from parts.kitchen_hardware import add_side_hinges, add_lift_hinges, add_handles, hinge_spec
from parts.joinery import add_panel_joints, add_adjacent_cabinet_ties
from parts.machining import validate_drilling
from parts.manual_cutout import add_side_cutout_guide
from parts.kitchen_ventilation import add_plinth_opening, add_rear_notch, add_upper_back


_WOOD = (0.82, 0.67, 0.47, 1.0)
_SHELF = (0.72, 0.57, 0.38, 1.0)
_DARK = (0.08, 0.08, 0.08, 1.0)
_WHITE = (0.91, 0.91, 0.91, 1.0)
_AXIS = (0.18, 0.20, 0.22, 1.0)

# Installation dimensions are model data, not project geometry.  A project
# selects a model; the vertical layout is then derived from its required
# opening, appliance fascia and the configured board thickness/reveals.
_APPLIANCE_MODELS = {
    'SAMSUNG-BRB38G705DWWEF': {
        'envelope': (690, 1935, 550), 'niche': (714, 1940, 580),
        # Door heights and elevations above the appliance base (manual p.32).
        'doors': {
            'freezer': {'bottom': 50, 'height': 621},
            'refrigerator': {'bottom': 735, 'height': 1147},
        },
        'installation': {
            'source': 'https://downloadcenter.samsung.com/content/UM/202404/20240422175259820/DA68-04801C-00_PL__um_sepol.pdf',
            'page': 32,
        },
    },
    'ELECTROLUX-EOE7C31Z': {
        'niche': (560, 590, 550),
        'body_height': 589,
        'installation': {
            'front_below_support': 3,
            'source': 'https://api.electrolux-medialibrary.com/asset/f47112f2-6040-4696-b7d7-b55af15d7494/E4RM3Q/e091b0cc-fe00-43a1-a878-f6e654be481b/PDF/e091b0cc-fe00-43a1-a878-f6e654be481b.pdf',
            'page': 37,
        },
        'front': {'width': 596, 'height': 589, 'top_above_support': 594, 'depth': 20,
                  # Installation manual p.37: fascia bottom 5 mm ABOVE support.
                  'side_reveal': 2, 'bottom_overhang': -5},
    },
    'ELECTROLUX-EMS4253TMK': {
        'niche': (560, 380, 550),
        # Overall appliance depth includes the 20 mm fascia ahead of the carcass.
        # The installation niche is deeper for ventilation/cables, not solid metal.
        'overall_depth': 377,
        'installation': {
            'source': 'https://www.electrolux.pl/services/eml/asset/e71ace65-48a1-49dc-9c43-9ba7a267b629/E4RM3Q/250513HMLN/PDF/250513HMLN.pdf',
            'page': 25,
        },
        'front': {'width': 595, 'height': 388, 'depth': 20,
                  # EMS manual p.25: 4.5 mm below / 3.5 mm above the opening.
                  'side_reveal': 2.5, 'bottom_overhang': 4.5},
    },
}


def _appliance_model(config):
    model = config.get('model')
    try:
        return _APPLIANCE_MODELS[model]
    except KeyError as exc:
        raise ValueError(f'Unknown appliance model: {model!r}') from exc


def _model_front(model, overrides):
    """Appliance fascia geometry belongs to its model, not the furniture YAML."""
    if overrides:
        raise ValueError('Appliance front dimensions must be defined in the model library')
    return dict(model['front'])


def _add_appliance(boards, name, width, height, depth, pos, colour, label):
    """Preview-only appliance envelope; it is never sent to the cut list."""
    boards.append(Board(name, width, height, depth, pos, colour,
                        movable=False, fabrication=False))
    boards[-1].label = label


def _add_appliance_front(boards, name, width, height, depth, pos, label):
    """Visible appliance fascia; separate from its body/niche envelope."""
    _add_appliance(boards, name, width, height, depth, pos, _DARK, label)
    return boards[-1]


def _add_front_detail(boards, front, kind):
    """Non-fabricated, dimensional illustration of the supplied appliance face."""
    x, y, z = front.pos
    face_y = y - 1.2
    def add(name, width, height, dx, dz, colour, depth=1.0):
        boards.append(Board(f'{front.name}_{name}', width, depth, height,
                            (x + dx, face_y - depth, z + dz), colour,
                            movable=False, fabrication=False))
    if kind == 'oven':
        # EOE7C31Z: black glass door and upper control panel.  The handle is
        # included in the photographic texture, so do not duplicate it in 3D.
        add('glass', front.width - 28, front.height - 108, 14, 14, (0.015, 0.020, 0.028, 1))
        add('control_panel', front.width - 18, 72, 9, front.height - 88, (0.10, 0.12, 0.14, 1))
        add('display', 110, 20, (front.width - 110) / 2, front.height - 62, (0.12, 0.50, 0.68, 1), 1.8)
    elif kind == 'microwave':
        # EMS4253TMK: left perforated-glass door and the right touch-control strip.
        add('glass', front.width - 145, front.height - 72, 14, 36, (0.025, 0.030, 0.038, 1))
        add('control_panel', 102, front.height - 28, front.width - 116, 14, (0.10, 0.12, 0.14, 1))
        add('display', 64, 20, front.width - 97, front.height - 68, (0.12, 0.50, 0.68, 1), 1.8)
        for index in range(4):
            add(f'touch_key_{index}', 50, 11, front.width - 90,
                front.height - 110 - index * 40, (0.36, 0.38, 0.40, 1), 1.5)


def _add_front_photo(boards, front, texture):
    """Put a catalogue-style front image just ahead of the 3D fascia."""
    photo = Board(f'{front.name}_photo', front.width, front.height, 0.4,
                  (front.pos[0], front.pos[1] - 0.8, front.pos[2]),
                  (1, 1, 1, 1), movable=False, fabrication=False)
    photo.texture = texture
    photo.label = 'Tekstura podglądowa frontu AGD — nie jest elementem produkcyjnym'
    boards.append(photo)


def _add_fridge_sliding_connectors(boards, door, config):
    """Proportional preview centres; these are not a Samsung drilling template."""
    fraction = float(config.get('width_fraction_from_hinge', .75))
    heights = [float(v) for v in config.get('height_fractions', [.25, .75])]
    if not 0 < fraction < 1 or not heights or any(not 0 < v < 1 for v in heights):
        raise ValueError('Sliding connector centre fractions must be between 0 and 1')
    x = door.width * (fraction if door.opening == 'hinge_left' else 1 - fraction)
    width, height, depth = 90, 38, 12
    if not width / 2 <= x <= door.width - width / 2 or any(
            not height / 2 <= v * door.height <= door.height - height / 2 for v in heights):
        raise ValueError('Sliding connector preview must fit inside the door')
    for index, fraction_z in enumerate(heights):
        connector = Board(f'{door.name}_sliding_connector_{index}', width, height, depth,
                          (door.pos[0] + x - width / 2, door.pos[1] + door.depth,
                           door.pos[2] + fraction_z * door.height - height / 2),
                          _DARK, movable=False, fabrication=False)
        connector.movable = True
        connector.motion_parent = door.name
        connector.label = ('Plastikowy łącznik ślizgowy frontu z drzwiami lodówki; '
                           'pozycję potwierdzić z instrukcją Samsung')
        boards.append(connector)


def _add_adjustable_legs(boards, config, columns, depth, height, thickness):
    """Place selected kitchen feet and bore their fixing pattern into the bottom."""
    if not config.get('enabled', True):
        return
    with (Path(__file__).parents[1] / 'db/kitchen_legs.yaml').open() as stream:
        library = yaml.safe_load(stream)['legs']
    model = config.get('model', 'EMUCA-BONE-2024417')
    if model not in library:
        raise ValueError(f'Unknown kitchen leg model: {model}')
    spec = library[model]
    if not spec['height_range'][0] <= height <= spec['height_range'][1]:
        raise ValueError(f'{model}: plinth height must fit the leg adjustment range')
    side = float(config.get('side_offset', 65))
    front = float(config.get('front_offset', 80))
    rear = float(config.get('rear_offset', 65))
    plate_w, plate_d = spec['plate_width'], spec['plate_depth']
    plate_h, foot_h = spec['plate_height'], 8
    if front - plate_d / 2 < thickness or rear < plate_d / 2 or depth - rear - front < plate_d:
        raise ValueError('Leg rows must fit behind the plinth without overlapping')
    bottoms = [board for board in boards if board.name.startswith('kitchen_bottom')]
    for column, x0, width in columns:
        if side - plate_w / 2 < thickness or width - 2 * side < plate_w:
            raise ValueError('Leg columns must fit behind the side plinths without overlapping')
        for side_name, x in (('left', x0 + side), ('right', x0 + width - side)):
            for row, y in (('front', front), ('rear', depth - rear)):
                prefix = f'kitchen_leg_{column}_{side_name}_{row}'
                matching = [board for board in bottoms
                            if (board.pos[0] <= x - plate_w / 2
                                and x + plate_w / 2 <= board.pos[0] + board.width
                                and board.pos[1] <= y - plate_d / 2
                                and y + plate_d / 2 <= board.pos[1] + board.depth)]
                if len(matching) != 1 or spec['pilot_depth'] >= matching[0].height:
                    raise ValueError(f'{prefix}: leg plate and pilots must fit one bottom panel')
                bottom = matching[0]
                for dx in (-spec['mounting_spacing_x'] / 2, spec['mounting_spacing_x'] / 2):
                    for dy in (-spec['mounting_spacing_y'] / 2, spec['mounting_spacing_y'] / 2):
                        bottom.holes.append(Hole(x + dx, y + dy, bottom.pos[2],
                                                 spec['pilot_diameter'], spec['pilot_depth'],
                                                 '-z', 'kitchen_leg_mount'))
                shaft_h = height - foot_h - plate_h
                sleeve_h = round(shaft_h * .65 * 2) / 2
                for part, size, z, part_h, shape, colour in (
                    ('foot', spec['foot_diameter'], 0, foot_h, 'cylinder_z', _DARK),
                    ('stem', spec['stem_diameter'], foot_h, shaft_h, 'cylinder_z', (0.35, .36, .38, 1)),
                    ('sleeve', spec['stem_diameter'] + 2, height - plate_h - sleeve_h,
                     sleeve_h, 'cylinder_z', _DARK),
                    ('plate', plate_w, height - plate_h, plate_h, '', _DARK),
                ):
                    part_depth = plate_d if part == 'plate' else size
                    boards.append(Board(f'{prefix}_{part}', size, part_h, part_depth,
                                        (x - size / 2, y - part_depth / 2, z), colour,
                                        movable=False, fabrication=False,
                                        preview_shape=shape,
                                        label=f'{model}: poglądowy obrys, nawierty płytki w dnie'))


def load_kitchen_tall_unit(path: str) -> DrawerModel:
    with Path(path).open() as stream:
        root = yaml.safe_load(stream)
    cfg = root['kitchen_tall_unit']
    hinge = hinge_spec(cfg.get('hinges', {}))
    material = cfg.get('material', {})
    t = float(material.get('thickness', 18))
    h = float(cfg['height'])
    d = float(cfg['depth'])
    plinth = float(cfg.get('plinth', {}).get('height', 100))
    plinth_inset_front = float(cfg.get('plinth', {}).get('inset_front', 0))
    if min(t, h, d, plinth) <= 0:
        raise ValueError('Kitchen tall unit dimensions must be positive')
    if not 0 <= plinth_inset_front < d - t:
        raise ValueError('plinth.inset_front must leave room for the plinth side boards')

    left = cfg['left_column']
    right = cfg['right_column']
    left_clear = float(left['clear_width'])
    right_outer = float(right['width'])
    right_clear = right_outer - 2 * t
    if right_clear <= 0:
        raise ValueError('Right column width must exceed two board thicknesses')
    left_outer = left_clear + 2 * t
    # Each column retains its own side boards, even with shared end panels.
    total_w = left_outer + right_outer
    z0, ztop = plinth + t, h - t
    if ztop <= z0:
        raise ValueError('Plinth and top leave no cabinet height')
    x_mid = left_outer - t
    boards = [
        Board('kitchen_left_side', t, h - plinth - 2 * t, d, (0, 0, z0), _WOOD,
              movable=False, cabinet_id='fridge_column', cabinet_side='left'),
        Board('kitchen_left_right_side', t, h - plinth - 2 * t, d, (x_mid, 0, z0), _WOOD,
              movable=False, cabinet_id='fridge_column', cabinet_side='right'),
        Board('kitchen_right_left_side', t, h - plinth - 2 * t, d, (left_outer, 0, z0), _WOOD,
              movable=False, cabinet_id='appliance_column', cabinet_side='left'),
        Board('kitchen_right_side', t, h - plinth - 2 * t, d, (total_w - t, 0, z0), _WOOD,
              movable=False, cabinet_id='appliance_column', cabinet_side='right'),
    ]
    panels = cfg.get('panels', {})
    for end, elevation, default in (('top', ztop, 'shared'), ('bottom', plinth, 'separate')):
        mode = panels.get(end, default)
        if mode not in ('shared', 'separate'):
            raise ValueError(f'panels.{end} must be shared or separate')
        if mode == 'shared':
            boards.append(Board(f'kitchen_{end}', total_w, t, d,
                                (0, 0, elevation), _WOOD, movable=False))
        else:
            for column, x, width in (('left', 0, left_outer), ('right', left_outer, right_outer)):
                boards.append(Board(f'kitchen_{end}_{column}', width, t, d,
                                    (x, 0, elevation), _WOOD, movable=False))
    boards += [
        Board('kitchen_plinth_front', total_w, plinth, t,
              (0, plinth_inset_front, 0), _SHELF, movable=False),
        Board('kitchen_plinth_left', t, plinth, d-t-plinth_inset_front,
              (0, plinth_inset_front+t, 0), _SHELF, movable=False),
        Board('kitchen_plinth_right', t, plinth, d-t-plinth_inset_front,
              (total_w-t, plinth_inset_front+t, 0), _SHELF, movable=False),
    ]
    plinth_boards = boards[-3:]
    grille = cfg.get('fridge_ventilation', {})
    if grille.get('enabled', True):
        add_plinth_opening(plinth_boards[0], grille, 0, left_outer)
        for end in ('top', 'bottom'):
            for panel in boards:
                if panel.name in (f'kitchen_{end}', f'kitchen_{end}_left'):
                    add_rear_notch(panel, grille, end, t, left_clear)

    fridge = left['fridge']
    fridge_model = _appliance_model(fridge)
    fridge_w, fridge_h, fridge_d = fridge_model['niche']
    if fridge_w > left_clear or fridge_h > ztop - z0:
        raise ValueError('Fridge niche exceeds the left column')
    divider_z = z0 + fridge_h
    fridge_front = fridge.get('fronts', {})
    fridge_gap = VERTICAL_GAP
    front_reveal = SIDE_REVEAL
    front_width = left_outer - 2 * front_reveal
    if not 0 < front_reveal < t or not 0 < front_width <= left_outer:
        raise ValueError('Samsung front width or outer reveal is invalid')
    appliance_doors = fridge_model['doors']
    freezer_top = appliance_doors['freezer']['bottom'] + appliance_doors['freezer']['height']
    split_center = z0 + (freezer_top + appliance_doors['refrigerator']['bottom']) / 2
    front_bottom = plinth + END_REVEAL
    freezer_h = split_center - fridge_gap / 2 - front_bottom
    lift_bottom = divider_z + front_reveal
    refrigerator_bottom = front_bottom + freezer_h + fridge_gap
    refrigerator_h = lift_bottom - fridge_gap - refrigerator_bottom
    if min(freezer_h, refrigerator_h) <= 0:
        raise ValueError('Fridge front split must fit between the plinth and upper cabinet')
    boards.append(Board('fridge_top_divider', left_clear, t, d, (t, 0, divider_z), _SHELF, movable=False))
    if grille.get('enabled', True):
        add_rear_notch(boards[-1], grille, 'middle', t, left_clear)
        add_upper_back(boards, grille, t, left_clear, divider_z + t, ztop, d, t, _WOOD)
    top_door = Board('fridge_top_lift_door', front_width, h - END_REVEAL - lift_bottom, 18,
                     ((left_outer-front_width)/2, -18, lift_bottom), _WOOD, movable=True)
    top_door.opening = 'lift_up'
    boards.append(top_door)
    top_panel = next(b for b in boards if b.name in ('kitchen_top', 'kitchen_top_left'))
    add_lift_hinges(top_door, top_panel, hinge)
    appliance_w, appliance_h, appliance_d = fridge_model['envelope']
    if appliance_w > fridge_w or appliance_h > fridge_h or appliance_d > fridge_d:
        raise ValueError('Fridge appliance envelope exceeds its niche')
    appliance_x = t + (left_clear-appliance_w)/2
    # Schematic door skins occupy the front of the existing overall envelope.
    # These preview dimensions are not an installation/drilling template.
    fridge_door_depth = 30
    _add_appliance(boards, 'appliance_fridge_samsung_brb38g705dwwef', appliance_w, appliance_h,
                   appliance_d - fridge_door_depth,
                   (appliance_x, fridge_door_depth, z0), (0.65, 0.67, 0.68, 1),
                   'Samsung BRB38G705DWWEF')
    for section, geometry in appliance_doors.items():
        _add_appliance(boards, f'appliance_fridge_samsung_brb38g705dwwef_{section}_door',
                       appliance_w, geometry['height'], fridge_door_depth,
                       (appliance_x, 0, z0 + geometry['bottom']), _WHITE,
                       'Samsung — door height/elevation from installation manual p.32; thickness schematic')
    hinge_side = fridge_front.get('hinge_side', 'right')
    if hinge_side not in ('left', 'right'):
        raise ValueError("fridge.fronts.hinge_side must be 'left' or 'right'")
    front_specs = (
        ('fridge_lower_door', front_bottom, freezer_h, float(fridge_front.get('lower_thickness', 18))),
        ('fridge_upper_door', refrigerator_bottom, refrigerator_h, float(fridge_front.get('upper_thickness', 18))),
    )
    for name, f_z, f_h, f_t in front_specs:
        if f_t <= 0 or f_t > 23:
            raise ValueError('Samsung Slide Hinge front thickness is out of range')
        door = Board(name, front_width, f_h, f_t,
                     ((left_outer-front_width)/2, -f_t, f_z), _WOOD, movable=True)
        door.opening = f'hinge_{hinge_side}'
        boards.append(door)
        # Sliding coupling joins two independently hinged doors. Furniture
        # hinges are still necessary to carry the overlay panel.
        add_side_hinges(door, hinge_side, boards[0] if hinge_side == 'left' else boards[1], hinge)
        _add_fridge_sliding_connectors(boards, door, fridge_front.get('sliding_connectors', {}))

    r_x = left_outer + t
    drawers = right['drawers']
    raw_heights = list(drawers['front_heights'])
    if len(raw_heights) == 3 and raw_heights[-1] is None and all(v is not None for v in raw_heights[:-1]):
        raw_heights[-1] = freezer_h - 2 * VERTICAL_GAP - sum(float(v) for v in raw_heights[:-1])
    drawer_heights = [float(v) for v in raw_heights]
    if len(drawer_heights) != 3 or any(v <= 0 for v in drawer_heights):
        raise ValueError('Right column requires three positive drawer front heights')
    gap = VERTICAL_GAP
    axis = drawers['axis_pro']
    axis_data, nl, variants = axis_spec(axis)
    # Keep the right drawer-front group level with the lower freezer panel.
    z = front_bottom
    if abs(sum(drawer_heights) + gap * (len(drawer_heights) - 1) - freezer_h) > 0.01:
        raise ValueError('Right drawer fronts plus gaps must equal freezer_height')
    rail_depth = float(drawers.get('rail_depth', 100))
    rail_thickness = float(drawers.get('rail_thickness', t))
    if not 0 < rail_depth <= d or rail_thickness < gap:
        raise ValueError('Drawer rails must fit the carcass depth and cover the front gap')
    datum = z0
    for index, front_h in enumerate(drawer_heights):
        # Keep the lowest front-connector bore at least 47.5 mm above its
        # bottom edge (catalogue), even over a narrow separator rail.
        datum = max(datum, z + 15)
        rail_z = z + front_h + (gap - rail_thickness) / 2
        # The final ceiling is the underside of the oven support. Its top is
        # 3 mm above the last drawer front, according to the appliance model.
        support_gap = _appliance_model(right['oven'])['installation']['front_below_support']
        ceiling = rail_z if index < 2 else z + front_h + support_gap - t
        add_axis_drawer(boards, f'kitchen_drawer_{index}', boards[2], boards[3],
                        z, front_h, datum, ceiling, axis_data, nl, variants[index], _WOOD)
        if index < 2:
            boards.append(Board(f'kitchen_drawer_rail_{index}', right_clear,
                                rail_thickness, rail_depth, (r_x, 0, rail_z),
                                _SHELF, movable=False))
            datum = rail_z + rail_thickness
        z += front_h + gap
    drawer_end = z - gap

    oven = right['oven']
    oven_model = _appliance_model(oven)
    oven_w, oven_h, oven_d = oven_model['niche']
    oven_front = _model_front(oven_model, oven.get('front'))
    if 'drawer_support_clearance' in right or 'top_board_overlap' in oven:
        raise ValueError('Remove drawer_support_clearance/top_board_overlap: installation geometry comes from the appliance model')
    support_clearance = float(oven_model['installation']['front_below_support'])
    top_overlap = float(oven_front['top_above_support']) - oven_h
    if not 0 <= top_overlap <= t:
        raise ValueError('Oven top overlap must fit the divider thickness')
    oven_z = drawer_end + support_clearance
    oven_front_top = oven_z + float(oven_front['top_above_support'])
    oven_divider_z = oven_z + oven_h
    body_height = float(oven_model['body_height'])
    if oven_divider_z < oven_z + body_height:
        raise ValueError('Oven top divider collides with appliance body')
    boards.append(Board('right_drawer_top', right_clear, t, d,
                        (r_x, 0, oven_z - t), _SHELF, movable=False))
    for board in boards:
        if board.name.startswith('kitchen_drawer_') and not board.name.endswith('_front'):
            if board.pos[2] + board.height > oven_z - t:
                raise ValueError('Drawer hardware or box collides with the oven support')
    _add_appliance(boards, 'appliance_oven_electrolux_eoe7c31z', oven_w, body_height, oven_d,
                   (r_x + (right_clear-oven_w)/2, 0, oven_z), _DARK,
                   'Electrolux EOE7C31Z')
    oven_front_z = oven_z - float(oven_front['bottom_overhang'])
    oven_fascia = _add_appliance_front(
        boards, 'appliance_oven_electrolux_eoe7c31z_front',
        float(oven_front.get('width', 596)), oven_front_top - oven_front_z,
        float(oven_front.get('depth', 20)),
        (left_outer + float(oven_front.get('side_reveal', 2)), -float(oven_front.get('depth', 20)),
         oven_front_z),
        'Electrolux EOE7C31Z — fascia from support +5 to +594 mm')
    _add_front_detail(boards, oven_fascia, 'oven')
    _add_front_photo(boards, oven_fascia, 'assets/appliances/electrolux_eoe7c31z_front.png')
    microwave = right['microwave']
    microwave_model = _appliance_model(microwave)
    microwave_w, microwave_h, microwave_d = microwave_model['niche']
    microwave_front = _model_front(microwave_model, microwave.get('front'))
    microwave_body_depth = float(microwave_model['overall_depth']) - float(microwave_front['depth'])
    if not 0 < microwave_body_depth <= microwave_d:
        raise ValueError('Microwave body depth must fit its installation niche')
    microwave_z = oven_divider_z + t
    boards.append(Board('right_oven_microwave_divider', right_clear, t, d, (r_x, 0, oven_divider_z), _SHELF, movable=False))
    _add_appliance(boards, 'appliance_microwave_electrolux_ems4253tmk',
                   microwave_w, microwave_h, microwave_body_depth,
                   (r_x + (right_clear-microwave_w)/2, 0, microwave_z), _DARK,
                   'Electrolux EMS4253TMK')
    microwave_front_z = microwave_z - float(microwave_front['bottom_overhang'])
    microwave_fascia = _add_appliance_front(
        boards, 'appliance_microwave_electrolux_ems4253tmk_front',
        float(microwave_front.get('width', 595)), float(microwave_front.get('height', 388)),
        float(microwave_front.get('depth', 20)),
        (left_outer + float(microwave_front.get('side_reveal', 2.5)), -float(microwave_front.get('depth', 20)),
         microwave_front_z),
        'Electrolux EMS4253TMK — visible fascia 595 × 388 mm')
    _add_front_detail(boards, microwave_fascia, 'microwave')
    _add_front_photo(boards, microwave_fascia, 'assets/appliances/electrolux_ems4253tmk_front.png')
    upper_z = microwave_z + microwave_h + t
    boards.append(Board('right_microwave_upper_divider', right_clear, t, d, (r_x, 0, microwave_z + microwave_h), _SHELF, movable=False))
    upper_h = ztop - upper_z
    if upper_h <= 0:
        raise ValueError('Appliances and drawers do not fit the right column height')
    # Side-by-side doors and vertically adjacent fronts have distinct reveals.
    front_gap = DOUBLE_DOOR_GAP
    if front_gap <= 0:
        raise ValueError('Upper cabinet front gap must be positive')
    total_front_w = right_clear + 2 * t - 4 - front_gap
    left_front_w = round(total_front_w) / 2
    right_front_w = total_front_w - left_front_w
    microwave_front_top = microwave_front_z + float(microwave_front.get('height', 388))
    # The fronts form one continuous face with the appliances.  The lower
    # edge is therefore calculated from the microwave fascia, rather than
    # from the structural shelf above its installation niche.  This keeps
    # the requested reveal when a different microwave model is selected.
    upper_front_z = microwave_front_top + VERTICAL_GAP
    upper_front_h = h - END_REVEAL - upper_front_z
    left_door = Board('right_upper_left_door', left_front_w, upper_front_h, 18,
                      (r_x - t + 2, -18, upper_front_z), _WOOD, movable=True)
    right_door = Board('right_upper_right_door', right_front_w, upper_front_h, 18,
                       (left_door.pos[0] + left_front_w + front_gap, -18, upper_front_z), _WOOD, movable=True)
    left_door.opening, right_door.opening = 'hinge_left', 'hinge_right'
    boards += [left_door, right_door]
    add_side_hinges(left_door, 'left', boards[2], hinge)
    add_side_hinges(right_door, 'right', boards[3], hinge)
    shelves = int(right.get('upper_cabinet', {}).get(
        'shelves', right.get('upper_cabinet', {}).get('shelves_per_bay', 1)))
    for idx in range(shelves):
        shelf_z = round((upper_z + (idx+1) * upper_h / (shelves+1)) * 2) / 2
        boards.append(Board(f'right_upper_shelf_{idx}', right_clear, t, d,
                            (r_x, 0, shelf_z), _SHELF, movable=False))
    cutout = microwave.get('side_cutout', {})
    if cutout.get('enabled', False):
        cut_depth = float(cutout.get('depth', 120))
        cut_height = float(cutout.get('height', 280))
        rear_offset = float(cutout.get('rear_offset', 0))
        cut_y = d - rear_offset - cut_depth
        cut_z = microwave_z + (microwave_h-cut_height) / 2
        if (rear_offset < 0 or cut_depth <= 0 or cut_height <= 0
                or cut_height > microwave_h or cut_y < microwave_body_depth):
            raise ValueError('Microwave side cutout must fit behind the appliance and inside its niche')
        add_side_cutout_guide(boards[3], cutout, cut_y, cut_z, cut_depth, cut_height,
                              face='-x')
    _add_adjustable_legs(boards, cfg.get('legs', {}),
                         [('left', 0, left_outer), ('right', left_outer, right_outer)],
                         d, plinth, t)
    # Separate structural assemblies: the plinth is clipped to the legs.
    structural = [b for b in boards if b.fabrication and not b.movable
                  and min(b.width, b.height, b.depth) >= 12
                  and all(b is not plinth_board for plinth_board in plinth_boards)]
    joinery = cfg.get('joinery', {})
    joints = add_panel_joints(structural, joinery)
    joints += add_panel_joints(plinth_boards, {**joinery, 'visible': 'dowel'})
    joints += add_adjacent_cabinet_ties(boards, joinery.get('column_ties'))
    add_handles(boards, cfg.get('handles'))
    validate_drilling(boards)
    notes = [
        'Eight Emuca Bone 2024417 adjustable kitchen legs, four per carcass. Plate fixing centres 64 × 64 mm from the Emuca catalogue p.727; underside pilot Ø2.5 × 12 mm is a project choice for Ø4 wood screws in 18 mm board. Mounting plate preview is simplified.',
        'Samsung BRB38G705DWWEF: recommended niche 714 × 1940 × 580 mm (allowed width 712–720 and height 1938–1942). Sliding connectors couple the independently hinged furniture and appliance doors. Furniture panels have their own cup hinges; confirm their clearance against the actual appliance. The 18 mm panels are permitted; maximum panel mass is 23 kg for the refrigerator door and 15.5 kg for the freezer door.',
        'Electrolux EOE7C31Z: niche 590 × 560 × 550 mm; appliance envelope is preview only.',
        'Electrolux EMS4253TMK: overall depth 377 mm = 20 mm fascia + 357 mm rear envelope. Installation niche remains 380 × 560 × 550 mm; its free space is not part of the appliance body.',
        'GTV AXIS PRO: 16 mm bottom (LW-75 × NL-24) and rear (LW-87). Cut rear heights D/B/A: 199/116/84; purchased sides: 200/120/86. Catalogue pp.6–8 drilling; Ø2 × 12 connectors, project Ø3 × 12 runner pilots. Metal profile shape is simplified.',
        'AXIS PRO: GTV recommends additional railing for fronts taller than 284 mm; select and fit that accessory with its supplied template. Bottom fixing screws follow the metal-side template, not a guessed CNC pattern.',
        'GTV ZM-INHC09H04-BE H0: Ø35 × 12 cups, K=3 mm, cup-screw spacing 45 mm (offset 9.5); plate spacing 32 mm at 37 mm. Ø2.5 × 10 screw pilots are a project choice. Lift hinges attach to the top panel, adjusted -1 mm for 15 mm overlay.',
        'GTV NEO lift drilling is not generated: the previous unverified positions were removed. Choose force for the front mass and transfer the mounting template supplied with the lifts.',
        'Carcass joints: dowels on visible outer cheeks; confirmats through hidden inner cheeks and outer top/bottom faces. Assemble inner-cheek screws before joining columns. Plinth-clip fixing is still unresolved.',
    ]
    ties = joinery.get('column_ties') or {}
    if ties.get('enabled', True):
        notes.append(f"Column ties: aligned Ø{float(ties.get('diameter', 3)):g} through-bores in both adjoining side boards. Join the columns before installing the refrigerator. Select a suitable through-fastener and its head/retainer for this joint.")
    if grille.get('enabled', True):
        notes.append('Refrigerator ventilation: plinth, bottom, middle and top boards remain rectangular for cutting. Groove segments within the selected edge-distance limit and shallow Ø3 drill markers on unreachable segments trace the material to remove separately. The upper cabinet has furniture-board back ahead of the rear channel.')
    issues = [
        dict(operation='axis_bottom_fixing',
             boards=[f'kitchen_drawer_{i}_bottom' for i in range(3)],
             reason='Brak wymiarowanego szablonu wkrętów mocujących dno do metalowych boków AXIS PRO.'),
        dict(operation='gas_lift_mount',
             boards=['fridge_top_lift_door', 'kitchen_left_side', 'kitchen_left_right_side'],
             reason='Brak potwierdzonego szablonu montażowego i doboru podnośników klapy.'),
        dict(operation='fridge_slider_mount', boards=['fridge_lower_door', 'fridge_upper_door'],
             reason='Pozycje łączników Samsung są orientacyjne; brakuje szablonu ich mocowania.'),
    ]
    if cfg.get('legs', {}).get('enabled', True):
        issues.append(dict(operation='plinth_clip_mount',
                           boards=[b.name for b in plinth_boards],
                           reason='Klipsy cokołu Emuca Bone wymagają ustalenia sposobu zamocowania do płyt cokołu.'))
    return DrawerModel(boards=_center_model(boards), max_travel=nl,
                       slide_model='GTV Axis Pro', slide_nl=int(nl), drawer_count=3,
                       joints=joints, notes=notes, machining_issues=issues)
