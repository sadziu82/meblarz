"""
Obliczenia geometrii szafki (komody) z szufladami wewnętrznymi.
Wejście: wymiary zewnętrzne korpusu + parametry szuflad z YAML.
Wyjście: DrawerModel ze wszystkimi elementami (korpus + szuflady).
"""

from pathlib import Path
from typing import List, Tuple
import yaml

from elementy.szuflada import (
    Board, Hole, JointHole, DrawerModel,
    _build_drawer, _shift_boards, _center_model,
    _joint_positions, _select_nl, _load_slides_db,
)

JH = JointHole


# ── Tryby wysokości ───────────────────────────────────────────────────────────

def _parse_height_mode(raw) -> str:
    """Normalizuje height_mode do 'front' | 'niche' | 'interior'."""
    if raw in (1, '1', 'niche'):
        return 'niche'
    if raw in (2, '2', 'interior'):
        return 'interior'
    return 'front'


def height_to_front_H(h: float, mode: str, top_gap: float, bot_gap: float) -> float:
    """
    Przelicza podaną wysokość szuflady na wysokość frontu.

    Tryby:
      'front'    — h to wysokość frontu (bez przeliczenia)
      'niche'    — h to wysokość wnęki (niche_H = bot_gap + front_H + top_gap)
      'interior' — h to max wysokość zawartości (= side_H = round(2/3 × front_H));
                   zwraca minimalne front_H dające side_H ≥ h
    """
    if mode == 'niche':
        fh = h - top_gap - bot_gap
        if fh <= 0:
            raise ValueError(
                f"Wysokość wnęki {h}mm za mała — "
                f"top_gap({top_gap})+bot_gap({bot_gap})={top_gap+bot_gap}mm"
            )
        return fh
    if mode == 'interior':
        # Najmniejszy front_H taki że round(2/3 * front_H) >= h
        # Wzór: (3*h) // 2  (wyprowadzony z warunku round(2/3*fH) >= h)
        return (3 * int(h)) // 2
    return h   # 'front' — bez przeliczenia


# ── Kolory ────────────────────────────────────────────────────────────────────

_C_CORPUS   = (0.82, 0.67, 0.47, 1.0)
_C_PLINTH   = (0.72, 0.57, 0.38, 1.0)
_C_RAIL     = (0.65, 0.50, 0.33, 1.0)


# ── Pomocnicze ────────────────────────────────────────────────────────────────

def _rename_drawer(boards: list[Board],
                   joints: list[tuple[str, str]],
                   prefix: str) -> tuple[list[Board], list[tuple[str, str]]]:
    """Dodaje prefix do nazw desek szuflady i aktualizuje referencje partner."""
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
        ))
    renamed_joints = [(name_map[a], name_map[b]) for a, b in joints]
    return renamed, renamed_joints


def _corpus_joint_positions(depth: float) -> list[float]:
    """Pozycje połączeń wierzch/spód ↔ bok wzdłuż głębokości (oś Y)."""
    return _joint_positions(0, depth)


def _rail_joint_positions(rail_depth: float) -> list[float]:
    """Pozycje połączeń poprzeczka ↔ bok wzdłuż głębokości poprzeczki."""
    max_from = rail_depth * 0.25
    return _joint_positions(0, rail_depth, max_from_end=max_from)


# ── Główna funkcja ────────────────────────────────────────────────────────────

