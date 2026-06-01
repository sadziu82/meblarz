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
    movable: bool = True  # False = element korpusu (nie przesuwa się przy otwarciu)


@dataclass
class DrawerModel:
    boards: List[Board] = field(default_factory=list)
    open_amount: float = 0.0
    max_travel: float = 0.0
    slide_model: str = ""
    slide_nl: int = 0
    joints: List[Tuple[str, str]] = field(default_factory=list)
    drawer_count: int = 0  # 0 = samodzielna szuflada, >0 = komoda


_SLIDES_DB: dict | None = None

def _load_slides_db() -> dict:
    global _SLIDES_DB
    if _SLIDES_DB is None:
        db_path = Path(__file__).parent.parent / 'baza' / 'prowadnice.yaml'
        with open(db_path) as f:
            _SLIDES_DB = yaml.safe_load(f)['prowadnice']
    return _SLIDES_DB


def _joint_positions(start: float, length: float,
                     max_from_end: float = 100, max_spacing: float = 300) -> list[float]:
    """
    Pozycje konfirmatów / kołków wzdłuż krawędzi (zasady 36/39):
    1/4 i 3/4 długości, ale nie dalej niż max_from_end od końca.
    Jeśli odstęp >300mm – dodaj pośrednie w równych odstępach.
    """
    # Pozycje liczone RELATIVE (od 0), zaokrąglone do mm, potem dodajemy start
    # Próg 40mm: krótsza krawędź → 1 otwór w środku (zbyt mało miejsca na 2)
    if length < 40:
        return [start + round(length / 2)]
    p1 = round(min(length * 0.25, max_from_end))
    p2 = round(max(length * 0.75, length - max_from_end))
    positions = sorted({p1, p2})
    i = 0
    while i < len(positions) - 1:
        if positions[i + 1] - positions[i] > max_spacing:
            positions.insert(i + 1, round((positions[i] + positions[i + 1]) / 2))
        else:
            i += 1
    return [start + p for p in positions]


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


def _build_drawer(
    nw: float, front_H: float, nd: float,
    mdf: float, bot: float,
    slide_cfg: dict,
    inset: float, side_gap: float, bot_gap: float,
) -> tuple[list[Board], list[tuple[str, str]], int]:
    """
    Oblicza geometrię szuflady wewnętrznej.
    Pozycje we współrzędnych niszy (lewy-przód-spód = 0,0,0).
    front_H = wysokość frontu (już po odjęciu top_gap i bot_gap przez wywołującego).
    Zwraca (boards, joints, nl).
    """
    slide_side = slide_cfg['luz_boczny_mm']
    slide_rear = slide_cfg['luz_tylny_mm']
    hole_d   = slide_cfg['montaz_szuflada_wewnetrzna']['srednica_otworow_skrzynka_mm']
    hole_dep = slide_cfg['montaz_szuflada_wewnetrzna']['glebokos_otworow_mm']

    front_D = mdf

    box_W_ext = nw - 2 * slide_side
    max_box_depth = nd - (front_D + inset) - slide_rear
    nl = _select_nl(slide_cfg['dostepne_dlugosci_mm'], max_box_depth)
    box_depth = float(nl)

    side_H = round((2 / 3) * front_H)

    front_x = side_gap
    front_y = inset
    front_z = bot_gap

    box_start_y = front_y + front_D
    box_start_x = slide_side

    bottom_z = front_z + 2
    bottom_y = box_start_y

    side_z = bottom_z + bot
    side_y = box_start_y

    rear_y = box_start_y + box_depth - mdf
    rear_z = side_z

    slide_z_abs = bottom_z + 50.0
    holes_y = _mount_holes_y(slide_cfg, nl, box_start_y)

    boards: list[Board] = []

    boards.append(Board(
        name='front',
        width=nw - 2 * side_gap, height=front_H, depth=front_D,
        pos=(front_x, front_y, front_z),
        color=(0.6, 0.45, 0.3, 1.0),
    ))

    boards.append(Board(
        name='bottom',
        width=box_W_ext, height=bot, depth=box_depth,
        pos=(box_start_x, bottom_y, bottom_z),
        color=(0.75, 0.6, 0.4, 1.0),
    ))

    right_x = box_start_x + box_W_ext - mdf
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

    boards.append(Board(
        name='rear',
        width=box_W_ext, height=side_H, depth=mdf,
        pos=(box_start_x, rear_y, rear_z),
        color=(0.7, 0.55, 0.38, 1.0),
    ))

    bd = {b.name: b for b in boards}
    joints: list[tuple[str, str]] = []
    JH = JointHole

    x_sl = box_start_x + mdf / 2
    x_sr = right_x + mdf / 2
    rear_y_back = rear_y + mdf
    rear_cy = rear_y + mdf / 2

    for yp in _joint_positions(side_y, box_depth - mdf):
        bd['bottom'].joint_holes.append(JH(x_sl, yp, bottom_z, '-z', 1, 'side_left'))
        bd['side_left'].joint_holes.append(JH(x_sl, yp, side_z, '-z', 2, 'bottom'))
    joints.append(('bottom', 'side_left'))

    for yp in _joint_positions(side_y, box_depth - mdf):
        bd['bottom'].joint_holes.append(JH(x_sr, yp, bottom_z, '-z', 1, 'side_right'))
        bd['side_right'].joint_holes.append(JH(x_sr, yp, side_z, '-z', 2, 'bottom'))
    joints.append(('bottom', 'side_right'))

    for zp in _joint_positions(rear_z, side_H):
        bd['rear'].joint_holes.append(JH(x_sl, rear_y_back, zp, '+y', 1, 'side_left'))
        bd['side_left'].joint_holes.append(JH(x_sl, rear_y, zp, '+y', 2, 'rear'))
    joints.append(('rear', 'side_left'))

    for zp in _joint_positions(rear_z, side_H):
        bd['rear'].joint_holes.append(JH(x_sr, rear_y_back, zp, '+y', 1, 'side_right'))
        bd['side_right'].joint_holes.append(JH(x_sr, rear_y, zp, '+y', 2, 'rear'))
    joints.append(('rear', 'side_right'))

    for xp in _joint_positions(box_start_x, box_W_ext):
        bd['bottom'].joint_holes.append(JH(xp, rear_cy, bottom_z, '-z', 1, 'rear'))
        bd['rear'].joint_holes.append(JH(xp, rear_cy, rear_z, '-z', 2, 'bottom'))
    joints.append(('bottom', 'rear'))

    front_back_y = front_y + front_D
    for zp in _joint_positions(side_z, side_H):
        bd['front'].joint_holes.append(JH(x_sl, front_back_y, zp, '+y', 1, 'side_left', 'dowel'))
        bd['side_left'].joint_holes.append(JH(x_sl, side_y, zp, '-y', 2, 'front', 'dowel'))
    joints.append(('front', 'side_left'))

    for zp in _joint_positions(side_z, side_H):
        bd['front'].joint_holes.append(JH(x_sr, front_back_y, zp, '+y', 1, 'side_right', 'dowel'))
        bd['side_right'].joint_holes.append(JH(x_sr, side_y, zp, '-y', 2, 'front', 'dowel'))
    joints.append(('front', 'side_right'))

    bottom_z_center = bottom_z + bot / 2
    for xp in _joint_positions(box_start_x, box_W_ext):
        bd['front'].joint_holes.append(JH(xp, front_back_y, bottom_z_center, '+y', 1, 'bottom', 'dowel'))
        bd['bottom'].joint_holes.append(JH(xp, bottom_y, bottom_z_center, '-y', 2, 'front', 'dowel'))
    joints.append(('front', 'bottom'))

    return boards, joints, nl


