"""Explicit draft for the supplier UI. No manufacturing export gate is bypassed."""
from pathlib import Path
import json
import math
import yaml
from parts.precision import mm
from export import _load_model, _is_slide_visualisation
from parts.materials import panel_axes, FACE_AXES, material_selections, grain_code

FACE_DIAMETERS = {3, 5, 8, 10, 15, 20, 35}
EDGE_DIAMETERS = {4, 8}


def material_config(root):
    return {**root.get('material', {}), **root.get('kitchen_tall_unit', {}).get('material', {})}


def face_surface(normal_axis, direction, u, v):
    # A is the visible face when supplier X points right and Y points up.
    sign = 1 if (u, v, normal_axis) in ((0, 1, 2), (1, 2, 0), (2, 0, 1)) else -1
    return 'A' if sign == (1 if direction.startswith('+') else -1) else 'B'


def drill(board, hole, diameter, depth, through=False):
    sizes = tuple(mm(v) for v in (board.width, board.depth, board.height))
    u, v, normal = panel_axes(board)
    axis = 'xyz'.index(hole.direction[-1])
    local = tuple(mm(a-b) for a, b in zip((hole.x, hole.y, hole.z), board.pos))
    if not all(math.isfinite(x) for x in (*local, diameter, depth)):
        return None, 'Niefinitywne wymiary nawiertu'
    if axis == normal:
        if diameter not in FACE_DIAMETERS or (not through and depth not in range(2, 16)):
            return None, 'Średnica/głębokość niedostępna dla wiercenia w płaszczyźnie'
        x, y = local[u], local[v]
        if not (diameter/2 <= x <= sizes[u]-diameter/2 and diameter/2 <= y <= sizes[v]-diameter/2):
            return None, 'Otwór przecina krawędź formatki'
        return dict(kind='face', powierzchnia=face_surface(normal, hole.direction, u, v),
                    wsp_x=x, wsp_y=y, srednica=diameter,
                    glebokosc='przelot' if through else depth), None
    if diameter not in EDGE_DIAMETERS or through or depth not in range(2, 36):
        return None, 'Średnica/głębokość niedostępna dla wiercenia w czole'
    if abs(local[normal]-sizes[normal]/2) > 1e-5:
        return None, 'Wiercenie w czole poza osią grubości płyty'
    edge = ('right' if hole.direction[0]=='+' else 'left') if axis == u else (
        'top' if hole.direction[0]=='+' else 'bottom')
    distance = local[v if axis == u else u]
    if not diameter/2 <= distance <= sizes[v if axis == u else u]-diameter/2:
        return None, 'Otwór przecina koniec krawędzi'
    return dict(kind='edge', krawedz=edge, odleglosc_x=distance,
                srednica=diameter, glebokosc=depth), None


