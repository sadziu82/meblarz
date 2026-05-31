"""
Obliczenia geometrii szuflady wewnętrznej wg zasad_meblarskie.md.
Wejście: wymiary wnęki + referencja do modelu prowadnicy z prowadnice.yaml.
Wyjście: słownik z wymiarami wszystkich elementów i pozycjami otworów.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple
import yaml


@dataclass
class Hole:
    """Otwór montażowy prowadnicy."""
    x: float
    y: float
    z: float
    diameter: float
    depth: float
    direction: str  # normalna powierzchni: '+x','-x','+y','-y','+z','-z'


@dataclass
class JointHole:
    """Otwór łączeniowy (konfirmat lub kołek) między dwoma deskami."""
    x: float
    y: float
    z: float
    direction: str      # normalna powierzchni (wiercenie w kierunku odwrotnym)
    element: int        # 1 = pierwszy element (czerwony), 2 = drugi (zielony)
    partner: str        # nazwa deski partnerskiej
    hole_type: str = 'confirmat'  # 'confirmat' | 'dowel'


@dataclass
class Board:
    name: str
    width: float   # X
    height: float  # Z
    depth: float   # Y
    pos: Tuple[float, float, float]  # (x, y, z) left-bottom-front corner
    color: Tuple[float, float, float, float] = (0.8, 0.65, 0.45, 1.0)
    holes: List[Hole] = field(default_factory=list)
    joint_holes: List[JointHole] = field(default_factory=list)


@dataclass
class DrawerModel:
    boards: List[Board] = field(default_factory=list)
    open_amount: float = 0.0
    max_travel: float = 0.0
    slide_model: str = ""
    slide_nl: int = 0
    joints: List[Tuple[str, str]] = field(default_factory=list)  # (first_elem, second_elem)


_SLIDES_DB: dict | None = None

def _load_slides_db() -> dict:
    global _SLIDES_DB
    if _SLIDES_DB is None:
        db_path = Path(__file__).parent / 'prowadnice.yaml'
        with open(db_path) as f:
            _SLIDES_DB = yaml.safe_load(f)['prowadnice']
    return _SLIDES_DB


def _joint_positions(start: float, length: float,
                     max_from_end: float = 100, max_spacing: float = 300) -> list[float]:
    """
    Pozycje konfirmatów wzdłuż krawędzi (zasady 27/29):
    1/4 i 3/4 długości, max 100mm od końca, jeśli odstęp >300mm – dodaj pośrednie.
    """
    if length < 2 * max_from_end:
        return [round(start + length / 2, 1)]
    p1 = max(start + max_from_end, start + length * 0.25)
    p2 = min(start + length - max_from_end, start + length * 0.75)
    positions = sorted({round(p1, 1), round(p2, 1)})
    i = 0
    while i < len(positions) - 1:
        if positions[i + 1] - positions[i] > max_spacing:
            positions.insert(i + 1, round((positions[i] + positions[i + 1]) / 2, 1))
        else:
            i += 1
    return positions


def _select_nl(available: list[int], max_depth: float) -> int:
    """Wybierz największe NL nieprzekraczające max_depth."""
    candidates = [nl for nl in sorted(available) if nl <= max_depth]
    if not candidates:
        raise ValueError(
            f"Żadne dostępne NL ({available}) nie mieści się w głębokości {max_depth:.1f}mm"
        )
    return candidates[-1]


def _mount_holes_y(slide_cfg: dict, nl: int, y_start: float) -> list[float]:
    """
    Generuje absolutne pozycje Y otworów montażowych prowadnicy na boku skrzynki.
    Pozycje liczone od y_start (= przednia krawędź boku skrzynki).
    Otwory wg schematu z karty produktowej – używane tylko te mieszczące się w NL.
    """
    mount = slide_cfg['montaz_szuflada_wewnetrzna']
    first = mount['pierwszy_otwor_od_krawedzi_mm']
    spacings = mount['schemat_odstepow_mm']

    positions = [first]
    for s in spacings:
        nxt = positions[-1] + s
        if nxt > nl:
            break
        positions.append(nxt)

    return [y_start + p for p in positions]


def load_drawer(path: str) -> DrawerModel:
    with open(path) as f:
        cfg = yaml.safe_load(f)

    nw = cfg['niche']['width']
    nh = cfg['niche']['height']
    nd = cfg['niche']['depth']

    mdf = cfg['material']['thickness']
    bot = cfg['material']['bottom_thickness']

    # Wczytaj model prowadnicy z bazy
    slide_model_id = cfg['slides']['model']
    db = _load_slides_db()
    if slide_model_id not in db:
        raise ValueError(f"Nieznany model prowadnicy: '{slide_model_id}'. Dostępne: {list(db)}")
    slide_cfg = db[slide_model_id]

    slide_side = slide_cfg['luz_boczny_mm']       # luz z każdej strony (zasada 18)
    slide_rear = slide_cfg['luz_tylny_mm']         # luz tylny (zasada 19)
    hole_d     = slide_cfg['montaz_szuflada_wewnetrzna']['srednica_otworow_skrzynka_mm']
    hole_dep   = slide_cfg['montaz_szuflada_wewnetrzna']['glebokos_otworow_mm']

    top_gap  = cfg['front']['top_gap']
    inset    = cfg['front']['inset']
    side_gap = cfg['front']['side_gap']
    bot_gap  = cfg['front']['bottom_gap']

    # --- Front szuflady ---
    front_W = nw - 2 * side_gap
    front_H = nh - top_gap - bot_gap
    front_D = mdf

    # --- Skrzynka szuflady ---
    # box_W_ext = zasada 13: niche_W - 2*luz_boczny
    box_W_ext = nw - 2 * slide_side

    # Maksymalna głębokość skrzynki przed doborem NL (zasada 14)
    # Skrzynka zaczyna się za tylną ścianą frontu: front_D + inset
    max_box_depth = nd - (front_D + inset) - slide_rear

    # Dobierz NL: szuflada wewnętrzna → SKL = NL (zasada z karty H53)
    # Wybierz największe dostępne NL nieprzekraczające max_box_depth
    available_nl = slide_cfg['dostepne_dlugosci_mm']
    nl = _select_nl(available_nl, max_box_depth)
    box_depth = float(nl)  # głębokość skrzynki = NL prowadnicy

    # Wysokość boków = 2/3 wysokości frontu (zasada 6)
    side_H = round((2 / 3) * front_H)

    # --- Pozycje elementów ---
    front_x = side_gap
    front_y = inset
    front_z = bot_gap

    box_start_y = front_y + front_D  # tylna ściana frontu = inset + mdf
    box_start_x = slide_side

    bottom_z = front_z + 2  # dno skrzynki 2mm wyżej niż spód frontu
    bottom_y = box_start_y

    side_z = bottom_z + bot
    side_y = box_start_y

    rear_y = box_start_y + box_depth - mdf
    rear_z = side_z

    # Wysokość montażu prowadnicy: spód prowadnicy 50mm od spodu dna (zasada 20)
    slide_z_abs = bottom_z + 50.0

    # Pozycje otworów montażowych (Y) na boku skrzynki
    holes_y = _mount_holes_y(slide_cfg, nl, box_start_y)

    boards = []

    # Front
    boards.append(Board(
        name='front',
        width=front_W, height=front_H, depth=front_D,
        pos=(front_x, front_y, front_z),
        color=(0.6, 0.45, 0.3, 1.0),
    ))

    # Dno (zasady 12–14: pełna szerokość i głębokość)
    boards.append(Board(
        name='bottom',
        width=box_W_ext, height=bot, depth=box_depth,
        pos=(box_start_x, bottom_y, bottom_z),
        color=(0.75, 0.6, 0.4, 1.0),
    ))

    # Bok lewy (zasada 16: głębokość = box_depth - mdf)
    left = Board(
        name='side_left',
        width=mdf, height=side_H, depth=box_depth - mdf,
        pos=(box_start_x, side_y, side_z),
        color=(0.7, 0.55, 0.38, 1.0),
    )
    for hy in holes_y:
        left.holes.append(Hole(
            x=box_start_x, y=hy, z=slide_z_abs,
            diameter=hole_d, depth=hole_dep, direction='-x',
        ))
    boards.append(left)

    # Bok prawy
    right_x = box_start_x + box_W_ext - mdf
    right = Board(
        name='side_right',
        width=mdf, height=side_H, depth=box_depth - mdf,
        pos=(right_x, side_y, side_z),
        color=(0.7, 0.55, 0.38, 1.0),
    )
    for hy in holes_y:
        right.holes.append(Hole(
            x=right_x + mdf, y=hy, z=slide_z_abs,
            diameter=hole_d, depth=hole_dep, direction='+x',
        ))
    boards.append(right)

    # Tył (zasada 15: pełna szerokość box_W_ext, leży na dnie)
    boards.append(Board(
        name='rear',
        width=box_W_ext, height=side_H, depth=mdf,
        pos=(box_start_x, rear_y, rear_z),
        color=(0.7, 0.55, 0.38, 1.0),
    ))

    # --- Otwory łączeniowe (konfirmaty) wg zasad 27/29 ---
    bd = {b.name: b for b in boards}
    joints: list[tuple[str, str]] = []
    JH = JointHole

    def _add_confirmats(name_a: str, name_b: str,
                        positions: list[float],
                        ax: float, ay_or_az_a: float, az_or_ay_a: float, dir_a: str,
                        bx: float, ay_or_az_b: float, az_or_ay_b: float, dir_b: str,
                        axis: str = 'y'):
        """Dodaj konfirmaty między dwiema deskami."""
        for p in positions:
            if axis == 'y':
                bd[name_a].joint_holes.append(JH(ax, p, az_or_ay_a, dir_a, 1, name_b))
                bd[name_b].joint_holes.append(JH(bx, p, az_or_ay_b, dir_b, 2, name_a))
            elif axis == 'x':
                bd[name_a].joint_holes.append(JH(p, ay_or_az_a, az_or_ay_a, dir_a, 1, name_b))
                bd[name_b].joint_holes.append(JH(p, ay_or_az_b, az_or_ay_b, dir_b, 2, name_a))
            else:  # axis == 'z'
                bd[name_a].joint_holes.append(JH(p, ay_or_az_a, az_or_ay_a, dir_a, 1, name_b))
                bd[name_b].joint_holes.append(JH(p, ay_or_az_b, az_or_ay_b, dir_b, 2, name_a))
        joints.append((name_a, name_b))

    x_sl = box_start_x + mdf / 2   # środek boku lewego w X
    x_sr = right_x + mdf / 2       # środek boku prawego w X
    rear_y_back = rear_y + mdf      # tylna ściana tylnej deski

    # 1. Dno ↔ Bok lewy  (konfirmaty w osi Y, otwory -Z na dnie, -Z na boku)
    for yp in _joint_positions(side_y, box_depth - mdf):
        bd['bottom'].joint_holes.append(JH(x_sl, yp, bottom_z, '-z', 1, 'side_left'))
        bd['side_left'].joint_holes.append(JH(x_sl, yp, side_z, '-z', 2, 'bottom'))
    joints.append(('bottom', 'side_left'))

    # 2. Dno ↔ Bok prawy
    for yp in _joint_positions(side_y, box_depth - mdf):
        bd['bottom'].joint_holes.append(JH(x_sr, yp, bottom_z, '-z', 1, 'side_right'))
        bd['side_right'].joint_holes.append(JH(x_sr, yp, side_z, '-z', 2, 'bottom'))
    joints.append(('bottom', 'side_right'))

    # 3. Tył ↔ Bok lewy  (konfirmaty w osi Z, od tyłu tylnej deski w -Y do boku)
    for zp in _joint_positions(rear_z, side_H):
        bd['rear'].joint_holes.append(JH(x_sl, rear_y_back, zp, '+y', 1, 'side_left'))
        bd['side_left'].joint_holes.append(JH(x_sl, rear_y, zp, '+y', 2, 'rear'))
    joints.append(('rear', 'side_left'))

    # 4. Tył ↔ Bok prawy
    for zp in _joint_positions(rear_z, side_H):
        bd['rear'].joint_holes.append(JH(x_sr, rear_y_back, zp, '+y', 1, 'side_right'))
        bd['side_right'].joint_holes.append(JH(x_sr, rear_y, zp, '+y', 2, 'rear'))
    joints.append(('rear', 'side_right'))

    # 5. Dno ↔ Tył  (konfirmaty w osi X, od spodu w -Z przez dno do podstawy tyłu)
    rear_cy = rear_y + mdf / 2
    for xp in _joint_positions(box_start_x, box_W_ext):
        bd['bottom'].joint_holes.append(JH(xp, rear_cy, bottom_z, '-z', 1, 'rear'))
        bd['rear'].joint_holes.append(JH(xp, rear_cy, rear_z, '-z', 2, 'bottom'))
    joints.append(('bottom', 'rear'))

    # 6. Front ↔ Bok lewy  (kołki drewniane, zasady 30-33+35)
    # Front widoczny → kołki. Otwory frontu: w płaszczyźnie (tył frontu, depth=11mm).
    # Otwory boku: w czole (ściana przednia boku, depth=27mm).
    # Wspólny wymiar = min(front_H, side_H) = side_H (krótszy z dwóch).
    front_back_y = front_y + front_D          # tylna ściana frontu = box_start_y
    for zp in _joint_positions(side_z, side_H):
        bd['front'].joint_holes.append(
            JH(x_sl, front_back_y, zp, '+y', 1, 'side_left', 'dowel'))
        bd['side_left'].joint_holes.append(
            JH(x_sl, side_y, zp, '-y', 2, 'front', 'dowel'))
    joints.append(('front', 'side_left'))

    # 7. Front ↔ Bok prawy
    for zp in _joint_positions(side_z, side_H):
        bd['front'].joint_holes.append(
            JH(x_sr, front_back_y, zp, '+y', 1, 'side_right', 'dowel'))
        bd['side_right'].joint_holes.append(
            JH(x_sr, side_y, zp, '-y', 2, 'front', 'dowel'))
    joints.append(('front', 'side_right'))

    # 8. Front ↔ Dno  (zawsze dwa kołki, zasada 35)
    # Otwory frontu: w płaszczyźnie (tył frontu), Z = środek grubości dna
    # Otwory dna: w czole (przednia krawędź), depth = 27mm
    bottom_z_center = bottom_z + bot / 2
    for xp in _joint_positions(box_start_x, box_W_ext):
        bd['front'].joint_holes.append(
            JH(xp, front_back_y, bottom_z_center, '+y', 1, 'bottom', 'dowel'))
        bd['bottom'].joint_holes.append(
            JH(xp, bottom_y, bottom_z_center, '-y', 2, 'front', 'dowel'))
    joints.append(('front', 'bottom'))

    # --- Wyśrodkuj model: (0,0,0) = centrum bbox ---
    xs = [b.pos[0] for b in boards] + [b.pos[0] + b.width  for b in boards]
    ys = [b.pos[1] for b in boards] + [b.pos[1] + b.depth  for b in boards]
    zs = [b.pos[2] for b in boards] + [b.pos[2] + b.height for b in boards]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    cz = (min(zs) + max(zs)) / 2

    for b in boards:
        b.pos = (b.pos[0] - cx, b.pos[1] - cy, b.pos[2] - cz)
        b.holes = [
            Hole(h.x - cx, h.y - cy, h.z - cz, h.diameter, h.depth, h.direction)
            for h in b.holes
        ]
        b.joint_holes = [
            JH(jh.x - cx, jh.y - cy, jh.z - cz,
               jh.direction, jh.element, jh.partner, jh.hole_type)
            for jh in b.joint_holes
        ]

    return DrawerModel(
        boards=boards,
        max_travel=box_depth,
        slide_model=slide_model_id,
        slide_nl=nl,
        joints=joints,
    )
