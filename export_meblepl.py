#!/usr/bin/env python3
"""Export a furniture YAML model to a Meble.pl cut-list CSV and drilling sheet."""

import argparse
import csv
import re
from pathlib import Path

import yaml

from parts.drawer import Board, DrawerModel, Hole, JointHole, load_drawer
from parts.desk_drawer_wall import load_desk_drawer_wall
from parts.kitchen_tall_unit import load_kitchen_tall_unit
from parts.kitchen_ventilation import (routable_guide_rectangles,
                                       guide_marker_points)
from parts.dresser import load_dresser


MEBLEPL_HEADER = [
    'Nazwa (nie wpływa na rozkrój)',
    'Szerokość',
    'Oklejanie szerokości',
    'Wysokość',
    'Oklejanie wysokość',
    'Grubość płyty',
    'Ilość sztuk',
    'Słoje [0 = bez znaczenia / 1 = po drugim wymiarze (po wysokości) /  2 lub puste = po pierwszym wymiarze (po szerokości) ]',
]


class IncompleteMachiningError(ValueError):
    """Preview is available, but this model is not ready for manufacturing."""


def _require_complete_machining(model: DrawerModel) -> None:
    if model.machining_issues:
        details = '\n'.join(f'- {issue["reason"]} Elementy: {", ".join(issue["boards"])}'
                            for issue in model.machining_issues)
        raise IncompleteMachiningError('Eksport produkcyjny zablokowany: niekompletna obróbka.\n'
                                       + details + '\nPodgląd modelu pozostaje dostępny.')


def _load_model(path: Path) -> DrawerModel:
    with path.open() as source:
        config = yaml.safe_load(source)
    if 'desk_drawer_wall' in config:
        return load_desk_drawer_wall(str(path))
    if 'kitchen_tall_unit' in config:
        return load_kitchen_tall_unit(str(path))
    return load_dresser(str(path)) if 'carcass' in config else load_drawer(str(path))


def _is_slide_visualisation(board: Board) -> bool:
    """Slides are purchased hardware, not board parts to send for cutting."""
    return 'slide_' in board.name or not board.fabrication


def _cut_dimensions(board: Board) -> tuple[float, float, float]:
    """Return the two face dimensions and thickness for a rectangular board."""
    dimensions = sorted((board.width, board.height, board.depth))
    thickness = dimensions[0]
    width, height = dimensions[2], dimensions[1]
    return width, height, thickness


def _number(value: float) -> str:
    """Write integer millimetres without a redundant decimal separator."""
    return str(int(value)) if value == int(value) else f'{value:.2f}'.rstrip('0').rstrip('.')


def write_meblepl_csv(model: DrawerModel, path: Path) -> None:
    """Write a semicolon-delimited CSV accepted by Meble.pl's PRO100 importer."""
    _require_complete_machining(model)
    boards = [board for board in model.boards if not _is_slide_visualisation(board)]
    with path.open('w', encoding='utf-8', newline='') as output:
        writer = csv.writer(output, delimiter=';', lineterminator='\r\n')
        writer.writerow(MEBLEPL_HEADER)
        for board in boards:
            width, height, thickness = _cut_dimensions(board)
            writer.writerow([
                board.name,
                _number(width),
                '-',  # edging is intentionally unset: choose it in Meble.pl
                _number(height),
                '-',
                _number(thickness),
                '1',
                '0',  # no grain direction was specified in the YAML
            ])


def _plane_coordinates(board: Board, hole: Hole | JointHole) -> tuple[str, float, float]:
    """Express a hole in the local plane that is drilled, starting at its min edges."""
    if hole.direction.endswith('x'):
        return 'Y–Z', hole.y - board.pos[1], hole.z - board.pos[2]
    if hole.direction.endswith('y'):
        return 'X–Z', hole.x - board.pos[0], hole.z - board.pos[2]
    return 'X–Y', hole.x - board.pos[0], hole.y - board.pos[1]


def _joint_spec(hole: JointHole) -> str:
    if hole.hole_type == 'dowel':
        depth = 11 if hole.element == 1 else 27
        return f'kołek Ø8, głębokość {depth} mm'
    if hole.element == 1:
        return 'konfirmat: otwór Ø5 przelotowy + pogłębienie Ø11 × 4,5 mm'
    return 'konfirmat: otwór gwintowany Ø5, głębokość min. 35 mm'


