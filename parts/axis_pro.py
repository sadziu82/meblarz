"""GTV AXIS PRO soft-close, 16 mm cut parts and catalogue drilling (pp.6–8)."""
from pathlib import Path

import yaml

from parts.drawer import Board, Hole
from parts.front_rules import SIDE_REVEAL


def axis_spec(config):
    with (Path(__file__).parents[1] / 'db/drawer_systems.yaml').open() as stream:
        spec = yaml.safe_load(stream)['systems']['GTV-AXIS-PRO']
    model = config.get('model', 'GTV-AXIS-PRO')
    if model not in ('GTV-AXIS-PRO', 'GTV-AXIS-PRO-H199-L550-ANTHRACITE'):
        raise ValueError(f'Unknown drawer system: {model}')
    nl = float(config.get('nl', 550))
    if nl not in spec['runner_holes']:
        raise ValueError('Unsupported Axis Pro NL')
    if float(config.get('bottom_thickness', 16)) != 16:
        raise ValueError('Axis Pro drawer bottom must be 16 mm')
    if 'variants' in config:
        variants = list(config['variants'])
    else:
        # Legacy project heights referred to the REAR cut board, despite the key.
        old = config.get('side_heights', [config.get('side_height', 199)] * 3)
        lookup = {v['rear_height']: k for k, v in spec['variants'].items()}
        try:
            variants = [lookup[h] for h in old]
        except KeyError as exc:
            raise ValueError('Unsupported legacy Axis Pro side_heights') from exc
    if len(variants) != 3 or any(v not in spec['variants'] for v in variants):
        raise ValueError('Axis Pro requires three variants selected from A, B, C, D')
    return spec, nl, variants


def add_axis_drawer(boards, prefix, left, right, z, front_height, datum,
                    ceiling, spec, nl, variant, colour):
    """Datum is the top of the panel/rail below the drawer, not front bottom.

    The metal profile and telescoping members are simplified envelopes. Cut
    sizes and drilling use the catalogue, independently of those envelopes.
    """
    v = spec['variants'][variant]
    x = left.pos[0] + left.width
    lw = right.pos[0] - x
    if ceiling - datum < v['minimum_niche_height']:
        raise ValueError(f'{prefix}: Axis Pro {variant} needs {v["minimum_niche_height"]} mm clear height')
    if min(left.depth, right.depth) < nl + spec['minimum_depth_extra']:
        raise ValueError('Axis Pro needs carcass depth of at least NL + 10 mm')
    if lw <= spec['rear_width_deduction']:
        raise ValueError('Axis Pro drawer is too narrow')
    front = Board(f'{prefix}_front', lw + left.width + right.width - 2 * SIDE_REVEAL,
                  front_height, 18, (left.pos[0] + SIDE_REVEAL, -18, z), colour,
                  travel=nl)
    bottom = Board(f'{prefix}_bottom', lw - spec['bottom_width_deduction'], 16,
                   nl - spec['bottom_length_deduction'],
                   (x + 37.5, 0, datum + 28), colour, travel=nl)
    rear = Board(f'{prefix}_rear', lw - spec['rear_width_deduction'],
                 v['rear_height'], 16, (x + 43.5, bottom.depth, datum + 23),
                 colour, travel=nl)
    boards.extend((front, bottom, rear))
    for side, carcass, sign in (('left', left, 1), ('right', right, -1)):
        face_x = x if sign == 1 else right.pos[0]
        for y in spec['runner_holes'][nl]:
            carcass.holes.append(Hole(face_x, y, datum + spec['runner_hole_height'],
                spec['runner_pilot_diameter'], spec['runner_pilot_depth'],
                '+x' if sign == 1 else '-x', 'axis_runner'))
        for dz in v['front_holes']:
            front.holes.append(Hole(face_x + sign * spec['front_hole_inset'], 0,
                datum + dz, spec['connector_pilot_diameter'],
                spec['connector_pilot_depth'], '+y', 'axis_front'))
        rear_x = rear.pos[0] + spec['rear_hole_inset'] if sign == 1 else (
            rear.pos[0] + rear.width - spec['rear_hole_inset'])
        for dz in v['rear_holes_from_top']:
            rear.holes.append(Hole(rear_x, rear.pos[1] + rear.depth,
                rear.pos[2] + rear.height - dz, spec['connector_pilot_diameter'],
                spec['connector_pilot_depth'], '+y', 'axis_rear'))
        # 14 mm metal shell, with the lower return kept clear of the bottom.
        sx = x + 23.5 if sign == 1 else right.pos[0] - 37.5
        shell = Board(f'{prefix}_axis_pro_{side}', spec['side_thickness'],
                      v['side_height'], nl - spec['side_length_deduction'],
                      (sx, 0, datum + 23 + v['rear_height'] - v['side_height']),
                      (.18, .20, .22, 1),
                      fabrication=False, travel=nl,
                      label=f'GTV PB-AXISPRO-KPL{int(nl)}{variant}; uproszczony profil metalowy')
        boards.append(shell)
        # Fixed mounting brackets, plus middle/inner telescoping members.
        for k, fraction in enumerate((0, .5, 1)):
            rx = face_x + k * 7 if sign == 1 else face_x - (k + 1) * 7
            boards.append(Board(f'{prefix}_runner_{side}_{k}', 7, 18, nl,
                (rx, 0, datum + 4), (.38 + k * .1, .4 + k * .1, .42 + k * .1, 1),
                fabrication=False, movable=fraction > 0, move_fraction=fraction,
                travel=nl, label='AXIS PRO — uproszczony profil prowadnicy'))
        for j, y in enumerate(spec['runner_holes'][nl]):
            rx = face_x if sign == 1 else face_x - 2
            boards.append(Board(f'{prefix}_runner_mount_{side}_{j}', 2, 34, 32,
                (rx, y - 16, datum + 4), (.35, .37, .39, 1),
                fabrication=False, movable=False))
    return front
