"""
Unit tests for dresser (chest of drawers).
Verifies rules 54–66 from design_rules.md.
"""
from pathlib import Path
import pytest

from parts.dresser import load_dresser, height_to_front_H

YAML_PATH = str(Path(__file__).parent.parent / 'projects' / 'dresser.yaml')

# ── Parameters from dresser.yaml ────────────────────────────────────────────────────
CW, CH, CD  = 410, 2070, 1100
THICK       = 18
D_THICK     = 18
D_BOT       = 18
PH          = 170   # plinth height
P_FRONT     = 450
P_SIDE      = 0
PLACEMENT   = 'builtin_both'
R_DEPTH     = 100
R_THICK     = 18
N_DRAW      = 5
INSET       = 1.5
SIDE_GAP    = 3
BOT_GAP     = 3
TOP_GAP     = 50

INT_W = CW - 2 * THICK            # 374
INT_H = (CH - PH) - 2 * THICK    # (2070-170) - 36 = 1864  — korpus bez cokołu
INT_D = CD                        # 1100

# front_H: custom distribution [380,380,180] + 2 wyliczone równo
_avail         = INT_H - (N_DRAW - 1) * R_THICK - N_DRAW * (BOT_GAP + TOP_GAP)  # 1527
_GIVEN         = [380, 380, 180]
_rem_count     = N_DRAW - len(_GIVEN)               # 2
_rem_avail     = _avail - sum(_GIVEN)               # 587
_base          = int(_rem_avail // _rem_count)       # 293
_extra_rem     = int(round(_rem_avail - _rem_count * _base))  # 1
_extra         = [_base + _extra_rem] + [_base] * (_rem_count - 1)  # [294, 293]
FRONT_HEIGHTS  = _GIVEN + _extra                    # [380,380,180,294,293]


@pytest.fixture(scope='module')
def model():
    return load_dresser(YAML_PATH)


@pytest.fixture(scope='module')
def bd(model):
    return {b.name: b for b in model.boards}


# ══════════════════════════════════════════════════════════════════════════════
# Liczba elementów i flagi movable (reguła 54)
# ══════════════════════════════════════════════════════════════════════════════

class TestBoardInventory:

    def test_total_board_count(self, model):
        """3 cokoł + 4 korpus + (N-1) poprzeczki + N×5 szuflady."""
        expected = 3 + 4 + (N_DRAW - 1) + N_DRAW * 5
        assert len(model.boards) == expected

    def test_drawer_count(self, model):
        assert model.drawer_count == N_DRAW

    def test_carcass_boards_not_movable(self, bd):
        """Deski korpusu, cokołu i poprzeczek są nieruchome."""
        fixed = (['carcass_top', 'carcass_bottom', 'carcass_left_side', 'carcass_right_side',
                  'plinth_front', 'plinth_left', 'plinth_right']
                 + [f'rail_{i}' for i in range(N_DRAW - 1)])
        for name in fixed:
            assert not bd[name].movable, f"{name} powinien mieć movable=False"

    def test_drawer_boards_movable(self, bd):
        """Deski szuflad są ruchome."""
        for i in range(N_DRAW):
            for part in ('front', 'bottom', 'side_left', 'side_right', 'rear'):
                name = f'drawer_{i}_{part}'
                assert bd[name].movable, f"{name} powinien mieć movable=True"

    def test_rail_count(self, model):
        """Liczba poprzeczek = drawers.count − 1 (reguła 60)."""
        rails = [b for b in model.boards if b.name.startswith('rail_')]
        assert len(rails) == N_DRAW - 1


# ══════════════════════════════════════════════════════════════════════════════
# Wymiary korpusu (reguła 54)
# ══════════════════════════════════════════════════════════════════════════════

class TestCarcassDimensions:

    def test_carcass_top_full_width(self, bd):
        """Wierzch ma pełną szerokość zewnętrzną (reguła 54)."""
        assert bd['carcass_top'].width == pytest.approx(CW)

    def test_carcass_bottom_full_width(self, bd):
        """Spód ma pełną szerokość zewnętrzną (reguła 54)."""
        assert bd['carcass_bottom'].width == pytest.approx(CW)

    def test_carcass_top_bottom_depth(self, bd):
        """Wierzch i spód mają pełną głębokość."""
        assert bd['carcass_top'].depth == pytest.approx(CD)
        assert bd['carcass_bottom'].depth    == pytest.approx(CD)

    def test_carcass_top_bottom_thickness(self, bd):
        """Wierzch i spód mają grubość MDF=18mm."""
        assert bd['carcass_top'].height == pytest.approx(THICK)
        assert bd['carcass_bottom'].height    == pytest.approx(THICK)

    def test_side_height_equals_interior_H(self, bd):
        """Boki mają wysokość = int_H = height − 2×thick (reguła 54)."""
        assert bd['carcass_left_side'].height  == pytest.approx(INT_H)
        assert bd['carcass_right_side'].height == pytest.approx(INT_H)

    def test_side_width_equals_thickness(self, bd):
        assert bd['carcass_left_side'].width  == pytest.approx(THICK)
        assert bd['carcass_right_side'].width == pytest.approx(THICK)

    def test_side_full_depth(self, bd):
        assert bd['carcass_left_side'].depth  == pytest.approx(CD)
        assert bd['carcass_right_side'].depth == pytest.approx(CD)

    def test_sides_span_between_top_and_bottom(self, bd):
        """Boki mieszczą się dokładnie między spodem a wierzchem."""
        bok = bd['carcass_left_side']
        carcass_btm = bd['carcass_bottom']
        carcass_top = bd['carcass_top']
        assert bok.pos[2] == pytest.approx(carcass_btm.pos[2] + carcass_btm.height)
        assert bok.pos[2] + bok.height == pytest.approx(carcass_top.pos[2])

    def test_model_centered_at_origin(self, model):
        xs = [b.pos[0] for b in model.boards] + [b.pos[0]+b.width  for b in model.boards]
        ys = [b.pos[1] for b in model.boards] + [b.pos[1]+b.depth  for b in model.boards]
        zs = [b.pos[2] for b in model.boards] + [b.pos[2]+b.height for b in model.boards]
        assert (min(xs)+max(xs))/2 == pytest.approx(0)
        assert (min(ys)+max(ys))/2 == pytest.approx(0)
        assert min(zs) == pytest.approx(0)


# ══════════════════════════════════════════════════════════════════════════════
# Cokoł (reguły 65–66)
# ══════════════════════════════════════════════════════════════════════════════

class TestPlinth:

    def test_plinth_front_height(self, bd):
        assert bd['plinth_front'].height == pytest.approx(PH)

    def test_plinth_front_width(self, bd):
        """Szerokość deski przedniej = carcass.width − 2×inset_side (reguła 66)."""
        assert bd['plinth_front'].width == pytest.approx(CW - 2 * P_SIDE)

    def test_plinth_side_depth(self, bd):
        """Głębokość desek bocznych = depth − inset_front − thick (reguła 66)."""
        expected = CD - P_FRONT - THICK
        assert bd['plinth_left'].depth  == pytest.approx(expected)
        assert bd['plinth_right'].depth == pytest.approx(expected)

    def test_plinth_side_height(self, bd):
        assert bd['plinth_left'].height  == pytest.approx(PH)
        assert bd['plinth_right'].height == pytest.approx(PH)

    def test_carcass_bottom_sits_on_plinth(self, bd):
        """Spód korpusu zaczyna się na górze cokołu (reguła 65)."""
        carcass_btm = bd['carcass_bottom']
        plinth = bd['plinth_front']
        assert carcass_btm.pos[2] == pytest.approx(plinth.pos[2] + PH)


# ══════════════════════════════════════════════════════════════════════════════
# Poprzeczki (reguły 60, 63, 64)
# ══════════════════════════════════════════════════════════════════════════════

class TestRails:

    def test_rail_width_equals_int_W(self, bd):
        """Szerokość poprzeczki = int_W (reguła 60)."""
        for i in range(N_DRAW - 1):
            assert bd[f'rail_{i}'].width == pytest.approx(INT_W)

    def test_rail_depth(self, bd):
        """Głębokość poprzeczki = 100mm (reguła 64)."""
        for i in range(N_DRAW - 1):
            assert bd[f'rail_{i}'].depth == pytest.approx(R_DEPTH)

    def test_rail_thickness(self, bd):
        for i in range(N_DRAW - 1):
            assert bd[f'rail_{i}'].height == pytest.approx(R_THICK)

    def test_rails_inside_corpus(self, bd):
        """Poprzeczki zaczynają się na wewnętrznej krawędzi lewego boku."""
        side_l = bd['carcass_left_side']
        for i in range(N_DRAW - 1):
            rail = bd[f'rail_{i}']
            assert rail.pos[0] == pytest.approx(side_l.pos[0] + THICK)


# ══════════════════════════════════════════════════════════════════════════════
# Podział wysokości i sekwencja elementów (reguły 61, 62)
# ══════════════════════════════════════════════════════════════════════════════

class TestHeightDistribution:

    def test_front_heights_correct(self, bd):
        """Wysokości frontów zgodne z wyliczeniem równego podziału (reguła 62)."""
        for i in range(N_DRAW):
            name = f'drawer_{i}_front'
            assert bd[name].height == pytest.approx(FRONT_HEIGHTS[i]), (
                f"{name}: H={bd[name].height}, oczekiwano {FRONT_HEIGHTS[i]}"
            )

    def test_front_heights_sum(self, bd):
        """Suma frontów + odstępów + poprzeczki = int_H (reguła 62)."""
        total = sum(bd[f'drawer_{i}_front'].height for i in range(N_DRAW))
        total += N_DRAW * (BOT_GAP + TOP_GAP) + (N_DRAW - 1) * R_THICK
        assert total == pytest.approx(INT_H)

    def test_sequence_bottom_gap(self, bd):
        """Pod każdym frontem jest bot_gap=3mm (reguła 61)."""
        for i in range(N_DRAW):
            front = bd[f'drawer_{i}_front']
            if i == 0:
                # dno niszy = spód korpusu (górna ściana spodu)
                ref = bd['carcass_bottom']
                ref_top_z = ref.pos[2] + ref.height
            else:
                rail = bd[f'rail_{i-1}']
                ref_top_z = rail.pos[2] + rail.height
            gap = front.pos[2] - ref_top_z
            assert gap == pytest.approx(BOT_GAP), (
                f"drawer_{i}_front: przerwa dolna={gap}, oczekiwano {BOT_GAP}"
            )

    def test_sequence_top_gap(self, bd):
        """Nad każdym frontem jest top_gap=50mm (reguła 61)."""
        for i in range(N_DRAW):
            front = bd[f'drawer_{i}_front']
            front_top_z = front.pos[2] + front.height
            if i < N_DRAW - 1:
                rail = bd[f'rail_{i}']
                ref_z = rail.pos[2]
            else:
                # ostatnia szuflada → wierzch
                carcass_top = bd['carcass_top']
                ref_z = carcass_top.pos[2]
            gap = ref_z - front_top_z
            assert gap == pytest.approx(TOP_GAP), (
                f"drawer_{i}_front: przerwa górna={gap}, oczekiwano {TOP_GAP}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# Połączenia korpusu (reguły 57, 32)
# ══════════════════════════════════════════════════════════════════════════════

class TestCarcassJoints:

    def test_top_left_side_min_2_holes(self, bd):
        """Wierzch↔Bok lewy: min 2 otwory (reguła 32)."""
        holes = [jh for jh in bd['carcass_top'].joint_holes
                 if jh.partner == 'carcass_left_side']
        assert len(holes) >= 2

    def test_top_right_side_min_2_holes(self, bd):
        holes = [jh for jh in bd['carcass_top'].joint_holes
                 if jh.partner == 'carcass_right_side']
        assert len(holes) >= 2

    def test_bottom_side_min_2_holes(self, bd):
        for side in ('carcass_left_side', 'carcass_right_side'):
            holes = [jh for jh in bd['carcass_bottom'].joint_holes if jh.partner == side]
            assert len(holes) >= 2

    def test_top_drilling_direction(self, bd):
        """Wierzch element 1: kołek od spodu (-Z), konfirmat od góry (+Z) (reguła 57)."""
        expected_dir = '-z' if PLACEMENT == 'freestanding' else '+z'
        for jh in bd['carcass_top'].joint_holes:
            if jh.element == 1:
                assert jh.direction == expected_dir, (
                    f"carcass_top el=1: kierunek {jh.direction}, oczekiwano {expected_dir}"
                )

    def test_bottom_drilling_direction(self, bd):
        """Spód element 1: kołek od góry (+Z), konfirmat od dołu (-Z) (reguła 57)."""
        expected_dir = '+z' if PLACEMENT == 'freestanding' else '-z'
        for jh in bd['carcass_bottom'].joint_holes:
            if jh.element == 1:
                assert jh.direction == expected_dir, (
                    f"carcass_bottom el=1: kierunek {jh.direction}, oczekiwano {expected_dir}"
                )

    def test_carcass_joint_type_matches_placement(self, bd):
        """Typ połączeń wierzch/spód↔boki zgodny z placement (reguła 57, 55)."""
        expected = 'confirmat' if PLACEMENT == 'builtin_both' else 'dowel'
        for board_name in ('carcass_top', 'carcass_bottom'):
            for jh in bd[board_name].joint_holes:
                assert jh.hole_type == expected, (
                    f"{board_name}→{jh.partner}: oczekiwano {expected}, jest {jh.hole_type}"
                )

    def test_side_receives_holes_from_top_and_bottom(self, bd):
        """Bok lewy ma otwory element=2 od wierzchu i spodu."""
        side_l = bd['carcass_left_side']
        from_wierzch = [jh for jh in side_l.joint_holes if jh.partner == 'carcass_top']
        from_spod    = [jh for jh in side_l.joint_holes if jh.partner == 'carcass_bottom']
        assert len(from_wierzch) >= 2
        assert len(from_spod)    >= 2
        assert all(jh.element == 2 for jh in from_wierzch)
        assert all(jh.element == 2 for jh in from_spod)

    def test_carcass_joint_y_max_spacing(self, bd):
        """Otwory wierzch↔bok wzdłuż Y: max 300mm odstęp (reguła 36)."""
        holes = sorted(
            [jh for jh in bd['carcass_top'].joint_holes
             if jh.partner == 'carcass_left_side'],
            key=lambda jh: jh.y
        )
        for i in range(len(holes) - 1):
            assert holes[i+1].y - holes[i].y <= 300


# ══════════════════════════════════════════════════════════════════════════════
# Połączenia poprzeczek (reguła 58, 32)
# ══════════════════════════════════════════════════════════════════════════════

class TestRailJoints:

    def test_each_rail_has_min_2_holes_per_side(self, bd):
        """Każda poprzeczka ma min 2 otwory do każdego boku (reguła 32)."""
        for i in range(N_DRAW - 1):
            rail = bd[f'rail_{i}']
            left_holes  = [jh for jh in rail.joint_holes if jh.partner == 'carcass_left_side']
            right_holes = [jh for jh in rail.joint_holes if jh.partner == 'carcass_right_side']
            assert len(left_holes)  >= 2, f"rail_{i}↔bok_lewy: {len(left_holes)} otworów"
            assert len(right_holes) >= 2, f"rail_{i}↔bok_prawy: {len(right_holes)} otworów"

    def test_rail_holes_at_center_of_rail_thickness(self, bd):
        """Otwory poprzeczki na środku jej grubości w Z (reguła 42)."""
        for i in range(N_DRAW - 1):
            rail = bd[f'rail_{i}']
            for jh in rail.joint_holes:
                local_z = jh.z - rail.pos[2]
                assert local_z == pytest.approx(R_THICK / 2), (
                    f"rail_{i}: otwór Z={local_z}, oczekiwano {R_THICK/2}"
                )

    def test_rail_drilled_from_side_faces(self, bd):
        """Poprzeczka: otwory od czoła (-X lub +X) (reguła 58)."""
        for i in range(N_DRAW - 1):
            rail = bd[f'rail_{i}']
            for jh in rail.joint_holes:
                assert jh.direction in ('-x', '+x'), (
                    f"rail_{i}: kierunek {jh.direction}"
                )

    def test_rail_joint_type_matches_placement(self, bd):
        """Typ połączeń rail↔bok zgodny z placement (reguła 58, 55)."""
        expected = 'confirmat' if PLACEMENT == 'builtin_both' else 'dowel'
        for i in range(N_DRAW - 1):
            for jh in bd[f'rail_{i}'].joint_holes:
                assert jh.hole_type == expected


# ══════════════════════════════════════════════════════════════════════════════
# Szuflady wewnątrz komody (reguły 6, 10, 12–17, 18–23)
# ══════════════════════════════════════════════════════════════════════════════

class TestDrawers:

    def test_all_drawers_have_correct_box_width(self, bd):
        """Zewnętrzna szerokość skrzynki = int_W − 2×luz_boczny (reguła 13)."""
        # GTV-H45: luz_boczny=12.5
        slide_side = 12.5
        expected_box_W = INT_W - 2 * slide_side
        for i in range(N_DRAW):
            assert bd[f'drawer_{i}_bottom'].width == pytest.approx(expected_box_W), (
                f"drawer_{i}_bottom.width={bd[f'drawer_{i}_bottom'].width}"
            )

    def test_all_drawers_same_nl(self, model):
        """Wszystkie szuflady mają ten sam NL (ta sama głębokość wnęki)."""
        assert model.slide_nl > 0
        # Sprawdź przez głębokość dna
        for i in range(N_DRAW):
            bot = next(b for b in model.boards if b.name == f'drawer_{i}_bottom')
            assert bot.depth == pytest.approx(model.slide_nl)

    def test_drawer_fronts_not_wider_than_int_W(self, bd):
        """Front szuflady węższy niż int_W."""
        for i in range(N_DRAW):
            assert bd[f'drawer_{i}_front'].width < INT_W

    def test_drawer_side_height_two_thirds_front(self, bd):
        """Wysokość boków = round(2/3 × front_H) (reguła 6)."""
        for i in range(N_DRAW):
            fh = bd[f'drawer_{i}_front'].height
            sh = bd[f'drawer_{i}_side_left'].height
            assert sh == round(2/3 * fh)

    def test_drawer_box_starts_behind_front(self, bd):
        """Skrzynka zaczyna się za tylną ścianą frontu (reguła 10)."""
        for i in range(N_DRAW):
            front  = bd[f'drawer_{i}_front']
            bottom = bd[f'drawer_{i}_bottom']
            assert bottom.pos[1] == pytest.approx(front.pos[1] + front.depth)

    def test_drawer_front_joints_are_dowels(self, bd):
        """Front szuflady: kołki do boków i dna (reguła 18)."""
        for i in range(N_DRAW):
            front = bd[f'drawer_{i}_front']
            for jh in front.joint_holes:
                assert jh.hole_type == 'dowel', (
                    f"drawer_{i}_front→{jh.partner}: oczekiwano dowel"
                )

    def test_drawer_bottom_side_joints_are_confirmats(self, bd):
        """Dno↔Boki: konfirmaty (reguła 18)."""
        for i in range(N_DRAW):
            bottom = bd[f'drawer_{i}_bottom']
            for side in (f'drawer_{i}_side_left', f'drawer_{i}_side_right'):
                holes = [jh for jh in bottom.joint_holes if jh.partner == side]
                assert all(jh.hole_type == 'confirmat' for jh in holes)

    def test_drawer_front_holes_only_from_back(self, bd):
        """Otwory frontu tylko od tylnej ściany +Y (reguła 44, 45)."""
        for i in range(N_DRAW):
            for jh in bd[f'drawer_{i}_front'].joint_holes:
                assert jh.direction == '+y'

    def test_each_drawer_joint_min_2_holes(self, model, bd):
        """Każde połączenie wewnątrz szuflady min 2 otwory (reguła 32)."""
        for name_a, name_b in model.joints:
            if not (name_a.startswith('drawer_') and name_b.startswith('drawer_')):
                continue
            prefix_a = name_a.split('_', 2)[:2]
            prefix_b = name_b.split('_', 2)[:2]
            if prefix_a != prefix_b:
                continue  # połączenie między różnymi szufladami (nie istnieje)
            holes = [jh for jh in bd[name_a].joint_holes if jh.partner == name_b]
            assert len(holes) >= 2, f"{name_a}↔{name_b}: {len(holes)} otworów"


# ══════════════════════════════════════════════════════════════════════════════
# Prowadnice (reguła 29, 30)
# ══════════════════════════════════════════════════════════════════════════════

class TestSlides:

    def test_slide_model(self, model):
        assert model.slide_model == 'GTV-H45'

    def test_slide_mount_50mm_from_bottom(self, bd):
        """Otwory montażowe 50mm od spodu dna szuflady (reguła 29)."""
        for i in range(N_DRAW):
            bottom = bd[f'drawer_{i}_bottom']
            for side_name in (f'drawer_{i}_side_left', f'drawer_{i}_side_right'):
                side = bd[side_name]
                assert side.holes, f"{side_name}: brak otworów montażowych"
                for h in side.holes:
                    z_from_bottom = h.z - bottom.pos[2]
                    assert z_from_bottom == pytest.approx(50.0)


# ══════════════════════════════════════════════════════════════════════════════
# Tryby wysokości — height_to_front_H
# ══════════════════════════════════════════════════════════════════════════════

class TestHeightMode:

    TOP_GAP = 50
    BOT_GAP = 3

    def test_mode_front_passthrough(self):
        """Tryb 'front': wartość bez przeliczenia."""
        assert height_to_front_H(380, 'front', self.TOP_GAP, self.BOT_GAP) == 380
        assert height_to_front_H(100, 'front', self.TOP_GAP, self.BOT_GAP) == 100

    def test_mode_niche_subtracts_gaps(self):
        """Tryb 'niche': front_H = niche_H − top_gap − bot_gap."""
        assert height_to_front_H(380, 'niche', self.TOP_GAP, self.BOT_GAP) == pytest.approx(327)
        assert height_to_front_H(200, 'niche', 50, 3) == pytest.approx(147)

    def test_mode_niche_error_too_small(self):
        """Tryb 'niche': błąd gdy wnęka mniejsza niż sum przerw."""
        with pytest.raises(ValueError):
            height_to_front_H(50, 'niche', 50, 3)  # 50 <= 53

    def test_mode_interior_minimum_front(self):
        """Tryb 'interior': minimalne front_H dające side_H >= h."""
        # side_H = round(2/3 * front_H)
        for interior_h, expected_front in [
            (100, 150),   # round(2/3*150)=100 ✓
            (101, 151),   # round(2/3*151)=round(100.67)=101 ✓
            (200, 300),   # round(2/3*300)=200 ✓
            (201, 301),   # round(2/3*301)=round(200.67)=201 ✓
            (3,   4),     # round(2/3*4)=round(2.67)=3 ✓
            (10,  15),    # round(2/3*15)=10 ✓
        ]:
            result = height_to_front_H(interior_h, 'interior', self.TOP_GAP, self.BOT_GAP)
            assert result == expected_front, (
                f"interior={interior_h}: oczekiwano front_H={expected_front}, "
                f"otrzymano {result}"
            )

    def test_mode_interior_side_H_condition(self):
        """Tryb 'interior': round(2/3 × front_H) >= żądana wysokość wnętrza."""
        for h in [50, 100, 150, 200, 201, 250, 300, 380]:
            front_H = height_to_front_H(h, 'interior', self.TOP_GAP, self.BOT_GAP)
            side_H = round(2 / 3 * front_H)
            assert side_H >= h, f"h={h}: side_H={side_H} < {h}"

    def test_mode_interior_is_minimum(self):
        """Tryb 'interior': front_H jest minimalne (front_H-1 dawałoby za mały box)."""
        for h in [50, 100, 150, 200, 201, 250, 380]:
            front_H = height_to_front_H(h, 'interior', self.TOP_GAP, self.BOT_GAP)
            if front_H > 1:
                side_H_minus1 = round(2 / 3 * (front_H - 1))
                assert side_H_minus1 < h, (
                    f"h={h}: front_H={front_H} nie jest minimalne "
                    f"(front_H-1={front_H-1} daje side_H={side_H_minus1} >= {h})"
                )

    def test_model_default_mode_is_front(self, model, bd):
        """Brak height_mode w YAML → tryb 'front' (bez przeliczenia)."""
        # Komoda w YAML nie ma height_mode, więc heights są interpretowane jako front_H
        assert bd['drawer_0_front'].height == pytest.approx(FRONT_HEIGHTS[0])

    def test_load_komoda_niche_mode(self, tmp_path):
        """Integracyjny: height_mode: niche przelicza wnęki na fronty."""
        import yaml as _yaml
        cfg = {
            'carcass': {'width': 600, 'height': 900, 'depth': 460, 'placement': 'freestanding'},
            'material': {'thickness': 18, 'back_thickness': 0,
                         'drawer_thickness': 18, 'drawer_bottom': 18},
            'plinth': {'height': 100, 'inset_front': 15, 'inset_side': 15},
            'rail': {'depth': 100, 'thickness': 18,
                     'led_groove': {'width': 12, 'depth': 4, 'face': 'bottom', 'offset': 20}},
            'drawers': {
                'count': 2,
                'distribution': 'custom',
                'height_mode': 'niche',   # <-- tryb wnęki
                'heights': [200, 200],    # wnęki po 200mm → front_H = 200-50-3 = 147
            },
            'slides': {'model': 'GTV-H45'},
            'front': {'inset': 1.5, 'side_gap': 3, 'bottom_gap': 3, 'top_gap': 50},
        }
        yaml_file = tmp_path / 'test_niche.yaml'
        yaml_file.write_text(_yaml.dump(cfg))
        m = load_dresser(str(yaml_file))
        bd = {b.name: b for b in m.boards}
        assert bd['drawer_0_front'].height == pytest.approx(147)
        assert bd['drawer_1_front'].height == pytest.approx(147)

    def test_load_komoda_interior_mode(self, tmp_path):
        """Integracyjny: height_mode: interior przelicza max zawartość na fronty."""
        import yaml as _yaml
        cfg = {
            'carcass': {'width': 600, 'height': 900, 'depth': 460, 'placement': 'freestanding'},
            'material': {'thickness': 18, 'back_thickness': 0,
                         'drawer_thickness': 18, 'drawer_bottom': 18},
            'plinth': {'height': 100, 'inset_front': 15, 'inset_side': 15},
            'rail': {'depth': 100, 'thickness': 18,
                     'led_groove': {'width': 12, 'depth': 4, 'face': 'bottom', 'offset': 20}},
            'drawers': {
                'count': 2,
                'distribution': 'custom',
                'height_mode': 'interior',   # <-- tryb zawartości
                'heights': [150, 150],       # zmieści się 150mm → front_H = (3*150)//2 = 225
            },
            'slides': {'model': 'GTV-H45'},
            'front': {'inset': 1.5, 'side_gap': 3, 'bottom_gap': 3, 'top_gap': 50},
        }
        yaml_file = tmp_path / 'test_interior.yaml'
        yaml_file.write_text(_yaml.dump(cfg))
        m = load_dresser(str(yaml_file))
        bd = {b.name: b for b in m.boards}
        assert bd['drawer_0_front'].height == pytest.approx(225)
        # Weryfikacja że zawartość (side_H) >= 150
        side_H = round(2 / 3 * 225)
        assert side_H >= 150
