"""Exact rectangular groove conversion for Meble.pl's edge-referenced form.

Verified against the live form and rozkroj.js: offset is the clear distance,
X1/X2 are end margins (left/right for horizontal, top/bottom for vertical).
No implicit change of cutter width or rounding of the clear edge distance.
"""
from collections import Counter
import math
from parts.materials import panel_axes
from parts.precision import mm
from parts.kitchen_ventilation import routable_guide_rectangles

WIDTHS = (3.2, 4.2, 10.2)


def rectangles(board, groove):
    """Yield machining face, local 3D bounding box and depth for each segment."""
    kind, face = groove['kind'], groove['face']
    axis = 'xyz'.index(face[-1])
    sizes = (board.width, board.depth, board.height)
    planes = [i for i in range(3) if i != axis]
    if kind == 'ventilation_cut_guide':
        rects = routable_guide_rectangles(board, groove)
    elif kind in ('back_rabbet', 'drawer_bottom'):
        rects = [(groove['x'], groove['z'], groove['x'] + groove['span_x'],
                  groove['z'] + groove['span_z'])]
    elif kind == 'led_wire':
        rects = [(groove['x'], groove['y'], groove['x'] + groove['span_x'],
                  groove['y'] + groove['span_y'])]
    elif kind == 'led':
        x = groove.get('x', 0)
        y = groove['offset'] - groove['width'] / 2
        rects = [(x, y, x + groove.get('span_x', board.width), y + groove['width'])]
    else:
        raise ValueError('Ten rodzaj wycięcia nie jest prostokątnym wręgiem formularza')
    for x1, y1, x2, y2 in rects:
        low, high = [0.] * 3, list(sizes)
        low[planes[0]], high[planes[0]] = x1, x2
        low[planes[1]], high[planes[1]] = y1, y2
        depth = groove['depth']
        low[axis], high[axis] = ((sizes[axis] - depth, sizes[axis])
                               if face[0] == '+' else (0, depth))
        yield low, high


def convert_rectangle(board, low, high):
    from parts.meble_pl_plan import face_surface
    u, v, normal = panel_axes(board)
    sizes = (board.width, board.depth, board.height)
    if not all(math.isfinite(c) for c in (*low, *high)):
        raise ValueError('Niefinitywna geometria wręgu')
    if any(lo < -1e-6 or hi > size + 1e-6 or hi <= lo
           for lo, hi, size in zip(low, high, sizes)):
        raise ValueError('Wręg wychodzi poza formatkę lub ma nieprawidłowy wymiar')
    if abs(low[normal]) < 1e-6:
        direction = '-' + 'xyz'[normal]
    elif abs(high[normal] - sizes[normal]) < 1e-6:
        direction = '+' + 'xyz'[normal]
    else:
        raise ValueError('Wręg nie otwiera się na płaszczyznę formatki')
    depth = mm(high[normal] - low[normal])
    if depth not in range(2, 14) or depth >= sizes[normal]:
        raise ValueError(f'Głębokość {depth:g} mm niedostępna dla wręgowania (2–13 mm, bez przecięcia płyty)')
    lengths = {a: mm(high[a] - low[a]) for a in (u, v)}
    narrow = min((u, v), key=lengths.get)
    width = lengths[narrow]
    if width not in WIDTHS:
        raise ValueError(f'Szerokość {width:g} mm niedostępna (3,2 / 4,2 / 10,2 mm)')
    offset_low, offset_high = mm(low[narrow]), mm(sizes[narrow] - high[narrow])
    is_high = offset_high < offset_low
    offset = offset_high if is_high else offset_low
    if offset not in range(51):
        raise ValueError(f'Odległość od krawędzi {offset:g} mm niedostępna (0–50 mm, pełne milimetry)')
    # Live form boundary checks: 100 mm panel / 3.2 mm cutter accepts
    # offset 21 and rejects 22; a 120 mm panel accepts 41.
    if sizes[narrow] - offset - width < 75 - 1e-6:
        raise ValueError('Za mało płyty za wręgiem: formularz wymaga co najmniej 75 mm do przeciwnej krawędzi')
    edge = ('right' if is_high else 'left') if narrow == u else ('top' if is_high else 'bottom')
    along = v if narrow == u else u
    start, end = mm(low[along]), mm(sizes[along] - high[along])
    # Vertical supplier X1 is measured from the TOP, unlike local coordinates.
    if along == v:
        start, end = end, start
    if (start or end) and lengths[along] < 99:
        raise ValueError('Za krótki wręg nieprzelotowy dla formularza (minimum 99 mm)')
    return dict(powierzchnia=face_surface(normal, direction, u, v),
                wregowanie_bok=edge, wregowanie_glebokosc=depth,
                wregowanie_szerokosc=width, wregowanie_odleglosc=offset,
                wregowanie_rodzaj='nprzelot' if start or end else 'przelot',
                wregowanie_x1=start, wregowanie_x2=end,
                wregowanie_przelot_x1=start == 0, wregowanie_przelot_x2=end == 0)


def board_grooves(board):
    entries, manual = [], []
    for groove in board.grooves:
        try:
            boxes = list(rectangles(board, groove))
        except (ValueError, KeyError) as exc:
            manual.append(dict(board=board.name, operation=groove['kind'], geometry=groove, reason=str(exc)))
            continue
        for index, (low, high) in enumerate(boxes, 1):
            details = dict(board=board.name, operation=groove['kind'], segment=index,
                           geometry=dict(low=low, high=high))
            try:
                entries.append((convert_rectangle(board, low, high), details))
            except ValueError as exc:
                manual.append(dict(details, reason=str(exc)))
    # One uninterrupted groove per face/edge, as agreed for this supplier.
    counts = Counter((e['powierzchnia'], e['wregowanie_bok']) for e, _ in entries)
    result = []
    for entry, details in entries:
        if counts[(entry['powierzchnia'], entry['wregowanie_bok'])] > 1:
            manual.append(dict(details, reason='Więcej niż jeden wręg na tej samej powierzchni i krawędzi; popraw YAML'))
        else:
            result.append(entry)
    return result, manual