def _drilling_rows(board: Board) -> list[tuple[str, str, str, str, str, str]]:
    rows = []
    for hole in board.holes:
        if hole.kind == 'monitor_trial':
            continue
        plane, first, second = _plane_coordinates(board, hole)
        rows.append((
            {'handle': 'uchwyt', 'wood_screw': 'wkręt dna',
             'wood_screw_pilot': 'pilotaż wkrętu dna',
             'led_wire_entry': 'nawiert startowy przewodu LED',
             'hinge_cup': 'puszka zawiasu',
             'hinge_screw': 'wkręt puszki zawiasu',
             'hinge_plate': 'prowadnik zawiasu',
             'axis_runner': 'AXIS PRO — mocowanie prowadnicy',
             'axis_front': 'AXIS PRO — mocowanie frontu',
             'axis_rear': 'AXIS PRO — mocowanie tyłu',
             'column_tie_through': 'łączenie kolumn — otwór przelotowy',
             'kitchen_leg_mount': 'mocowanie nóżki kuchennej',
             'ventilation_cut_marker': 'znacznik ręcznego wycięcia wentylacji',
             'manual_cutout_marker': 'znacznik ręcznego wycięcia za mikrofalą',
             'gas_lift_mount': 'mocowanie podnośnika'}.get(hole.kind, 'prowadnica'),
            plane, _number(first), _number(second), hole.direction,
            f'Ø{_number(hole.diameter)}, ' + ('na wylot' if hole.through else f'głębokość {_number(hole.depth)} mm'),
        ))
    for hole in board.joint_holes:
        plane, first, second = _plane_coordinates(board, hole)
        rows.append((
            f'{hole.hole_type} → {hole.partner}', plane, _number(first), _number(second),
            hole.direction, _joint_spec(hole),
        ))
    return rows


