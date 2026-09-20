"""Schematic lighting-control locations, excluded from production geometry."""
from parts.drawer import Board


def append_lighting_controls(boards, config):
    if not config.get('preview', False):
        return []
    by_name = {b.name: b for b in boards}
    markers = []
    notes = []
    drawer_cfg = config.get('drawers', {})
    if drawer_cfg.get('enabled', True):
        side = drawer_cfg.get('side', 'left')
        if side not in ('left', 'right'):
            raise ValueError('Lighting drawer control side must be left or right')
        for rear in boards:
            if not rear.name.startswith('tower_drawer_') or not rear.name.endswith('_rear'):
                continue
            prefix = rear.name.removesuffix('_rear')
            slide = by_name[f'{prefix}_slide_{side}_outer']
            # Small location marker, NOT a switch envelope or mounting bracket.
            x = rear.pos[0] + (4 if side == 'left' else rear.width-4)
            y = rear.pos[1] + rear.depth + 4
            z = slide.pos[2] + slide.height + float(drawer_cfg.get('above_slide', 5)) + 3
            markers.append(Board(f'{prefix}_switch_location', 6, 6, 6,
                                 (x-3, y-3, z-3), (1, .55, .05, 1),
                                 movable=False, fabrication=False))
            notes.append(f'Sterowanie {prefix}: krańcówka na nieruchomym korpusie/wsporniku, '
                         f'z tyłu po stronie {side}, nad prowadnicą; zamknięta = LED wyłączony, '
                         'otwarta = LED włączony. Znacznik miejsca, bez wymiarów okucia i nawiertów.')
    shelf_cfg = config.get('shelves', {})
    if shelf_cfg.get('enabled', True):
        side = shelf_cfg.get('side', 'left')
        if side not in ('left', 'right'):
            raise ValueError('Lighting shelf control side must be left or right')
        for board in boards:
            if board.name.startswith(('tower_drawer_rail_', 'tower_drawer_top')):
                continue
            for index, groove in enumerate(g for g in board.grooves if g['kind'] == 'led'):
                start, length = groove.get('x', 0), groove.get('span_x', board.width)
                inset = min(15, length/2)
                x = start + (inset if side == 'left' else length-inset)
                z = board.pos[2]-6 if groove['face'] == '-z' else board.pos[2]+board.height
                markers.append(Board(f'led_sensor_location_{board.name}_{index}', 6, 6, 6,
                                     (board.pos[0]+x-3, board.pos[1]+groove['offset']-3, z),
                                     (.1, .7, 1, 1), movable=False, fabrication=False))
                notes.append(f'Sterowanie {board.name}: orientacyjne miejsce czujnika gestu dłoni '
                             f'przy końcu LED ({side}); przełączanie włącz/wyłącz. '
                             'Bez nawiertów, model i gabaryty do ustalenia.')
    boards.extend(markers)
    if markers:
        notes.append('Sterowanie LED: podgląd pokazuje wyłącznie znaczniki lokalizacji 6 mm, '
                     'nie gabaryty urządzeń ani symulację elektryczną. Dobór modeli, mocowań, '
                     'napięcia/prądu i podłączenia do sterownika pozostaje otwarty.')
    return notes