def make_plan(source):
    source = Path(source)
    root = yaml.safe_load(source.read_text())
    model = _load_model(source)
    selections = material_selections(material_config(root))
    boards = [b for b in model.boards if not _is_slide_visualisation(b)]
    needed = sorted({min(b.width,b.depth,b.height) for b in boards})
    missing = [t for t in needed if t not in selections]
    if missing:
        raise ValueError('Brak wyboru płyty dla grubości: ' + ', '.join(f'{t:g} mm' for t in missing) +
                         '. Uzupełnij material.boards_by_thickness w YAML; dekor nie jest zgadywany.')
    for t in needed:
        selected = selections[t]
        supplier = selected.get('meble_pl', {})
        if not supplier.get('decor') or not supplier.get('structure'):
            raise ValueError(f'Płyta {t:g} mm: wymagane meble_pl.decor i meble_pl.structure')
    # Reports must not expose local usernames or parent directory names.
    try:
        source_label = source.resolve().relative_to(Path(__file__).resolve().parents[1]).as_posix()
    except ValueError:
        source_label = source.name
    plan = dict(source=source_label, status='draft', groups=[],
                unresolved=model.machining_issues, manual=[], notes=model.notes,
                manual_finishing=list(model.assembly_operations))
    groups = {}
    for board in boards:
        dims = tuple(mm(v) for v in (board.width, board.depth, board.height))
        u,v,n = panel_axes(board)
        t = dims[n]
        if t not in groups:
            groups[t] = dict(thickness=t, material=selections[t], boards=[])
            plan['groups'].append(groups[t])
        edges = {}
        for face, band in board.edgebands.items():
            axis, high = FACE_AXES[face]
            edge = ('right' if high else 'left') if axis == u else ('top' if high else 'bottom')
            if band not in (0.8, 2):
                raise ValueError(f'{board.name}: nieobsługiwana grubość obrzeża {band}')
            edges[edge] = band
        if len(set(edges.values())) > 1:
            raise ValueError(f'{board.name}: różne grubości obrzeży wymagają ręcznej konfiguracji')
        item = dict(name=board.name,width=dims[u],height=dims[v],thickness=t,
                    edges=edges, drills=[], grain=grain_code(board))
        groups[t]['boards'].append(item)
        if board.corner_radius and any(board.rounded_front_corners):
            raise ValueError(f'{board.name}: skrypt obsługuje obecnie formatki prostokątne; zaokrąglenie wymaga ręcznej konfiguracji')
        # Supplier pilot holes are intentional substitutions, not hardware dimensions.
        operations = [(h,3 if h.kind == 'slide' else h.diameter,
                       3 if h.kind == 'slide' else h.depth,
                       False if h.kind == 'slide' else h.through,h.kind) for h in board.holes]
        for h in board.joint_holes:
            if h.hole_type=='dowel':
                operations.append((h,8,11 if h.element==1 else 27,False,'kołek'))
            elif h.element==1:
                operations.append((h,5,t,True,'konfirmat'))
            else:
                operations.append((h,4,35,False,'konfirmat w czole'))
        seen = set()
        for h, diameter, depth, through, label in operations:
            entry, reason = drill(board,h,diameter,depth,through)
            if entry:
                signature = json.dumps(entry,sort_keys=True)
                if signature not in seen:
                    item['drills'].append(entry);seen.add(signature)
            else:
                plan['manual'].append(dict(board=board.name,operation=label,
                    direction=h.direction,position=[mm(a-b) for a,b in zip((h.x,h.y,h.z),board.pos)],
                    diameter=diameter,depth=depth,through=through,reason=reason))
        for groove in board.grooves:
            plan['manual'].append(dict(board=board.name,operation=groove['kind'],geometry=groove,
                                      reason='Frez/wręg lub wycięcie: do ręcznego uzupełnienia; skrypt automatyzuje nawierty'))
    if any(h.hole_type != 'dowel' and h.element == 1
           for board in boards for h in board.joint_holes):
        plan['manual_finishing'].append(
            'Pogłębienia pod łby konfirmatów do wykonania samodzielnie.')
    return plan


def save_plan(plan, output):
    output = Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    lines = ['# Szkic rozkroju meble.pl', '', 'Nie jest kompletną dokumentacją produkcyjną.', '',
             '## Płyty i formatki', '']
    for group in plan['groups']:
        lines.append(f"- {group['material'].get('name',group['material']['id'])}, {group['thickness']:g} mm: {len(group['boards'])} formatek")
    lines += ['', '## Brakujące dane projektu (eksport produkcyjny nadal zablokowany)', '']
    for issue in plan['unresolved']:
        lines.append(f"- {issue['reason']} Elementy: {', '.join(issue['boards'])}.")
    if not plan['unresolved']: lines.append('Brak zgłoszonych braków danych modelu.')
    lines += ['', '## Obróbka do wykonania / uzupełnienia osobno', '']
    for operation in plan['manual']:
        lines.append('- ' + json.dumps(operation,ensure_ascii=False))
    if not plan['manual']: lines.append('Brak.')
    lines += ['', '## Uwagi do wykonania', '',
              'Otwory pod konfirmaty w krawędziach: piloty Ø4 × 35 mm; '
              'na płaszczyźnie: otwory Ø5 mm na wylot. '
              'Pogłębienia pod łby konfirmatów wykonuje użytkownik samodzielnie; '
              'nie są zlecane w rozkroju. Nawierty prowadnic: zaznaczenia Ø3 × 3 mm. '
              'Są to celowe zamienniki na potrzeby rozkroju, a nie zmiana wymiarów okuć.', '']
    if plan.get('manual_finishing'):
        lines += ['', '## Czynności do wykonania samodzielnie / podczas montażu', '']
        lines += ['- '+note for note in plan['manual_finishing']]
    lines += ['', '## Nawierty do automatycznego wprowadzenia', '']
    for group in plan['groups']:
        for b in group['boards']:
            lines += [f"### {b['name']} — {b['width']:g} × {b['height']:g} × {b['thickness']:g} mm", '',
                      'Obrzeża (układ formularza): '+json.dumps(b['edges'],ensure_ascii=False),
                      'Słoje: '+('na wysokość' if b['grain']==1 else 'na szerokość'), '']
            lines += ['- '+json.dumps(d,ensure_ascii=False) for d in b['drills']]
            lines.append('')
    (output/'raport.md').write_text('\n'.join(lines)+'\n')
    return output