def _shift_boards(boards: list[Board], dx: float, dy: float, dz: float) -> list[Board]:
    """Przesuwa wszystkie deski i ich otwory o podany offset."""
    result = []
    for b in boards:
        result.append(Board(
            name=b.name,
            width=b.width, height=b.height, depth=b.depth,
            pos=(b.pos[0] + dx, b.pos[1] + dy, b.pos[2] + dz),
            color=b.color,
            holes=[Hole(h.x+dx, h.y+dy, h.z+dz, h.diameter, h.depth, h.direction)
                   for h in b.holes],
            joint_holes=[JointHole(jh.x+dx, jh.y+dy, jh.z+dz,
                                   jh.direction, jh.element, jh.partner, jh.hole_type)
                         for jh in b.joint_holes],
            movable=b.movable,
        ))
    return result


def _center_model(boards: list[Board]) -> list[Board]:
    """Przesuwa cały model tak, by centrum bboxa znalazło się w (0,0,0)."""
    xs = [b.pos[0] for b in boards] + [b.pos[0] + b.width  for b in boards]
    ys = [b.pos[1] for b in boards] + [b.pos[1] + b.depth  for b in boards]
    zs = [b.pos[2] for b in boards] + [b.pos[2] + b.height for b in boards]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    cz = (min(zs) + max(zs)) / 2
    return _shift_boards(boards, -cx, -cy, -cz)


def load_drawer(path: str) -> DrawerModel:
    with open(path) as f:
        cfg = yaml.safe_load(f)

    nw = cfg['niche']['width']
    nh = cfg['niche']['height']
    nd = cfg['niche']['depth']

    mdf = cfg['material']['thickness']
    bot = cfg['material']['bottom_thickness']

    slide_model_id = cfg['slides']['model']
    db = _load_slides_db()
    if slide_model_id not in db:
        raise ValueError(f"Nieznany model prowadnicy: '{slide_model_id}'. Dostępne: {list(db)}")
    slide_cfg = db[slide_model_id]

    top_gap = cfg['front']['top_gap']
    inset   = cfg['front']['inset']
    side_gap = cfg['front']['side_gap']
    bot_gap  = cfg['front']['bottom_gap']

    front_H = nh - top_gap - bot_gap

    boards, joints, nl = _build_drawer(nw, front_H, nd, mdf, bot, slide_cfg,
                                       inset, side_gap, bot_gap)
    boards = _center_model(boards)

    return DrawerModel(
        boards=boards,
        max_travel=float(nl),
        slide_model=slide_model_id,
        slide_nl=nl,
        joints=joints,
    )