def write_drilling_sheet(model: DrawerModel, path: Path, source_name: str) -> None:
    """Write one fabrication section per board, with local coordinates for each hole."""
    _require_complete_machining(model)
    boards = [board for board in model.boards if not _is_slide_visualisation(board)]
    lines = [
        f'# Wiercenia — {source_name}',
        '',
        'Wymiary i współrzędne są w milimetrach. Współrzędne otworu są podane '
        'od dwóch minimalnych krawędzi wskazanej płaszczyzny elementu. Kierunek '
        'określa normalną powierzchni, od której rozpoczyna się wiercenie.',
        '',
        f'Prowadnice: **{model.slide_model}**, NL = **{model.slide_nl} mm**.',
        '',
    ]
    for note in model.notes:
        lines += [note, '']
    for board in boards:
        width, height, thickness = _cut_dimensions(board)
        lines += [
            f'## {board.name}',
            '',
            f'Formatka: **{_number(width)} × {_number(height)} × {_number(thickness)} mm** '
            '(szerokość × wysokość × grubość).',
            '',
        ]
        if board.name.endswith('_back') and board.color[:3] == (0.95, 0.95, 0.95):
            lines += ['Materiał: HDF biały, grubość ' + _number(thickness) + ' mm.', '']
        if board.name.endswith('bottom') and thickness == 3:
            lines += ['Materiał: HDF, grubość 3 mm; dno szuflady.', '']
        for groove in board.grooves:
            if 'wire_entry' in groove:
                entry = groove['wire_entry']
                lines += [f"Przewód LED: nawiert startowy Ø4 × 35 mm, krawędź {entry['edge']}, "
                          f"oś w połowie grubości płyty ({_number(entry['axis'])} mm). "
                          f"Odległość w płaszczyźnie do frezu: {_number(entry['distance'])} mm. "
                          f"Między otworem a dnem frezu pozostaje {_number(entry['bridge'])} mm materiału; "
                          "przy dodatniej wartości konieczne dodatkowe połączenie od dna frezu. "
                          "DXF zawiera tylko nawiert 35 mm, bez późniejszego pogłębiania i połączenia.", '']
            if groove['kind'] == 'drawer_bottom':
                lines += [f"Frez pod dno HDF: {groove['span_x']} × {groove['span_z']} mm, "
                          f"głębokość {groove['depth']} mm; tylna powierzchnia +Y, "
                          f"lokalne X={_number(groove['x'])}, Z={_number(groove['z'])} mm.", '']
            if groove['kind'] == 'back_rabbet':
                lines += [f"Wręg pod plecy: szerokość {groove['width']} mm, głębokość {groove['depth']} mm; "
                          f"tylna powierzchnia +Y, lokalne X={_number(groove['x'])}, Z={_number(groove['z'])} mm; "
                          f"obszar {_number(groove['span_x'])} × {_number(groove['span_z'])} mm (X × Z).", '']
            if groove['kind'] == 'led_wire':
                lines += [f"Rowek przewodu LED: {_number(groove['width'])} × {_number(groove['depth'])} mm, "
                          f"na płaszczyźnie {groove['face']}; od tyłu do frezu LED. "
                          f"Lokalne X={_number(groove['x'])}, Y={_number(groove['y'])} mm; "
                          f"obszar {_number(groove['span_x'])} × {_number(groove['span_y'])} mm (X × Y).", '']
            if groove['kind'] == 'led':
                lines += [
                    f"Wręg LED: {groove['width']} × {groove['depth']} mm, "
                    f"od krawędzi {groove['edge']} {groove['offset']} mm, "
                    f"na płaszczyźnie {groove['face']}.",
                    f"Zakres lokalnego X: {_number(groove.get('x', 0))}–"
                    f"{_number(groove.get('x', 0)+groove.get('span_x', board.width))} mm.",
                    '',
                ]
            if groove['kind'] == 'ventilation_grille':
                lines += [f"Wycięcie kratki wentylacyjnej: {_number(groove['width'])} × "
                          f"{_number(groove['height'])} mm, lokalne X={_number(groove['x'])}, "
                          f"Z={_number(groove['z'])} mm, przez całą grubość płyty.", '']
            if groove['kind'] == 'ventilation_cut_guide':
                second = 'Z' if groove['face'] == '-y' else 'Y'
                value = groove['z'] if groove['face'] == '-y' else groove['y']
                routed = routable_guide_rectangles(board, groove)
                markers = guide_marker_points(board, groove)
                lines += [f"Obrys otworu wentylacyjnego {_number(groove['width'])} × "
                          f"{_number(groove['height'])} mm na płaszczyźnie {groove['face']}: "
                          f"lokalne X={_number(groove['x'])}, {second}={_number(value)} mm; "
                          f"{len(routed)} wręgi {_number(groove['groove_width'])} × "
                          f"{_number(groove['depth'])} mm w zasięgu "
                          f"{_number(groove['max_edge_offset'])} mm od krawędzi; "
                          f"{len(markers)} znaczników Ø{_number(groove['marker_diameter'])} × "
                          f"{_number(groove['marker_depth'])} mm na pozostałych odcinkach "
                          f"(około {_number(groove['marker_spacing'])} mm, po "
                          f"{_number(groove['marker_end_offset'])} mm od końców). "
                          "Płyta pozostaje pełna; materiał wewnątrz obrysu wyciąć osobno po rozkroju.", '']
            if groove['kind'] == 'manual_cutout_guide':
                lines += [f"Obrys ręcznego wycięcia za mikrofalą: "
                          f"{_number(groove['span_z'])} mm wysokości × "
                          f"{_number(groove['span_y'])} mm wzdłuż głębokości boku, "
                          f"od wewnętrznej strony {groove['face']}, lokalne Y={_number(groove['y'])}, "
                          f"Z={_number(groove['z'])} mm. Nawierty Ø{_number(groove['marker_diameter'])} "
                          f"× {_number(groove['marker_depth'])} mm, po maksymalnie "
                          f"{groove['marker_count_per_edge']} na odcinek, pierwszy i ostatni "
                          f"{_number(groove['marker_end_offset'])} mm od jego końców. "
                          + ("Bez nawiertów na tylnej krawędzi płyty. "
                             if not groove['rear_edge_marked'] else "") +
                          "Formatka pozostaje pełna; materiał wewnątrz obrysu wyciąć ręcznie.", '']
        rows = _drilling_rows(board)
        if not rows:
            lines += ['Brak wierceń.', '']
            continue
        lines += [
            '| Typ / połączenie | Płaszczyzna | Poz. 1 | Poz. 2 | Kierunek | Wiercenie |',
            '| --- | --- | ---: | ---: | --- | --- |',
        ]
        lines += [f'| {kind} | {plane} | {first} | {second} | {direction} | {spec} |'
                  for kind, plane, first, second, direction, spec in rows]
        lines.append('')
    path.write_text('\n'.join(lines), encoding='utf-8')


