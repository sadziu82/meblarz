"""Material and edge finish shared by generators, preview and cut lists."""
from pathlib import Path
import fnmatch
import math
import yaml
from parts.motion import movable_group
from parts.precision import round_panel

ROOT = Path(__file__).resolve().parent.parent
FACE_AXES = {'left': (0, 0), 'right': (0, 1), 'front': (1, 0),
             'rear': (1, 1), 'bottom': (2, 0), 'top': (2, 1)}


def panel_axes(board):
    """Installed orientation: horizontal X/Y, fronts X/Z, sides Y/Z."""
    sizes = (board.width, board.depth, board.height)
    normal = sorted(range(3), key=lambda axis: (-sizes[axis], axis))[-1]
    return {0: (1, 2, 0), 1: (0, 2, 1), 2: (0, 1, 2)}[normal]


def grain_code(board):
    """Meble.pl/PRO100: 1 = height (vertical sides), 2 = width (other panels)."""
    return 1 if panel_axes(board)[2] == 0 else 2


def texture_axes(board):
    """The material image has grain along its horizontal (S) axis."""
    u, v, _ = panel_axes(board)
    return (v, u) if grain_code(board) == 1 else (u, v)


def face_texture_axes(board, face):
    """On banded edges S follows edge length, T follows board thickness."""
    normal = panel_axes(board)[2]
    face_axis = FACE_AXES[face][0]
    if face in board.edgebands and face_axis != normal:
        along = next(axis for axis in range(3) if axis not in (normal, face_axis))
        return along, normal
    return texture_axes(board)


def _panel(board):
    return board.fabrication and 'slide_' not in board.name


def _assembly(board):
    return ('moving', movable_group(board)) if board.movable else ('fixed', '')


def _covered(rect, covers, tolerance=1e-5):
    """Exact union coverage, not summed area (overlapping blockers may coincide)."""
    u0, u1, v0, v1 = rect
    clipped = [(max(u0, a), min(u1, b), max(v0, c), min(v1, d))
               for a, b, c, d in covers]
    clipped = [(a, b, c, d) for a, b, c, d in clipped
               if b-a > tolerance and d-c > tolerance]
    cuts = sorted({u0, u1, *(x for r in clipped for x in r[:2])})
    for left, right in zip(cuts, cuts[1:]):
        if right-left <= tolerance:
            continue
        middle = (left+right)/2
        spans = sorted((c, d) for a, b, c, d in clipped if a <= middle <= b)
        end = v0
        for start, stop in spans:
            if start > end+tolerance:
                return False
            end = max(end, stop)
        if end < v1-tolerance:
            return False
    return bool(clipped)


def _visible_side(board, peers, bounds):
    """A vertical side is external if either broad face has an unoccluded region."""
    low, high = bounds[id(board)]
    rect = (low[1], high[1], low[2], high[2])
    for positive in (False, True):
        covers = []
        for neighbor in peers:
            if neighbor is board or neighbor.yaw or neighbor.corner_radius:
                continue
            nlow, nhigh = bounds[id(neighbor)]
            if (nlow[0] >= high[0]-1e-5 if positive else nhigh[0] <= low[0]+1e-5):
                covers.append((nlow[1], nhigh[1], nlow[2], nhigh[2]))
        if not _covered(rect, covers):
            return True
    return False


def automatic_edgebands(boards, thickness, *, rear_edges=False, floor_edges=False, floor_z=0):
    """Finish complete exposed narrow faces, independent of the current camera.

    Only permanent contacts within one moving assembly can conceal an edge.
    Any uncovered portion makes the whole edge a candidate for banding.
    """
    panels = [b for b in boards if _panel(b)]
    floor = floor_z
    bounds = {id(b): (b.pos, tuple(p+s for p, s in zip(
        b.pos, (b.width, b.depth, b.height)))) for b in panels}
    for board in panels:
        board.edgebands = {}
        sizes = (board.width, board.depth, board.height)
        if min(sizes) <= 6:  # thin HDF/back panels are not edge-banded
            continue
        low, high = bounds[id(board)]
        normal = panel_axes(board)[2]
        assembly = _assembly(board)
        peers = [b for b in panels if _assembly(b) == assembly]
        # Hinged fronts and the foremost vertical panel of a drawer assembly.
        front = bool(board.opening) or (board.movable and normal == 1 and
                abs(low[1] - min(b.pos[1] for b in peers)) < 1e-5)
        for face, (axis, positive) in FACE_AXES.items():
            if axis == normal or face in board.covered_edges:
                continue
            if face == 'bottom' and floor is not None and abs(low[2]-floor) < 1e-5 and not floor_edges:
                continue
            if not front and face == 'rear':
                if rear_edges is False:
                    continue
                if rear_edges == 'visible_sides' and not (
                        normal == 0 and _visible_side(board, peers, bounds)):
                    continue
            plane = high[axis] if positive else low[axis]
            other = [i for i in range(3) if i != axis]
            u, v = other
            rect = (low[u], high[u], low[v], high[v])
            covers = []
            for neighbor in peers:
                if neighbor is board or neighbor.yaw or neighbor.corner_radius:
                    continue
                nlow, nhigh = bounds[id(neighbor)]
                touches = (nlow[axis] <= plane+1e-5 and nhigh[axis] > plane+1e-5
                           if positive else
                           nhigh[axis] >= plane-1e-5 and nlow[axis] < plane-1e-5)
                if touches:
                    covers.append((nlow[u], nhigh[u], nlow[v], nhigh[v]))
            if front or not _covered(rect, covers):
                board.edgebands[face] = thickness
    return boards


