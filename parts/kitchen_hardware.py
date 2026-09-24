"""Carcass joints, INHC H04 drilling and kitchen handle placement."""
from pathlib import Path
import yaml

from parts.drawer import Board, Hole, _resolve_handle


def hinge_spec(config):
    with (Path(__file__).parents[1] / 'db/hinges.yaml').open() as stream:
        library = yaml.safe_load(stream)['hinges']
    model = config.get('model', 'GTV-ZM-INHC09H04-BE')
    if model not in library:
        raise ValueError(f'Unknown hinge: {model}')
    return library[model]


def _check_hinge(door, overlay, spec):
    lo, hi = spec['front_thickness_range']
    if not lo <= door.depth <= hi:
        raise ValueError(f'{door.name}: selected hinge requires front thickness {lo}–{hi} mm')
    if abs(overlay - spec['nominal_overlay']) > spec['overlay_adjustment']:
        raise ValueError(f'{door.name}: overlay exceeds adjustment of the selected hinge')


def hinge_positions(height):
    count = 2 if height <= 900 else 3 if height <= 1600 else 4 if height <= 2000 else 5
    if height < 250:
        raise ValueError('Door too short for the configured hinge end distances')
    return tuple(round((100 + i * (height - 200) / (count - 1)) * 2) / 2
                 for i in range(count))


def add_side_hinges(door, side, carcass, spec):
    # Catalogue H0: K=3 -> overlay 16, centre K+17.5=20.5.
    sign = 1 if side == 'left' else -1
    overlay = (carcass.pos[0] + carcass.width - door.pos[0] if sign == 1
               else door.pos[0] + door.width - carcass.pos[0])
    _check_hinge(door, overlay, spec)
    cup_edge = spec['cup_edge_distance'] + spec['cup_diameter'] / 2
    cup_x = door.pos[0] + (cup_edge if sign == 1 else door.width - cup_edge)
    plate_x = carcass.pos[0] + (carcass.width if sign == 1 else 0)
    for local_z in hinge_positions(door.height):
        z = door.pos[2] + local_z
        door.holes.append(Hole(cup_x, door.pos[1] + door.depth, z,
                               spec['cup_diameter'], spec['cup_depth'], '+y', 'hinge_cup'))
        for sign_z in (-1, 1):
            door.holes.append(Hole(cup_x - sign * spec['cup_screw_offset'], door.pos[1] + door.depth,
                z + sign_z * spec['cup_screw_spacing'] / 2, spec['pilot_diameter'],
                spec['pilot_depth'], '+y', 'hinge_screw'))
            carcass.holes.append(Hole(plate_x, carcass.pos[1] + spec['plate_setback'],
                z + sign_z * spec['plate_screw_spacing'] / 2,
                spec['pilot_diameter'], spec['pilot_depth'], '+x' if sign == 1 else '-x', 'hinge_plate'))


def add_lift_hinges(door, top, spec):
    # K=3 / NF=16; adjust overlay by -1 mm for the 3 mm top reveal (NF=15).
    # Rotate the same drilling template through 90 degrees onto the TOP panel.
    _check_hinge(door, door.pos[2] + door.height - top.pos[2], spec)
    z = door.pos[2] + door.height - spec['cup_edge_distance'] - spec['cup_diameter'] / 2
    for x in (door.pos[0] + 100, door.pos[0] + door.width - 100):
        door.holes.append(Hole(x, door.pos[1] + door.depth, z,
                               spec['cup_diameter'], spec['cup_depth'], '+y', 'hinge_cup'))
        for sign in (-1, 1):
            door.holes.append(Hole(x + sign * spec['cup_screw_spacing'] / 2,
                door.pos[1] + door.depth, z + spec['cup_screw_offset'],
                spec['pilot_diameter'], spec['pilot_depth'], '+y', 'hinge_screw'))
            top.holes.append(Hole(x + sign * spec['plate_screw_spacing'] / 2,
                top.pos[1] + spec['plate_setback'], top.pos[2],
                spec['pilot_diameter'], spec['pilot_depth'], '-z', 'hinge_plate'))


def add_handles(boards, config):
    if not config or not config.get('enabled', True):
        return
    handle = _resolve_handle(config)
    spacing = float(handle['hole_spacing'])
    length, width, projection = (float(handle[k]) for k in ('length_mm', 'height_mm', 'projection_mm'))
    edge = float(config.get('door_edge_offset', 50))
    end = float(config.get('door_end_offset', 50))
    lift_offset = float(config.get('lift_bottom_offset', 50))
    diameter = float(handle.get('hole_diameter', 5))
    for front in list(boards):
        drawer = front.name.startswith('kitchen_drawer_') and front.name.endswith('_front')
        if not drawer and front.opening not in ('lift_up', 'hinge_left', 'hinge_right'):
            continue
        vertical = not drawer and front.opening != 'lift_up'
        if drawer:
            cx, cz = front.width / 2, front.height / 2
        elif front.opening == 'lift_up':
            cx, cz = front.width / 2, lift_offset
        else:
            cx = front.width - edge if front.opening == 'hinge_left' else edge
            # Freezer handle near the upper edge; upper doors near the bottom.
            cz = front.height - end - spacing / 2 if front.name == 'fridge_lower_door' else end + spacing / 2
        # Preserve exact centring, including quarter-mm centres of half-mm fronts.
        dx, dz = (0, spacing / 2) if vertical else (spacing / 2, 0)
        bw, bh = (width, length) if vertical else (length, width)
        if min(cx - bw / 2, cz - bh / 2) < 0 or cx + bw / 2 > front.width or cz + bh / 2 > front.height:
            raise ValueError(f'Handle does not fit {front.name}')
        for sign in (-1, 1):
            front.holes.append(Hole(front.pos[0] + cx + sign * dx,
                front.pos[1] + front.depth, front.pos[2] + cz + sign * dz,
                diameter, front.depth, '+y', 'handle', True))
        if not handle.get('preview', True):
            continue
        colour = (.08, .08, .08, 1)
        if handle.get('preview_mesh'):
            boards.append(Board(f'{front.name}_handle_bar', bw, bh, projection,
                (front.pos[0] + cx - bw / 2, front.pos[1] - projection,
                 front.pos[2] + cz - bh / 2), colour, fabrication=False,
                motion_parent=front.name, travel=front.travel, label=handle['name'],
                preview_mesh=handle['preview_mesh'],
                preview_shape='mesh_vertical' if vertical else 'mesh_horizontal'))
            continue
        def part(name, w, h, d, x, y, z):
            boards.append(Board(f'{front.name}_handle_{name}', w, h, d, (x, y, z), colour,
                fabrication=False, motion_parent=front.name, travel=front.travel,
                label=handle['name']))
        x, z = front.pos[0] + cx, front.pos[2] + cz
        part('bar', bw, bh, 3, x - bw / 2, front.pos[1] - projection, z - bh / 2)
        for i, sign in enumerate((-1, 1)):
            mw, mh = (width, 8) if vertical else (8, width)
            part(f'mount_{i}', mw, mh, projection - 3,
                 x + sign * dx - mw / 2, front.pos[1] - projection + 3,
                 z + sign * dz - mh / 2)
