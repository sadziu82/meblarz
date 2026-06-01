"""
Dresser (chest of drawers) geometry calculations.
Input: external carcass dimensions + drawer parameters from YAML.
Output: DrawerModel with all boards (carcass + drawers).
"""

from pathlib import Path
from typing import List, Tuple
import yaml

from parts.drawer import (
    Board, Hole, JointHole, DrawerModel,
    _build_drawer, _shift_boards, _center_model,
    _joint_positions, _select_nl, _load_slides_db,
)

JH = JointHole


# ── Height modes ──────────────────────────────────────────────────────────────

def _parse_height_mode(raw) -> str:
    """Normalise height_mode to 'front' | 'niche' | 'interior'."""
    if raw in (1, '1', 'niche'):
        return 'niche'
    if raw in (2, '2', 'interior'):
        return 'interior'
    return 'front'


def height_to_front_H(h: float, mode: str, top_gap: float, bot_gap: float) -> float:
    """
    Convert a given drawer height to front height.

    Modes:
      'front'    — h is the front height (no conversion)
      'niche'    — h is the niche height (niche_H = bot_gap + front_H + top_gap)
      'interior' — h is the max contents height (= side_H = round(2/3 × front_H));
                   returns the minimum front_H yielding side_H >= h
    """
    if mode == 'niche':
        fh = h - top_gap - bot_gap
        if fh <= 0:
            raise ValueError(
                f"Niche height {h}mm too small — "
                f"top_gap({top_gap})+bot_gap({bot_gap})={top_gap+bot_gap}mm"
            )
        return fh
    if mode == 'interior':
        return (3 * int(h)) // 2
    return h


# ── Colours ───────────────────────────────────────────────────────────────────