def _dxf_number(value: float) -> str:
    return f'{value:.4f}'.rstrip('0').rstrip('.') or '0'


def _dxf_pair(code: int, value: str | float | int) -> list[str]:
    return [str(code), str(value)]


def _dxf_line(layer: str, x1: float, y1: float, x2: float, y2: float) -> list[str]:
    return ['0', 'LINE', '8', layer, '10', _dxf_number(x1), '20', _dxf_number(y1), '30', '0',
            '11', _dxf_number(x2), '21', _dxf_number(y2), '31', '0']


def _dxf_circle(layer: str, x: float, y: float, diameter: float) -> list[str]:
    return ['0', 'CIRCLE', '8', layer, '10', _dxf_number(x), '20', _dxf_number(y), '30', '0',
            '40', _dxf_number(diameter / 2)]


def _dxf_arc(layer: str, x: float, y: float, radius: float, start: float, end: float) -> list[str]:
    return ['0', 'ARC', '8', layer, '10', _dxf_number(x), '20', _dxf_number(y), '30', '0',
            '40', _dxf_number(radius), '50', _dxf_number(start), '51', _dxf_number(end)]


def _dxf_text(text: str, x: float, y: float, height: float = 5) -> list[str]:
    return ['0', 'TEXT', '8', 'NOTES', '10', _dxf_number(x), '20', _dxf_number(y), '30', '0',
            '40', _dxf_number(height), '1', text]


def _face_dimensions(board: Board, direction: str) -> tuple[float, float]:
    if direction.endswith('x'):
        return board.depth, board.height
    if direction.endswith('y'):
        return board.width, board.height
    return board.width, board.depth


def _dxf_drills(hole: Hole | JointHole) -> list[tuple[float, str]]:
    if isinstance(hole, Hole):
        prefix = 'HANDLE' if hole.kind == 'handle' else 'DRILL'
        if hole.kind == 'led_wire_entry':
            prefix = 'LED_WIRE_START'
        elif hole.kind == 'hinge_cup':
            prefix = 'HINGE_CUP'
        elif hole.kind == 'hinge_plate':
            prefix = 'HINGE_PLATE'
        elif hole.kind in ('hinge_screw', 'axis_runner', 'axis_front', 'axis_rear'):
            prefix = hole.kind.upper()
        elif hole.kind == 'gas_lift_mount':
            prefix = 'GAS_LIFT_MOUNT'
        elif hole.kind == 'column_tie_through':
            prefix = hole.kind.upper()
        elif hole.kind == 'kitchen_leg_mount':
            prefix = 'KITCHEN_LEG_MOUNT'
        elif hole.kind == 'ventilation_cut_marker':
            prefix = 'VENT_CUT_MARKER'
        elif hole.kind == 'manual_cutout_marker':
            prefix = 'MANUAL_CUT_MARKER'
        depth = 'THRU' if hole.through else f'DEPTH{_number(hole.depth)}'
        return [(hole.diameter, f'{prefix}_D{_number(hole.diameter)}_{depth}')]
    if hole.hole_type == 'dowel':
        depth = 11 if hole.element == 1 else 27
        return [(8, f'DRILL_D8_DEPTH{depth}')]
    if hole.element == 1:
        return [(5, 'DRILL_D5_THRU'), (11, 'COUNTERSINK_D11_DEPTH4.5')]
    return [(5, 'DRILL_D5_DEPTH35')]


