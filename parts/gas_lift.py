"""GTV gas-lift mounting template and schematic moving preview geometry."""

import math
from pathlib import Path

import yaml

from parts.drawer import GasLiftPreview, Hole


LIFT_OPEN_FRONT_CLEARANCE = 2.0
LIFT_CLOSED_TOP_REVEAL = 2.0


def lift_flap_point(door, offset, amount):
    """Transform a door-local anchor exactly as the viewer transforms the flap."""
    x, y, z = offset
    angle = math.radians(-door.opening_angle * amount)
    dy, dz = y - door.depth, z - door.height
    return (
        door.pos[0] + x,
        door.pos[1] - LIFT_OPEN_FRONT_CLEARANCE * amount + door.depth
        + math.cos(angle) * dy - math.sin(angle) * dz,
        door.pos[2] - (door.depth - LIFT_CLOSED_TOP_REVEAL) * amount
        + door.height + math.sin(angle) * dy + math.cos(angle) * dz,
    )


def gas_lift_anchors(lift, boards, amount):
    """Return the fixed carcass and moving door joint centres in model space."""
    side = boards[lift.side_board]
    fixed = tuple(side.pos[i] + lift.side_anchor[i] for i in range(3))
    moving = lift_flap_point(boards[lift.door_board], lift.door_anchor, amount)
    return fixed, moving


def add_gas_lifts(door, left_side, right_side, top, config):
    """Drill the GTV template in both sides and the flap; return preview lifts."""
    if not config.get('enabled', True):
        return []
    with (Path(__file__).parents[1] / 'db/gas_lifts.yaml').open() as stream:
        library = yaml.safe_load(stream)['gas_lifts']
    model = config.get('model', 'GTV-PD-GNEO12-80-60')
    if model not in library:
        raise ValueError(f'Unknown gas lift model: {model}')
    spec = library[model]
    layout = spec['mounting_options'].get(door.opening_angle)
    if layout is None:
        raise ValueError(f'{model}: no mounting template for {door.opening_angle:g}°')
    if door.opening != 'lift_up' or top.pos[2] - door.pos[2] < layout['w']:
        raise ValueError(f'{model}: lift requires a suitable upper cabinet')
    if spec['pilot_depth'] >= min(door.depth, left_side.width, right_side.width):
        raise ValueError(f'{model}: pilot drilling exceeds panel thickness')
    top_underside = top.pos[2]
    # GTV p.2: L ends at the UPPER fixing screw, not the ball centre.
    front_z = top_underside - layout['l'] - spec['fixing_spacing'] / 2
    upper_side_z = top_underside - layout['h']
    result = []
    for side, sign in ((left_side, 1), (right_side, -1)):
        inner_x = side.pos[0] + (side.width if sign == 1 else 0)
        side_y = side.pos[1] + spec['side_front_setback']
        centre_x = inner_x + sign * layout['c']
        for z in (upper_side_z, upper_side_z - spec['fixing_spacing']):
            side.holes.append(Hole(inner_x, side_y, z,
                                   spec['pilot_diameter'], spec['pilot_depth'],
                                   '+x' if sign == 1 else '-x', 'gas_lift_mount'))
        # The front plate follows the YZ plane of the strut. On the closed
        # vertical door its two screw holes form a vertical line, not a row
        # across the door width.
        for z in (front_z - spec['fixing_spacing'] / 2,
                  front_z + spec['fixing_spacing'] / 2):
            door.holes.append(Hole(centre_x, door.pos[1] + door.depth, z,
                                   spec['pilot_diameter'], spec['pilot_depth'],
                                   '+y', 'gas_lift_mount'))
        # Ball-joint centres are schematic; the two screw patterns above are
        # dimensioned by GTV. The lift extends between these moving centres.
        result.append(GasLiftPreview(
            model=model, side_board=side.name, door_board=door.name,
            side_anchor=(inner_x + sign * spec['side_projection'] - side.pos[0],
                         side_y - side.pos[1],
                         upper_side_z - spec['fixing_spacing'] / 2 - side.pos[2]),
            door_anchor=(centre_x - door.pos[0], door.depth + spec['front_projection'],
                         front_z - door.pos[2]),
            fixing_spacing=spec['fixing_spacing'], plate_length=spec['plate_length'],
            plate_width=spec['plate_width'],
            side_projection=spec['side_projection'],
            front_projection=spec['front_projection'],
            barrel_diameter=spec['barrel_diameter'], rod_diameter=spec['rod_diameter'],
            barrel_length=spec['barrel_length'], socket_length=spec['socket_length'],
        ))
    return result