def material_selections(material):
    """Resolve explicit per-thickness choices; never assume a decor for other sizes."""
    chosen = {}
    if material.get('board'):
        chosen[float(material.get('thickness', 18))] = material['board']
    for size, value in material.get('boards_by_thickness', {}).items():
        size = float(size)
        if not math.isfinite(size) or size <= 0:
            raise ValueError('Invalid material thickness')
        chosen[size] = value
    library = yaml.safe_load((ROOT / 'db/materials.yaml').read_text())['materials']
    result = {}
    for size, value in chosen.items():
        if isinstance(value, str):
            if value not in library:
                raise ValueError(f'Unknown material board: {value}')
            spec = {**library[value], 'id': value}
        elif isinstance(value, dict):
            spec = dict(value)
            spec.setdefault('id', spec.get('name', f'Płyta {size:g} mm'))
        else:
            raise ValueError(f'Material for {size:g} mm must be a library name or mapping')
        if spec.get('texture') and not (ROOT / spec['texture']).is_file():
            raise ValueError(f'Missing material texture: {spec["texture"]}')
        result[size] = spec
    return result


def apply_finishes(boards, config):
    for board in boards:
        if _panel(board):
            round_panel(board)
    material = config.get('material', {})
    selections = material_selections(material)
    edges = material.get('edge_banding', {})
    thickness = float(edges.get('thickness', 0.8))
    if not math.isfinite(thickness) or thickness <= 0:
        raise ValueError('Edge banding thickness must be positive')
    rear_edges = edges.get('band_rear_edges', edges.get('rear_edges', False))
    if 'band_rear_edges' in edges and not isinstance(edges['band_rear_edges'], bool):
        raise ValueError('band_rear_edges must be true or false')
    if rear_edges not in (True, False, 'visible_sides'):
        raise ValueError('rear_edges must be true, false or visible_sides')
    automatic_edgebands(boards, thickness,
                        rear_edges=rear_edges,
                        floor_edges=edges.get('floor_edges', False),
                        floor_z=None if 'niche' in config else 0)
    if not edges.get('automatic', True):
        for board in boards:
            board.edgebands = {}
    patterns = edges.get('boards', {})
    for pattern in patterns:
        if not any(fnmatch.fnmatchcase(b.name, pattern) and b.fabrication for b in boards):
            raise ValueError(f'Edge banding matches no board: {pattern}')
    for board in boards:
        if not board.fabrication or 'slide_' in board.name:
            continue
        spec = selections.get(min(board.width, board.depth, board.height))
        if spec:
            board.material_id = spec['id']
            if spec.get('texture'):
                board.material_texture = str(ROOT / spec['texture'])
                board.texture_size = tuple(spec.get('texture_size_mm', [900, 600]))
        for pattern, faces in patterns.items():
            if fnmatch.fnmatchcase(board.name, pattern):
                if not isinstance(faces, list):
                    raise ValueError(f'{pattern}: edge banding must be a list')
                normal = panel_axes(board)[2]
                for face in faces:
                    if face not in FACE_AXES or FACE_AXES[face][0] == normal:
                        raise ValueError(f'{board.name}: {face} is not a narrow panel edge')
                board.edgebands = {face: thickness for face in faces}
    return boards


def edge_outline(board, face, offset=0.35):
    """Perimeter of a narrow face, just outside the board to prevent z fighting."""
    if board.corner_radius and any(board.rounded_front_corners) and face in ('front', 'left', 'right'):
        w, d, h = board.width, board.depth, board.height
        r = min(board.corner_radius, w/2, d)
        left, right = board.rounded_front_corners
        if face == 'front':
            path = []
            if left:
                path.extend((r+(r+offset)*math.cos(a), r+(r+offset)*math.sin(a))
                            for a in (math.pi + i*math.pi/32 for i in range(17)))
            else:
                path.append((0, -offset))
            if right:
                path.extend((w-r+(r+offset)*math.cos(a), r+(r+offset)*math.sin(a))
                            for a in (-math.pi/2 + i*math.pi/32 for i in range(17)))
            else:
                path.append((w, -offset))
        elif face == 'left':
            path = [(-offset, r if left else 0), (-offset, d)]
        else:
            path = [(w+offset, r if right else 0), (w+offset, d)]
        return [(x, y, 0) for x, y in path] + [(x, y, h) for x, y in reversed(path)]
    axis, high = FACE_AXES[face]
    sizes = (board.width, board.depth, board.height)
    other = [a for a in range(3) if a != axis]
    points = []
    for u, v in ((0, 0), (1, 0), (1, 1), (0, 1)):
        point = [0., 0., 0.]
        point[axis] = sizes[axis] + offset if high else -offset
        point[other[0]] = u * sizes[other[0]]
        point[other[1]] = v * sizes[other[1]]
        points.append(tuple(point))
    return points


def csv_edging(board):
    """PRO100: blank=none, -=one, ==both parallel edges."""
    width_axis, height_axis, _ = panel_axes(board)
    return tuple(('' if count == 0 else '-' if count == 1 else '=')
                 for axis in (height_axis, width_axis)
                 for count in [sum(FACE_AXES[f][0] == axis for f in board.edgebands)])
