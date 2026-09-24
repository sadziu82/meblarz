"""
Inner drawer geometry calculations per design_rules.md.
Input: niche dimensions + slide model reference from db/slides.yaml.
Output: DrawerModel with all board dimensions and hole positions.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple
import yaml
from parts.front_rules import SIDE_REVEAL, END_REVEAL


@dataclass
class Hole:
    """Machining hole, for example for a slide or drawer handle."""
    x: float
    y: float
    z: float
    diameter: float
    depth: float
    direction: str  # surface normal: '+x','-x','+y','-y','+z','-z'
    kind: str = 'slide'
    through: bool = False


@dataclass
class JointHole:
    """Joint hole (confirmat or dowel) between two boards."""
    x: float
    y: float
    z: float
    direction: str      # surface normal (drilling in opposite direction)
    element: int        # 1 = first element (red), 2 = second (green)
    partner: str        # name of the partner board
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
    movable: bool = True        # False = carcass board (does not move on open)
    move_fraction: float = 1.0  # 0.0=fixed, 0.5=half-extension, 1.0=full (slide middle runner)
    travel: float | None = None # own travel distance [mm], otherwise model.max_travel
    corner_radius: float = 0.0  # front corner radius for shaped horizontal boards
    rounded_front_corners: Tuple[bool, bool] = (False, False)  # (left, right)
    grooves: list[dict] = field(default_factory=list)
    fabrication: bool = True  # False for purchased equipment shown only in preview
    yaw: float = 0.0  # preview rotation about local Z at pos, degrees
    opening: str = ''  # e.g. lift_up; construction/preview metadata
    label: str = ''  # non-production equipment label
    texture: str = ''  # project-relative image shown on this preview-only board
    preview_shape: str = ''  # 'cylinder_z' for round purchased equipment
    motion_parent: str = ''  # preview hardware follows this board's complete motion
    preview_mesh: str = ''  # normalized OBJ, positioned/scaled by the preview board
    cabinet_id: str = ''  # separate carcass identity for adjacent-cabinet joinery
    cabinet_side: str = ''  # 'left' or 'right' outer cheek of that carcass


@dataclass
class DrawerModel:
    boards: List[Board] = field(default_factory=list)
    open_amount: float = 0.0
    max_travel: float = 0.0
    slide_model: str = ""
    slide_nl: int = 0
    joints: List[Tuple[str, str]] = field(default_factory=list)
    drawer_count: int = 0  # 0 = standalone drawer, >0 = dresser
    notes: List[str] = field(default_factory=list)
    machining_issues: List[dict] = field(default_factory=list)


_SLIDES_DB: dict | None = None


def _resolve_handle(config: dict | None) -> dict | None:
    """Resolve a library handle while preserving per-project machining choices."""
    if not config or 'model' not in config:
        return config
    with (Path(__file__).parent.parent / 'db' / 'handles.yaml').open() as source:
        handles = yaml.safe_load(source)['handles']
    model = config['model']
    if model not in handles:
        raise ValueError(f'Unknown handle model: {model}')
    return {**handles[model], **config}


def _load_slides_db() -> dict:
    global _SLIDES_DB
    if _SLIDES_DB is None:
        db_path = Path(__file__).parent.parent / 'db' / 'slides.yaml'
        with open(db_path) as f:
            _SLIDES_DB = yaml.safe_load(f)['slides']
    return _SLIDES_DB


def _require_side_slide(slide: dict) -> None:
    if slide.get('mounting', 'side') != 'side' or not slide.get('geometry_supported', True):
        raise ValueError(f"{slide.get('symbol', slide.get('name'))}: prowadnica dolnego montażu; "
                         'obecny generator obsługuje prowadnice boczne. '
                         f"Maksymalna grubość boku tego modelu: {slide.get('max_side_thickness_mm')} mm.")


def _joint_positions(start: float, length: float,
                     max_from_end: float = 100, max_spacing: float = 300) -> list[float]:
    """
    Joint hole positions along an edge (rules 36/39):
    1/4 and 3/4 of length, but no further than max_from_end from either end.
    If spacing >300mm — add intermediate holes at equal intervals.
    """
    # Threshold 40mm: short edge → 1 hole in center (not enough room for 2)
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
    """Select the largest NL not exceeding max_depth."""
    candidates = [nl for nl in sorted(available) if nl <= max_depth]
    if not candidates:
        raise ValueError(
            f"No available NL ({available}) fits within depth {max_depth:.1f}mm"
        )
    return candidates[-1]


def _mount_holes_y(slide_cfg: dict, nl: int, y_start: float) -> list[float]:
    """Generate absolute Y positions of slide mounting holes on the box side."""
    mount = slide_cfg['inner_drawer_mount']
    first = mount['first_hole_from_edge_mm']
    spacings = mount['spacing_pattern_mm']

    positions = [first]
    for s in spacings:
        nxt = positions[-1] + s
        if nxt > nl:
            break
        positions.append(nxt)

    return [y_start + p for p in positions]


def _build_drawer(
    nw: float, front_H: float, nd: float,
    board_thickness: float, bot: float,
    slide_cfg: dict,
    inset: float, side_gap: float, bot_gap: float,
    target_nl: int | None = None,
    handle: dict | None = None,
    box_bottom_offset: float = 2,
) -> tuple[list[Board], list[tuple[str, str]], int]:
    """
    Calculate inner drawer geometry.
    Positions in niche coordinates (left-front-bottom = 0,0,0).
    front_H = front height (top_gap and bot_gap already subtracted by caller).
    target_nl: if given, use this NL instead of the maximum fitting one (rule 18).
    Returns (boards, joints, nl).
    """
    _require_side_slide(slide_cfg)
    slide_side = slide_cfg['side_clearance_mm']
    slide_rear = slide_cfg['rear_clearance_mm']
    hole_d   = slide_cfg['inner_drawer_mount']['box_hole_diameter_mm']
    hole_dep = slide_cfg['inner_drawer_mount']['hole_depth_mm']

    front_D = board_thickness

    box_W_ext     = nw - 2 * slide_side
    max_box_depth = nd - (front_D + inset) - slide_rear

    if target_nl is not None:
        available = slide_cfg['available_lengths_mm']
        if target_nl not in available:
            raise ValueError(
                f"NL {target_nl}mm not available for this slide model. "
                f"Available lengths: {available}"
            )
        if target_nl > max_box_depth:
            raise ValueError(
                f"Requested NL {target_nl}mm exceeds maximum box depth "
                f"{max_box_depth:.1f}mm for this niche"
            )
        nl = target_nl
    else:
        nl = _select_nl(slide_cfg['available_lengths_mm'], max_box_depth)

    box_depth = float(nl)

    side_H = round((2 / 3) * front_H)

    front_x = side_gap
    front_y = inset
    front_z = bot_gap

    box_start_y = front_y + front_D
    box_start_x = slide_side

    bottom_z = front_z + box_bottom_offset
    bottom_y = box_start_y

    side_z = bottom_z + bot
    side_y = box_start_y

    rear_y = box_start_y + box_depth - board_thickness
    rear_z = side_z

    height_mm    = slide_cfg.get('height_mm', 45)
    slide_bot_z  = bottom_z + 50.0               # slide bottom (rule 30)
    slide_hole_z = slide_bot_z + height_mm / 2   # mounting hole axis = centre of slide
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

    right_x = box_start_x + box_W_ext - board_thickness
    left = Board(
        name='side_left',
        width=board_thickness, height=side_H, depth=box_depth - board_thickness,
        pos=(box_start_x, side_y, side_z),
        color=(0.7, 0.55, 0.38, 1.0),
    )
    for hy in holes_y:
        left.holes.append(Hole(
            x=box_start_x, y=hy, z=slide_hole_z,
            diameter=hole_d, depth=hole_dep, direction='-x',
        ))
    boards.append(left)

    right = Board(
        name='side_right',
        width=board_thickness, height=side_H, depth=box_depth - board_thickness,
        pos=(right_x, side_y, side_z),
        color=(0.7, 0.55, 0.38, 1.0),
    )
    for hy in holes_y:
        right.holes.append(Hole(
            x=right_x + board_thickness, y=hy, z=slide_hole_z,
            diameter=hole_d, depth=hole_dep, direction='+x',
        ))
    boards.append(right)

    boards.append(Board(
        name='rear',
        width=box_W_ext, height=side_H, depth=board_thickness,
        pos=(box_start_x, rear_y, rear_z),
        color=(0.7, 0.55, 0.38, 1.0),
    ))

    bd = {b.name: b for b in boards}
    joints: list[tuple[str, str]] = []
    JH = JointHole

    x_sl = box_start_x + board_thickness / 2
    x_sr = right_x + board_thickness / 2
    rear_y_back = rear_y + board_thickness
    rear_cy = rear_y + board_thickness / 2

    for yp in _joint_positions(side_y, box_depth - board_thickness):
        bd['bottom'].joint_holes.append(JH(x_sl, yp, bottom_z, '-z', 1, 'side_left'))
        bd['side_left'].joint_holes.append(JH(x_sl, yp, side_z, '-z', 2, 'bottom'))
    joints.append(('bottom', 'side_left'))

    for yp in _joint_positions(side_y, box_depth - board_thickness):
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
    if handle:
        handle = _resolve_handle(handle)
        spacing = float(handle['hole_spacing'])
        diameter = float(handle.get('hole_diameter', 5))
        through = handle.get('hole_depth', front_D) == 'through'
        depth = front_D if through else float(handle.get('hole_depth', front_D))
        through = through or depth == front_D
        vertical = handle.get('vertical', 'offset_top')
        if vertical not in ('center', 'offset_top'):
            raise ValueError('handle.vertical must be center or offset_top')
        offset_top = front_H / 2 if vertical == 'center' else float(handle.get('offset_top', 40))
        if spacing <= 0 or spacing >= bd['front'].width:
            raise ValueError(
                f"Drawer handle hole_spacing ({spacing}mm) must be between 0 and "
                f"front width ({bd['front'].width}mm)"
            )
        z_handle = front_z + front_H - offset_top
        if not front_z <= z_handle <= front_z + front_H:
            raise ValueError(f"Drawer handle offset_top ({offset_top}mm) lies outside the front")
        for x_handle in (front_x + bd['front'].width / 2 - spacing / 2,
                         front_x + bd['front'].width / 2 + spacing / 2):
            bd['front'].holes.append(Hole(
                x=x_handle, y=front_back_y, z=z_handle,
                diameter=diameter, depth=depth, direction='+y', kind='handle', through=through,
            ))

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

    if bot == 3:
        # Thin HDF sits below the box and enters a 3 mm deep stopped front groove.
        groove_depth = 3
        if front_D <= groove_depth:
            raise ValueError('Drawer front must be thicker than the bottom groove')
        bottom = bd['bottom']
        bottom.pos = (bottom.pos[0], bottom.pos[1]-groove_depth, bottom.pos[2])
        bottom.depth += groove_depth
        bd['front'].grooves.append(dict(kind='drawer_bottom', face='+y', width=bot,
            depth=groove_depth, x=box_start_x-front_x, z=bottom_z-front_z,
            span_x=box_W_ext, span_z=bot))
        # Replace thick-board confirmats/dowels with small wood screws from below.
        for board in boards:
            board.joint_holes = [h for h in board.joint_holes
                                 if board.name != 'bottom' and h.partner != 'bottom']
        joints = [pair for pair in joints if 'bottom' not in pair]
        for name, points in (
            ('side_left', [(x_sl, yp) for yp in _joint_positions(side_y, box_depth-board_thickness)]),
            ('side_right', [(x_sr, yp) for yp in _joint_positions(side_y, box_depth-board_thickness)]),
            ('rear', [(xp, rear_cy) for xp in _joint_positions(box_start_x, box_W_ext)]),
        ):
            for xp, yp in points:
                bottom.holes.append(Hole(xp, yp, bottom_z, 3, bot, '-z', 'wood_screw', True))
                bd[name].holes.append(Hole(xp, yp, side_z, 2, 13, '-z', 'wood_screw_pilot'))
            joints.append(('bottom', name))

    # ── Slide body visualisation (3-part: outer / middle / inner) ────────────
    part_w = slide_side / 3.0
    _c = [
        (0.50, 0.53, 0.58, 1.0),  # outer — dark steel (fixed, on carcass)
        (0.62, 0.65, 0.70, 1.0),  # middle (half-extension)
        (0.72, 0.75, 0.80, 1.0),  # inner — light steel (moves with drawer)
    ]
    _f = [0.0, 0.5, 1.0]
    for k in range(3):
        boards.append(Board(
            name=f'slide_left_{"outer middle inner".split()[k]}',
            width=part_w, height=height_mm, depth=float(nl),
            pos=(k * part_w, box_start_y, slide_bot_z),
            color=_c[k], movable=(_f[k] > 0.0), move_fraction=_f[k],
        ))
    right_x0 = box_start_x + box_W_ext
    for k in range(3):
        # Right side mirrors left: inner is closest to the drawer box (k=0)
        boards.append(Board(
            name=f'slide_right_{"inner middle outer".split()[k]}',
            width=part_w, height=height_mm, depth=float(nl),
            pos=(right_x0 + k * part_w, box_start_y, slide_bot_z),
            color=_c[2 - k], movable=(_f[2 - k] > 0.0), move_fraction=_f[2 - k],
        ))

    return boards, joints, nl


def _shift_boards(boards: list[Board], dx: float, dy: float, dz: float) -> list[Board]:
    """Shift all boards and their holes by the given offset."""
    result = []
    for b in boards:
        result.append(Board(
            name=b.name,
            width=b.width, height=b.height, depth=b.depth,
            pos=(b.pos[0] + dx, b.pos[1] + dy, b.pos[2] + dz),
            color=b.color,
            holes=[Hole(h.x+dx, h.y+dy, h.z+dz, h.diameter, h.depth, h.direction, h.kind, h.through)
                   for h in b.holes],
            joint_holes=[JointHole(jh.x+dx, jh.y+dy, jh.z+dz,
                                   jh.direction, jh.element, jh.partner, jh.hole_type)
                         for jh in b.joint_holes],
            movable=b.movable,
            move_fraction=b.move_fraction,
            travel=b.travel,
            corner_radius=b.corner_radius,
            rounded_front_corners=b.rounded_front_corners,
            grooves=list(b.grooves),
            fabrication=b.fabrication,
            yaw=b.yaw,
            opening=b.opening,
            label=b.label,
            texture=b.texture,
            preview_shape=b.preview_shape,
            motion_parent=b.motion_parent,
            preview_mesh=b.preview_mesh,
        ))
    return result


def _center_model(boards: list[Board]) -> list[Board]:
    """Centre the model in X and Y; place the bottom face at Z=0 (floor)."""
    # Preview equipment must not move the furniture coordinate origin.
    bounds = [b for b in boards if b.fabrication] or boards
    xs = [b.pos[0] for b in bounds] + [b.pos[0] + b.width  for b in bounds]
    ys = [b.pos[1] for b in bounds] + [b.pos[1] + b.depth  for b in bounds]
    zs = [b.pos[2] for b in bounds] + [b.pos[2] + b.height for b in bounds]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    cz = min(zs)   # bottom of model at Z=0 (floor)
    return _shift_boards(boards, -cx, -cy, -cz)


def load_drawer(path: str) -> DrawerModel:
    with open(path) as f:
        cfg = yaml.safe_load(f)

    nw = cfg['niche']['width']
    nh = cfg['niche']['height']
    nd = cfg['niche']['depth']

    board_thickness = cfg['material']['thickness']
    bot = cfg['material']['bottom_thickness']

    slide_model_id = cfg['slides']['model']
    target_nl      = cfg['slides'].get('nl', None)
    db = _load_slides_db()
    if slide_model_id not in db:
        raise ValueError(f"Unknown slide model: '{slide_model_id}'. Available: {list(db)}")
    slide_cfg = db[slide_model_id]

    top_gap  = cfg['front']['top_gap']
    inset    = cfg['front']['inset']
    side_gap = cfg['front']['side_gap']
    bot_gap  = cfg['front']['bottom_gap']

    front_H = nh - top_gap - bot_gap
    if cfg['front'].get('mount', 'inset') == 'overlay':
        carcass_t = float(cfg['front'].get('carcass_thickness', board_thickness))
        side_gap = SIDE_REVEAL - carcass_t
        bot_gap = END_REVEAL - carcass_t
        front_H = nh + 2 * carcass_t - 2 * END_REVEAL
        inset = -(board_thickness + float(cfg['front'].get('carcass_gap', 2)))

    boards, joints, nl = _build_drawer(nw, front_H, nd, board_thickness, bot, slide_cfg,
                                       inset, side_gap, bot_gap,
                                       target_nl=target_nl,
                                       handle=cfg['front'].get('handle'),
                                       box_bottom_offset=carcass_t + 2 if cfg['front'].get('mount') == 'overlay' else 2)
    boards = _center_model(boards)

    return DrawerModel(
        boards=boards,
        max_travel=float(slide_cfg.get('travel_mm', nl)),
        slide_model=slide_model_id,
        slide_nl=nl,
        joints=joints,
        drawer_count=0,
    )