def _dxf_file(board: Board, direction: str, holes: list[Hole | JointHole], grooves: list[dict], path: Path) -> None:
    """Write one R12 DXF for a single drilled face of a board."""
    face_width, face_height = _face_dimensions(board, direction)
    layers = {'OUTLINE', 'NOTES'}
    entities: list[str] = []
    if direction.endswith('z') and board.corner_radius > 0 and any(board.rounded_front_corners):
        radius = min(board.corner_radius, face_width / 2, face_height)
        left, right = board.rounded_front_corners
        if left:
            entities += _dxf_line('OUTLINE', 0, face_height, 0, radius)
            entities += _dxf_arc('OUTLINE', radius, radius, radius, 180, 270)
        else:
            entities += _dxf_line('OUTLINE', 0, face_height, 0, 0)
        if right:
            entities += _dxf_line('OUTLINE', radius if left else 0, 0, face_width - radius, 0)
            entities += _dxf_arc('OUTLINE', face_width - radius, radius, radius, 270, 360)
            entities += _dxf_line('OUTLINE', face_width, radius, face_width, face_height)
        else:
            entities += _dxf_line('OUTLINE', radius if left else 0, 0, face_width, 0)
            entities += _dxf_line('OUTLINE', face_width, 0, face_width, face_height)
        entities += _dxf_line('OUTLINE', face_width, face_height, 0, face_height)
    else:
        entities += _dxf_line('OUTLINE', 0, 0, face_width, 0)
        entities += _dxf_line('OUTLINE', face_width, 0, face_width, face_height)
        entities += _dxf_line('OUTLINE', face_width, face_height, 0, face_height)
        entities += _dxf_line('OUTLINE', 0, face_height, 0, 0)

    drill_labels = []
    for hole in holes:
        _, first, second = _plane_coordinates(board, hole)
        for diameter, layer in _dxf_drills(hole):
            layers.add(layer)
            entities += _dxf_circle(layer, first, second, diameter)
            drill_labels.append(layer.replace('_', ' '))

    for groove in grooves:
        if groove.get('kind') == 'manual_cutout_guide' and direction == groove['face']:
            layer = 'MANUAL_CUT_GUIDE_NOT_TOOLPATH'
            layers.add(layer)
            y1, z1 = groove['y'], groove['z']
            y2, z2 = y1 + groove['span_y'], z1 + groove['span_z']
            entities += _dxf_line(layer, y1, z1, y2, z1)
            entities += _dxf_line(layer, y2, z1, y2, z2)
            entities += _dxf_line(layer, y2, z2, y1, z2)
            entities += _dxf_line(layer, y1, z2, y1, z1)
            drill_labels.append('MANUAL CUT AFTER DELIVERY')
            continue
        if groove.get('kind') == 'ventilation_cut_guide' and direction == groove['face']:
            layer = (f"GROOVE_VENT_GUIDE_W{_number(float(groove['groove_width']))}"
                     f"_D{_number(float(groove['depth']))}")
            layers.add(layer)
            for x1, y1, x2, y2 in routable_guide_rectangles(board, groove):
                entities += _dxf_line(layer, x1, y1, x2, y1)
                entities += _dxf_line(layer, x2, y1, x2, y2)
                entities += _dxf_line(layer, x2, y2, x1, y2)
                entities += _dxf_line(layer, x1, y2, x1, y1)
            drill_labels.append(layer.replace('_', ' '))
            continue
        if groove.get('kind') == 'ventilation_grille' and direction == '-y':
            x1, z1 = float(groove['x']), float(groove['z'])
            x2, z2 = x1 + float(groove['span_x']), z1 + float(groove['span_z'])
            layer = f"CUTOUT_VENT_W{_number(float(groove['width']))}_H{_number(float(groove['height']))}"
            layers.add(layer)
            entities += _dxf_line(layer, x1, z1, x2, z1)
            entities += _dxf_line(layer, x2, z1, x2, z2)
            entities += _dxf_line(layer, x2, z2, x1, z2)
            entities += _dxf_line(layer, x1, z2, x1, z1)
            drill_labels.append(layer.replace('_', ' '))
            continue
        if groove.get('kind') in ('back_rabbet', 'drawer_bottom') and direction == '+y':
            width = float(groove['width'])
            x1, z1 = groove['x'], groove['z']
            x2, z2 = x1 + groove['span_x'], z1 + groove['span_z']
            layer = f"RABBET_BACK_W{_number(width)}_D{_number(float(groove['depth']))}"
            if groove['kind'] == 'drawer_bottom':
                layer = f"GROOVE_BOTTOM_W{_number(width)}_D{_number(float(groove['depth']))}"
            layers.add(layer)
            entities += _dxf_line(layer, x1, z1, x2, z1)
            entities += _dxf_line(layer, x2, z1, x2, z2)
            entities += _dxf_line(layer, x2, z2, x1, z2)
            entities += _dxf_line(layer, x1, z2, x1, z1)
            drill_labels.append(layer.replace('_', ' '))
            continue
        if groove.get('kind') not in ('led', 'led_wire') or not direction.endswith('z'):
            continue
        groove_width = float(groove['width'])
        offset = float(groove.get('offset', 0))
        y1 = max(0, offset - groove_width / 2)
        y2 = min(face_height, offset + groove_width / 2)
        x1 = float(groove.get('x', 0))
        x2 = x1 + float(groove.get('span_x', face_width))
        layer = f"GROOVE_LED_W{_number(groove_width)}_D{_number(float(groove['depth']))}"
        if groove['kind'] == 'led_wire':
            y1 = groove['y']
            y2 = y1 + groove['span_y']
            layer = f"GROOVE_LED_WIRE_W{_number(groove_width)}_D{_number(float(groove['depth']))}"
        layers.add(layer)
        entities += _dxf_line(layer, x1, y1, x2, y1)
        entities += _dxf_line(layer, x2, y1, x2, y2)
        entities += _dxf_line(layer, x2, y2, x1, y2)
        entities += _dxf_line(layer, x1, y2, x1, y1)
        drill_labels.append(layer.replace('_', ' '))

    entities += _dxf_text(board.name, 0, face_height + 12)
    plane = {'x': 'Y-Z', 'y': 'X-Z', 'z': 'X-Y'}[direction[-1]]
    entities += _dxf_text(f'Drill from {direction}; plane {plane}',
                          0, face_height + 5)
    entities += _dxf_text('; '.join(sorted(set(drill_labels))), 0, -8)

    content = ['0', 'SECTION', '2', 'HEADER', '0', 'ENDSEC', '0', 'SECTION', '2', 'TABLES',
               '0', 'TABLE', '2', 'LAYER', '70', str(len(layers))]
    for layer in sorted(layers):
        content += ['0', 'LAYER', '2', layer, '70', '0', '62', '7', '6', 'CONTINUOUS']
    content += ['0', 'ENDTAB', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
    content += entities
    content += ['0', 'ENDSEC', '0', 'EOF']
    path.write_text('\n'.join(content) + '\n', encoding='ascii')


def write_dxf_files(model: DrawerModel, output_dir: Path) -> list[Path]:
    """Write a DXF for every board face that contains drillings."""
    _require_complete_machining(model)
    paths = []
    boards = [board for board in model.boards if not _is_slide_visualisation(board)]
    for index, board in enumerate(boards, start=1):
        by_direction: dict[str, list[Hole | JointHole]] = {}
        for hole in [*board.holes, *board.joint_holes]:
            if isinstance(hole, Hole) and hole.kind == 'monitor_trial':
                continue
            by_direction.setdefault(hole.direction, []).append(hole)
        grooves_by_direction: dict[str, list[dict]] = {}
        for groove in board.grooves:
            grooves_by_direction.setdefault(groove['face'], []).append(groove)
        safe_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', board.name)
        for direction in sorted(set(by_direction) | set(grooves_by_direction)):
            holes = by_direction.get(direction, [])
            grooves = grooves_by_direction.get(direction, [])
            safe_direction = direction.replace('+', 'plus-').replace('-', 'minus-')
            dxf_path = output_dir / f'{index:02d}-{safe_name}--{safe_direction}.dxf'
            _dxf_file(board, direction, holes, grooves, dxf_path)
            paths.append(dxf_path)
    return paths


def export(path: Path, output_dir: Path) -> tuple[Path, Path, Path]:
    model = _load_model(path)
    _require_complete_machining(model)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = path.stem
    csv_path = output_dir / f'{stem}-meblepl.csv'
    drilling_path = output_dir / f'{stem}-wiercenia.md'
    dxf_dir = output_dir / f'{stem}-dxf'
    dxf_dir.mkdir(exist_ok=True)
    write_meblepl_csv(model, csv_path)
    write_drilling_sheet(model, drilling_path, path.name)
    write_dxf_files(model, dxf_dir)
    return csv_path, drilling_path, dxf_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('yaml_path', type=Path, help='model YAML')
    parser.add_argument('--output-dir', type=Path, default=Path('exports'),
                        help='directory for generated files (default: exports)')
    args = parser.parse_args()
    try:
        csv_path, drilling_path, dxf_dir = export(args.yaml_path, args.output_dir)
    except ValueError as exc:
        parser.exit(2, str(exc) + '\n')
    print(f'CSV do importu Meble.pl: {csv_path}')
    print(f'Dokumentacja wierceń: {drilling_path}')
    print(f'Pliki DXF wierceń: {dxf_dir}')


if __name__ == '__main__':
    main()