_C_CARCASS = (0.82, 0.67, 0.47, 1.0)
_C_PLINTH  = (0.72, 0.57, 0.38, 1.0)
_C_RAIL    = (0.65, 0.50, 0.33, 1.0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rename_drawer(boards: list[Board],
                   joints: list[tuple[str, str]],
                   prefix: str) -> tuple[list[Board], list[tuple[str, str]]]:
    """Add prefix to drawer board names and update partner references."""
    name_map = {b.name: f"{prefix}{b.name}" for b in boards}
    renamed = []
    for b in boards:
        renamed.append(Board(
            name=name_map[b.name],
            width=b.width, height=b.height, depth=b.depth,
            pos=b.pos, color=b.color,
            holes=list(b.holes),
            joint_holes=[
                JointHole(jh.x, jh.y, jh.z, jh.direction, jh.element,
                          name_map.get(jh.partner, jh.partner), jh.hole_type)
                for jh in b.joint_holes
            ],
            movable=b.movable,
            move_fraction=b.move_fraction,
        ))
    renamed_joints = [(name_map[a], name_map[b]) for a, b in joints]
    return renamed, renamed_joints


def _carcass_joint_positions(depth: float) -> list[float]:
    """Joint positions for top/bottom ↔ side along depth (Y axis)."""
    return _joint_positions(0, depth)


def _rail_joint_positions(rail_depth: float) -> list[float]:
    """Joint positions for rail ↔ side along rail depth."""
    max_from = rail_depth * 0.25
    return _joint_positions(0, rail_depth, max_from_end=max_from)


# ── Main function ─────────────────────────────────────────────────────────────

def load_dresser(path: str) -> DrawerModel:
    with open(path) as f:
        cfg = yaml.safe_load(f)

    # ── Input parameters ──────────────────────────────────────────────────────
    carcass_w = cfg['carcass']['width']
    carcass_h = cfg['carcass']['height']
    carcass_d = cfg['carcass']['depth']
    placement = cfg['carcass'].get('placement', 'freestanding')

    thick   = cfg['material']['thickness']
    d_thick = cfg['material']['drawer_thickness']
    d_bot   = cfg['material']['drawer_bottom']

    plinth_h = cfg['plinth']['height']
    p_front  = cfg['plinth']['inset_front']
    p_side   = cfg['plinth']['inset_side']

    r_depth = cfg['rail']['depth']
    r_thick = cfg['rail']['thickness']

    n_drawers   = cfg['drawers']['count']
    distrib     = cfg['drawers'].get('distribution', 'equal')
    height_mode = _parse_height_mode(cfg['drawers'].get('height_mode', 'front'))

    slide_id  = cfg['slides']['model']
    target_nl = cfg['slides'].get('nl', None)
    db = _load_slides_db()
    if slide_id not in db:
        raise ValueError(f"Unknown slide model: '{slide_id}'. Available: {list(db)}")
    slide_cfg = db[slide_id]

    inset    = cfg['front']['inset']
    side_gap = cfg['front']['side_gap']
    bot_gap  = cfg['front']['bottom_gap']
    top_gap  = cfg['front']['top_gap']

    # ── Interior dimensions ───────────────────────────────────────────────────
    interior_W = carcass_w - 2 * thick
    interior_H = (carcass_h - plinth_h) - 2 * thick
    interior_D = carcass_d

    # ── Front heights ─────────────────────────────────────────────────────────
    available_for_fronts = interior_H - (n_drawers - 1) * r_thick - n_drawers * (bot_gap + top_gap)

    if distrib == 'custom':
        given_raw = list(cfg['drawers']['heights'])
        if len(given_raw) > n_drawers:
            raise ValueError(
                f"drawers.heights: {len(given_raw)} values provided but drawers.count={n_drawers}"
            )
        given = [height_to_front_H(h, height_mode, top_gap, bot_gap) for h in given_raw]

        if len(given) < n_drawers:
            remaining_count = n_drawers - len(given)
            available_remaining = available_for_fronts - sum(given)
            if available_remaining <= 0:
                raise ValueError(
                    f"Given heights ({sum(given)}mm front_H) exceed available "
                    f"height ({available_for_fronts:.1f}mm)"
                )
            base_H = int(available_remaining // remaining_count)
            rem    = int(round(available_remaining - remaining_count * base_H))
            extra  = [base_H] * remaining_count
            extra[0] += rem
            front_heights = given + extra
        else:
            front_heights = given
    else:
        base_H = int(available_for_fronts // n_drawers)
        remainder = int(round(available_for_fronts - n_drawers * base_H))
        front_heights = [base_H] * n_drawers
        front_heights[0] += remainder   # excess goes to the lowest drawer

    # ── Z positions (from plinth bottom) ─────────────────────────────────────
    z_plinth_top = plinth_h
    z_int_bottom = plinth_h + thick

    def niche_z(i: int) -> float:
        """Z position of the niche for drawer i (0 = bottom-most)."""
        z = z_int_bottom
        for j in range(i):
            z += bot_gap + front_heights[j] + top_gap + r_thick
        return z

    rail_z = [niche_z(i) + bot_gap + front_heights[i] + top_gap
              for i in range(n_drawers - 1)]

    # ── Joint types ───────────────────────────────────────────────────────────
    # Visible sides → dowels; hidden sides → confirmats (rules 57-58)
    left_visible  = placement in ('freestanding', 'builtin_right')
    right_visible = placement in ('freestanding', 'builtin_left')

    def joint_type(side: str) -> str:
        visible = left_visible if side == 'left' else right_visible
        return 'dowel' if visible else 'confirmat'

    # ── Build boards ──────────────────────────────────────────────────────────
    all_boards: list[Board] = []
    all_joints: list[tuple[str, str]] = []

    # ─ Plinth ────────────────────────────────────────────────────────────────
    if plinth_h > 0:
        plinth_boards = [
            Board('plinth_front',
                  width=carcass_w - 2 * p_side, height=plinth_h, depth=thick,
                  pos=(p_side, p_front, 0),
                  color=_C_PLINTH, movable=False),
            Board('plinth_left',
                  width=thick, height=plinth_h, depth=carcass_d - p_front - thick,
                  pos=(p_side, p_front + thick, 0),
                  color=_C_PLINTH, movable=False),
            Board('plinth_right',
                  width=thick, height=plinth_h, depth=carcass_d - p_front - thick,
                  pos=(carcass_w - p_side - thick, p_front + thick, 0),
                  color=_C_PLINTH, movable=False),
        ]
        all_boards.extend(plinth_boards)

    # ─ Carcass ────────────────────────────────────────────────────────────────
    top_split = cfg['carcass'].get('top_split', None)
    if top_split is not None:
        ts_front = top_split['front']
        ts_rear  = top_split['rear']
        ts_gap   = carcass_d - ts_front - ts_rear
        if ts_gap < 0:
            raise ValueError(
                f"carcass.top_split.front ({ts_front}mm) + rear ({ts_rear}mm) "
                f"exceeds carcass.depth ({carcass_d}mm)"
            )

    carcass_btm = Board('carcass_bottom',
                        width=carcass_w, height=thick, depth=carcass_d,
                        pos=(0, 0, z_plinth_top),
                        color=_C_CARCASS, movable=False)

    if top_split is None:
        _top = Board('carcass_top',
                     width=carcass_w, height=thick, depth=carcass_d,
                     pos=(0, 0, carcass_h - thick),
                     color=_C_CARCASS, movable=False)
        top_boards    = [_top]
        top_sections  = [(_top, 0, carcass_d)]  # (board, y_start, section_depth)
    else:
        _top_f = Board('carcass_top_front',
                       width=carcass_w, height=thick, depth=ts_front,
                       pos=(0, 0, carcass_h - thick),
                       color=_C_CARCASS, movable=False)
        _top_r = Board('carcass_top_rear',
                       width=carcass_w, height=thick, depth=ts_rear,
                       pos=(0, carcass_d - ts_rear, carcass_h - thick),
                       color=_C_CARCASS, movable=False)
        top_boards   = [_top_f, _top_r]
        top_sections = [(_top_f, 0, ts_front), (_top_r, carcass_d - ts_rear, ts_rear)]

    side_l = Board('carcass_left_side',
                   width=thick, height=interior_H, depth=carcass_d,
                   pos=(0, 0, z_int_bottom),
                   color=_C_CARCASS, movable=False)
    side_r = Board('carcass_right_side',
                   width=thick, height=interior_H, depth=carcass_d,
                   pos=(carcass_w - thick, 0, z_int_bottom),
                   color=_C_CARCASS, movable=False)

    carcass_boards = [carcass_btm] + top_boards + [side_l, side_r]

    # ─ Rails ─────────────────────────────────────────────────────────────────
    rail_boards = []
    for i, rz in enumerate(rail_z):
        rail_boards.append(Board(
            name=f'rail_{i}',
            width=interior_W, height=r_thick, depth=r_depth,
            pos=(thick, 0, rz),
            color=_C_RAIL, movable=False,
        ))

    # ─ Carcass joints ─────────────────────────────────────────────────────────
    x_lc = thick / 2
    x_rc = carcass_w - thick / 2
    z_top_bottom = carcass_h - thick
    z_btm_top    = z_plinth_top + thick

    jt_l   = joint_type('left')
    jt_r   = joint_type('right')
    # dowel: top drilled from below (-z), bottom from above (+z)
    # confirmat: top from above (+z), bottom from below (-z)
    w_dir_l = '-z' if jt_l == 'dowel' else '+z'
    s_dir_l = '+z' if jt_l == 'dowel' else '-z'
    w_dir_r = '-z' if jt_r == 'dowel' else '+z'
    s_dir_r = '+z' if jt_r == 'dowel' else '-z'

    # Bottom: always spans full carcass depth
    for yp in _carcass_joint_positions(carcass_d):
        carcass_btm.joint_holes.append(JH(x_lc, yp, z_btm_top, s_dir_l, 1, 'carcass_left_side',  jt_l))
        side_l.joint_holes.append(     JH(x_lc, yp, z_btm_top, '-z',    2, 'carcass_bottom',     jt_l))
        carcass_btm.joint_holes.append(JH(x_rc, yp, z_btm_top, s_dir_r, 1, 'carcass_right_side', jt_r))
        side_r.joint_holes.append(     JH(x_rc, yp, z_btm_top, '-z',    2, 'carcass_bottom',     jt_r))
    all_joints += [('carcass_bottom', 'carcass_left_side'), ('carcass_bottom', 'carcass_right_side')]

    # Top: one section or two (front + rear) when top_split is set
    for top_board, y_start, section_depth in top_sections:
        for yp in _joint_positions(y_start, section_depth):
            top_board.joint_holes.append(JH(x_lc, yp, z_top_bottom, w_dir_l, 1, 'carcass_left_side',  jt_l))
            side_l.joint_holes.append(   JH(x_lc, yp, z_top_bottom, '+z',    2, top_board.name,       jt_l))
            top_board.joint_holes.append(JH(x_rc, yp, z_top_bottom, w_dir_r, 1, 'carcass_right_side', jt_r))
            side_r.joint_holes.append(   JH(x_rc, yp, z_top_bottom, '+z',    2, top_board.name,       jt_r))
        all_joints += [(top_board.name, 'carcass_left_side'), (top_board.name, 'carcass_right_side')]

    # ─ Rail joints ────────────────────────────────────────────────────────────
    r_y_pos = _rail_joint_positions(r_depth)

    for i, rail in enumerate(rail_boards):
        rz_center = rail.pos[2] + r_thick / 2
        for yp in r_y_pos:
            jt_l = joint_type('left')
            # visible side (dowel): el=1 from inner face; hidden (confirmat): from outer face
            x_l1   = thick if jt_l == 'dowel' else 0
            dir_l1 = '+x'  if jt_l == 'dowel' else '-x'
            side_l.joint_holes.append(JH(x_l1,           yp, rz_center, dir_l1, 1, f'rail_{i}',           jt_l))
            rail.joint_holes.append(  JH(thick,           yp, rz_center, '-x',   2, 'carcass_left_side',   jt_l))

            jt_r = joint_type('right')
            x_r1   = carcass_w - thick if jt_r == 'dowel' else carcass_w
            dir_r1 = '-x'              if jt_r == 'dowel' else '+x'
            side_r.joint_holes.append(JH(x_r1,            yp, rz_center, dir_r1, 1, f'rail_{i}',           jt_r))
            rail.joint_holes.append(  JH(carcass_w-thick, yp, rz_center, '+x',   2, 'carcass_right_side',  jt_r))

        all_joints += [(f'rail_{i}', 'carcass_left_side'), (f'rail_{i}', 'carcass_right_side')]

    all_boards.extend(carcass_boards)
    all_boards.extend(rail_boards)

    # ─ Drawers ────────────────────────────────────────────────────────────────
    nl_used = 0
    for i in range(n_drawers):
        drawer_boards, drawer_joints, nl = _build_drawer(
            nw=interior_W,
            front_H=front_heights[i],
            nd=interior_D,
            mdf=d_thick,
            bot=d_bot,
            slide_cfg=slide_cfg,
            inset=inset,
            side_gap=side_gap,
            bot_gap=bot_gap,
            target_nl=target_nl,
        )
        nl_used = nl

        for b in drawer_boards:
            b.movable = True

        # Shift to niche position inside carcass
        drawer_boards = _shift_boards(drawer_boards, thick, 0, niche_z(i))

        prefix = f'drawer_{i}_'
        drawer_boards, drawer_joints = _rename_drawer(drawer_boards, drawer_joints, prefix)

        # ── Carcass slide mounting holes (same Y/Z as the drawer box holes) ──
        mount = slide_cfg['inner_drawer_mount']
        carcass_diam  = mount['carcass_hole_diameter_mm']
        carcass_depth = mount['hole_depth_mm']
        for b in drawer_boards:
            if b.name == f'{prefix}side_left':
                for h in b.holes:
                    side_l.holes.append(Hole(
                        x=thick, y=h.y, z=h.z,
                        diameter=carcass_diam, depth=carcass_depth,
                        direction='+x',  # inner face of left carcass side
                    ))
                    side_r.holes.append(Hole(
                        x=carcass_w - thick, y=h.y, z=h.z,
                        diameter=carcass_diam, depth=carcass_depth,
                        direction='-x',  # inner face of right carcass side
                    ))
                break

        all_boards.extend(drawer_boards)
        all_joints.extend(drawer_joints)

    # ─ Centre model ───────────────────────────────────────────────────────────
    all_boards = _center_model(all_boards)

    return DrawerModel(
        boards=all_boards,
        max_travel=float(nl_used),
        slide_model=slide_id,
        slide_nl=nl_used,
        joints=all_joints,
        drawer_count=n_drawers,
    )


# Keep backward-compatible alias used by viewer.py
load_komoda = load_dresser