def load_komoda(path: str) -> DrawerModel:
    with open(path) as f:
        cfg = yaml.safe_load(f)

    # ── Parametry wejściowe ───────────────────────────────────────────────────
    cw = cfg['carcass']['width']
    ch = cfg['carcass']['height']
    cd = cfg['carcass']['depth']
    placement = cfg['carcass'].get('placement', 'freestanding')

    thick   = cfg['material']['thickness']
    d_thick = cfg['material']['drawer_thickness']
    d_bot   = cfg['material']['drawer_bottom']

    ph      = cfg['plinth']['height']
    p_front = cfg['plinth']['inset_front']
    p_side  = cfg['plinth']['inset_side']

    r_depth = cfg['rail']['depth']
    r_thick = cfg['rail']['thickness']

    n_draw      = cfg['drawers']['count']
    distrib     = cfg['drawers'].get('distribution', 'equal')
    height_mode = _parse_height_mode(cfg['drawers'].get('height_mode', 'front'))

    slide_id = cfg['slides']['model']
    db = _load_slides_db()
    if slide_id not in db:
        raise ValueError(f"Nieznany model prowadnicy: '{slide_id}'. Dostępne: {list(db)}")
    slide_cfg = db[slide_id]

    inset    = cfg['front']['inset']
    side_gap = cfg['front']['side_gap']
    bot_gap  = cfg['front']['bottom_gap']
    top_gap  = cfg['front']['top_gap']

    # ── Wymiary wewnętrzne ────────────────────────────────────────────────────
    # carcass.height = całkowita wysokość mebla wliczając cokoł
    int_W = cw - 2 * thick          # szerokość wewnętrzna
    int_H = (ch - ph) - 2 * thick  # wysokość wewnętrzna (korpus bez cokołu)
    int_D = cd                      # głębokość (tył otwarty)

    # ── Wysokości frontów ─────────────────────────────────────────────────────
    # int_H = count*(bot_gap + front_H + top_gap) + (count-1)*rail_thick
    available_for_fronts = int_H - (n_draw - 1) * r_thick - n_draw * (bot_gap + top_gap)

    if distrib == 'custom':
        given_raw = list(cfg['drawers']['heights'])
        if len(given_raw) > n_draw:
            raise ValueError(
                f"drawers.heights: podano {len(given_raw)} wartości, ale drawers.count={n_draw}"
            )
        # Przelicz podane wysokości na front_H zgodnie z trybem
        given = [height_to_front_H(h, height_mode, top_gap, bot_gap) for h in given_raw]

        if len(given) < n_draw:
            # Oblicz brakujące szuflady (od góry) jako równy podział reszty (zawsze front_H)
            remaining_count = n_draw - len(given)
            available_remaining = available_for_fronts - sum(given)
            if available_remaining <= 0:
                raise ValueError(
                    f"Podane wysokości ({sum(given)}mm front_H) przekraczają dostępną "
                    f"wysokość ({available_for_fronts:.1f}mm)"
                )
            base_H = int(available_remaining // remaining_count)
            rem    = int(round(available_remaining - remaining_count * base_H))
            extra  = [base_H] * remaining_count
            extra[0] += rem   # nadmiar do najniższej z wyliczonych
            front_heights = given + extra
        else:
            front_heights = given
    else:
        base_H = int(available_for_fronts // n_draw)
        remainder = int(round(available_for_fronts - n_draw * base_H))
        # nadmiar dodajemy do najniższej szuflady
        front_heights = [base_H] * n_draw
        front_heights[0] += remainder  # indeks 0 = najniższa szuflada

    # ── Z-pozycje elementów (od dołu cokołu) ─────────────────────────────────
    z_plinth_top  = ph            # spód korpusu
    z_int_bottom  = ph + thick    # dno wnętrza

    # Pozycja Z niszy i-tej szuflady (liczone od dołu, i=0 = najniższa)
    def niche_z(i: int) -> float:
        z = z_int_bottom
        for j in range(i):
            z += bot_gap + front_heights[j] + top_gap + r_thick
        return z

    rail_z = [niche_z(i) + bot_gap + front_heights[i] + top_gap
              for i in range(n_draw - 1)]

    # ── Typ połączeń ──────────────────────────────────────────────────────────
    # placement decyduje o widoczności boków → typ złącza (reguła 57-58)
    left_visible  = placement in ('freestanding', 'builtin_right')
    right_visible = placement in ('freestanding', 'builtin_left')

    def joint_type(side: str) -> str:
        visible = left_visible if side == 'left' else right_visible
        return 'dowel' if visible else 'confirmat'

    # ── Budowa desek ──────────────────────────────────────────────────────────
    all_boards: list[Board] = []
    all_joints: list[tuple[str, str]] = []

    # ─ Cokoł ─────────────────────────────────────────────────────────────────
    if ph > 0:
        plinth_boards = [
            Board('plinth_front',
                  width=cw - 2 * p_side, height=ph, depth=thick,
                  pos=(p_side, p_front, 0),
                  color=_C_PLINTH, movable=False),
            Board('plinth_left',
                  width=thick, height=ph, depth=cd - p_front - thick,
                  pos=(p_side, p_front + thick, 0),
                  color=_C_PLINTH, movable=False),
            Board('plinth_right',
                  width=thick, height=ph, depth=cd - p_front - thick,
                  pos=(cw - p_side - thick, p_front + thick, 0),
                  color=_C_PLINTH, movable=False),
        ]
        all_boards.extend(plinth_boards)

    # ─ Korpus ─────────────────────────────────────────────────────────────────
    spod = Board('corpus_spod',
                 width=cw, height=thick, depth=cd,
                 pos=(0, 0, z_plinth_top),
                 color=_C_CORPUS, movable=False)
    wierzch = Board('corpus_wierzch',
                    width=cw, height=thick, depth=cd,
                    pos=(0, 0, ch - thick),
                    color=_C_CORPUS, movable=False)
    bok_l = Board('corpus_bok_lewy',
                  width=thick, height=int_H, depth=cd,
                  pos=(0, 0, z_int_bottom),
                  color=_C_CORPUS, movable=False)
    bok_r = Board('corpus_bok_prawy',
                  width=thick, height=int_H, depth=cd,
                  pos=(cw - thick, 0, z_int_bottom),
                  color=_C_CORPUS, movable=False)

    corpus_boards = [spod, wierzch, bok_l, bok_r]

    # ─ Poprzeczki ─────────────────────────────────────────────────────────────
    rail_boards = []
    for i, rz in enumerate(rail_z):
        rail_boards.append(Board(
            name=f'rail_{i}',
            width=int_W, height=r_thick, depth=r_depth,
            pos=(thick, 0, rz),
            color=_C_RAIL, movable=False,
        ))

    # ─ Połączenia korpusu ─────────────────────────────────────────────────────
    y_pos = _corpus_joint_positions(cd)   # pozycje wzdłuż Y (głębokość)

    x_bl = thick / 2             # środek lewego boku w X
    x_br = cw - thick / 2       # środek prawego boku w X

    z_wierzch_bottom = ch - thick          # spodnia ściana wierzchu
    z_spod_top       = z_plinth_top + thick  # górna ściana spodu

    for yp in y_pos:
        # Kierunek zależy od typu połączenia:
        # - kołek (dowel): element 1 w płaszczyźnie poziomej (wierzch od dołu '-z', spód od góry '+z')
        # - konfirmat: łeb na powierzchni zewnętrznej (wierzch od góry '+z', spód od dołu '-z')
        jt_l = joint_type('left')
        w_dir = '-z' if jt_l == 'dowel' else '+z'   # wierzch: kołek od dołu / konfirmat od góry
        s_dir = '+z' if jt_l == 'dowel' else '-z'   # spód:    kołek od góry / konfirmat od dołu
        wierzch.joint_holes.append(JH(x_bl, yp, z_wierzch_bottom, w_dir, 1, 'corpus_bok_lewy', jt_l))
        bok_l.joint_holes.append(  JH(x_bl, yp, z_wierzch_bottom, '+z',  2, 'corpus_wierzch',  jt_l))
        spod.joint_holes.append(   JH(x_bl, yp, z_spod_top,       s_dir, 1, 'corpus_bok_lewy', jt_l))
        bok_l.joint_holes.append(  JH(x_bl, yp, z_spod_top,       '-z',  2, 'corpus_spod',     jt_l))

        jt_r = joint_type('right')
        w_dir = '-z' if jt_r == 'dowel' else '+z'
        s_dir = '+z' if jt_r == 'dowel' else '-z'
        wierzch.joint_holes.append(JH(x_br, yp, z_wierzch_bottom, w_dir, 1, 'corpus_bok_prawy', jt_r))
        bok_r.joint_holes.append(  JH(x_br, yp, z_wierzch_bottom, '+z',  2, 'corpus_wierzch',   jt_r))
        spod.joint_holes.append(   JH(x_br, yp, z_spod_top,       s_dir, 1, 'corpus_bok_prawy', jt_r))
        bok_r.joint_holes.append(  JH(x_br, yp, z_spod_top,       '-z',  2, 'corpus_spod',      jt_r))

    all_joints += [
        ('corpus_wierzch', 'corpus_bok_lewy'),
        ('corpus_wierzch', 'corpus_bok_prawy'),
        ('corpus_spod',    'corpus_bok_lewy'),
        ('corpus_spod',    'corpus_bok_prawy'),
    ]

    # ─ Połączenia poprzeczek ──────────────────────────────────────────────────
    r_y_pos = _rail_joint_positions(r_depth)   # pozycje wzdłuż Y

    for i, rail in enumerate(rail_boards):
        rz_center = rail.pos[2] + r_thick / 2
        for yp in r_y_pos:
            jt_l = joint_type('left')
            # Bok widoczny (dowel) → el=1 od ściany wewnętrznej (ukryta).
            # Bok niewidoczny (confirmat) → el=1 od ściany zewnętrznej (przy ścianie budynku).
            x_l1   = thick if jt_l == 'dowel' else 0
            dir_l1 = '+x'  if jt_l == 'dowel' else '-x'
            bok_l.joint_holes.append(JH(x_l1,    yp, rz_center, dir_l1, 1, f'rail_{i}', jt_l))
            rail.joint_holes.append( JH(thick,   yp, rz_center, '-x',   2, 'corpus_bok_lewy', jt_l))

            jt_r = joint_type('right')
            x_r1   = cw - thick if jt_r == 'dowel' else cw
            dir_r1 = '-x'       if jt_r == 'dowel' else '+x'
            bok_r.joint_holes.append(JH(x_r1,    yp, rz_center, dir_r1, 1, f'rail_{i}', jt_r))
            rail.joint_holes.append( JH(cw-thick, yp, rz_center, '+x',  2, 'corpus_bok_prawy', jt_r))

        all_joints += [(f'rail_{i}', 'corpus_bok_lewy'), (f'rail_{i}', 'corpus_bok_prawy')]

    all_boards.extend(corpus_boards)
    all_boards.extend(rail_boards)

    # ─ Szuflady ───────────────────────────────────────────────────────────────
    nl_used = 0
    for i in range(n_draw):
        drawer_boards, drawer_joints, nl = _build_drawer(
            nw=int_W,
            front_H=front_heights[i],
            nd=int_D,
            mdf=d_thick,
            bot=d_bot,
            slide_cfg=slide_cfg,
            inset=inset,
            side_gap=side_gap,
            bot_gap=bot_gap,
        )
        nl_used = nl

        # Wszystkie deski szuflady są ruchome
        for b in drawer_boards:
            b.movable = True

        # Przesuń do pozycji niszy w korpusie
        # Nisza X: thick (wewnętrzna krawędź lewego boku)
        # Nisza Y: 0 (front face korpusu)
        # Nisza Z: niche_z(i)
        offset_x = thick
        offset_z = niche_z(i)
        drawer_boards = _shift_boards(drawer_boards, offset_x, 0, offset_z)

        # Zmień nazwy na drawer_{i}_*
        prefix = f'drawer_{i}_'
        drawer_boards, drawer_joints = _rename_drawer(drawer_boards, drawer_joints, prefix)

        all_boards.extend(drawer_boards)
        all_joints.extend(drawer_joints)

    # ─ Wyśrodkuj cały model ───────────────────────────────────────────────────
    all_boards = _center_model(all_boards)

    return DrawerModel(
        boards=all_boards,
        max_travel=float(nl_used),
        slide_model=slide_id,
        slide_nl=nl_used,
        joints=all_joints,
        drawer_count=n_draw,
    )
