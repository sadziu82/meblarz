"""
Unit tests verifying inner-drawer design rules.
Rules from docs/design_rules.md (rule numbers in docstrings).
"""
from pathlib import Path
import pytest

from parts.drawer import load_drawer, _joint_positions, _select_nl


YAML_PATH = str(Path(__file__).parent.parent / 'projects' / 'drawer.yaml')

# ── Expected values for drawer.yaml (410×420×1000mm, GTV-H53) ─────────────────
NW, NH, ND  = 410, 420, 1000
MDF         = 18
BOT         = 18
TOP_GAP     = 50
INSET       = 1.5
SIDE_GAP    = 3
BOT_GAP     = 3
SLIDE_SIDE  = 19.5
SLIDE_REAR  = 20

FRONT_W         = NW - 2 * SIDE_GAP          # 404
FRONT_H         = NH - TOP_GAP - BOT_GAP     # 367
BOX_W           = NW - 2 * SLIDE_SIDE        # 371
MAX_BOX_DEPTH   = ND - (MDF + INSET) - SLIDE_REAR  # 960.5
NL              = 950                         # największe dostępne NL ≤ 960.5
SIDE_H          = round(2 / 3 * FRONT_H)     # 245
SIDE_D          = NL - MDF                   # 932  (głębokość boku)


@pytest.fixture(scope='module')
def model():
    return load_drawer(YAML_PATH)


@pytest.fixture(scope='module')
def bd(model):
    return {b.name: b for b in model.boards}


# ══════════════════════════════════════════════════════════════════════════════
# _joint_positions — reguły 36, 39, 40
# ══════════════════════════════════════════════════════════════════════════════

class TestJointPositions:

    def test_short_edge_single_center_hole(self):
        """Krawędź < 40mm (za mało miejsca na 2 otwory) → 1 otwór w środku."""
        assert _joint_positions(0, 30) == [15]

    def test_150mm_edge_two_holes(self):
        """Krawędź 150mm → 2 otwory w 1/4 i 3/4 (reguła 32: min 2)."""
        assert _joint_positions(0, 150) == [38, 112]

    def test_length_200_two_holes(self):
        """Krawędź 200mm (= 2×100) → 2 otwory w 1/4 i 3/4."""
        pos = _joint_positions(0, 200)
        assert pos == [50, 150]

    def test_standard_two_positions(self):
        """Normalna krawędź → otwory w 1/4 i 3/4, ale nie dalej niż 100mm od końca."""
        pos = _joint_positions(0, 400)
        assert pos == [100, 300]

    def test_1_4_capped_at_100mm(self):
        """Dla długiej krawędzi 1/4 > 100mm → przycinamy do 100mm (reguła 36)."""
        pos = _joint_positions(0, 600)
        assert pos[0] == 100

    def test_3_4_capped_at_100mm_from_end(self):
        """Dla długiej krawędzi 3/4 < L−100mm → przesuwamy do L−100mm (reguła 36)."""
        pos = _joint_positions(0, 600)
        assert 600 - pos[-1] == 100

    def test_max_100mm_from_end_various_lengths(self):
        """Skrajne otwory zawsze ≤ 100mm od końców (reguła 36)."""
        for length in [200, 300, 400, 600, 800, 932, 1000]:
            pos = _joint_positions(0, length)
            assert pos[0] <= 100, f"length={length}: pos[0]={pos[0]}"
            assert length - pos[-1] <= 100, f"length={length}: pos[-1]={pos[-1]}"

    def test_max_spacing_300mm(self):
        """Odstęp między sąsiednimi otworami ≤ 300mm (reguła 36)."""
        for length in [200, 400, 600, 800, 932, 1000]:
            pos = _joint_positions(0, length)
            for i in range(len(pos) - 1):
                gap = pos[i + 1] - pos[i]
                assert gap <= 300, f"length={length}: gap={gap} między poz. {i} i {i+1}"

    def test_adds_intermediate_holes_for_long_edge(self):
        """Krawędź 700mm (gap=500>300) → dodaje otwory pośrednie (reguła 36)."""
        pos = _joint_positions(0, 700)
        assert len(pos) >= 3
        for i in range(len(pos) - 1):
            assert pos[i + 1] - pos[i] <= 300

    def test_at_least_two_holes_per_joint(self):
        """Każde połączenie ma min 2 otwory (reguła 32)."""
        for length in [200, 300, 400, 600, 800]:
            assert len(_joint_positions(0, length)) >= 2

    def test_positions_are_integer_mm_offset_from_start(self):
        """Przesunięcia od startu krawędzi są całkowitą liczbą mm (zasada lokalnego układu)."""
        for start in [0.0, 19.5, 1.5, 9.0]:
            pos = _joint_positions(start, 400)
            for p in pos:
                offset = p - start
                assert abs(offset - round(offset)) < 1e-9, (
                    f"start={start}: offset={offset} nie jest całkowity"
                )

    def test_offset_start_preserves_relative_positions(self):
        """Przesunięcie startu nie zmienia względnych pozycji."""
        pos_0 = _joint_positions(0.0, 400)
        pos_s = _joint_positions(19.5, 400)
        assert len(pos_0) == len(pos_s)
        for p0, ps in zip(pos_0, pos_s):
            assert ps - 19.5 == pytest.approx(p0)

    def test_932mm_edge_five_holes(self):
        """Krawędź 932mm (głębokość boku w szufladzie) → 5 otworów."""
        pos = _joint_positions(0, 932)
        assert len(pos) == 5
        assert pos == [100, 283, 466, 649, 832]


# ══════════════════════════════════════════════════════════════════════════════
# _select_nl
# ══════════════════════════════════════════════════════════════════════════════

class TestSelectNl:

    NLS = [300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000]

    def test_selects_largest_fitting(self):
        assert _select_nl(self.NLS, 960.5) == 950

    def test_selects_exact_match(self):
        assert _select_nl(self.NLS, 950.0) == 950

    def test_selects_smallest_when_tight(self):
        assert _select_nl(self.NLS, 300.0) == 300

    def test_raises_when_nothing_fits(self):
        with pytest.raises(ValueError):
            _select_nl(self.NLS, 299.0)


# ══════════════════════════════════════════════════════════════════════════════
# Wymiary frontu — reguły 4, 5, 11
# ══════════════════════════════════════════════════════════════════════════════

class TestFrontDimensions:

    def test_front_width(self, bd):
        """front_W = wnęka_W − 2×szczelina_boczna (reguła 11)."""
        assert bd['front'].width == pytest.approx(FRONT_W)

    def test_front_height(self, bd):
        """front_H = wnęka_H − przerwa_górna − szczelina_dolna (reguły 4, 11)."""
        assert bd['front'].height == pytest.approx(FRONT_H)

    def test_front_top_gap_50mm(self, bd):
        """Przerwa górna 50mm dla szuflady bez uchwytu (reguła 4)."""
        assert bd['front'].height == pytest.approx(NH - 50 - BOT_GAP)

    def test_front_thickness_equals_mdf(self, bd):
        """Front ma grubość MDF=18mm (reguła 2)."""
        assert bd['front'].depth == pytest.approx(MDF)


# ══════════════════════════════════════════════════════════════════════════════
# Wymiary i układ skrzynki — reguły 6, 10, 12–17
# ══════════════════════════════════════════════════════════════════════════════

class TestBoxDimensions:

    def test_side_height_two_thirds_front(self, bd):
        """Wysokość boków = 2/3 × front_H, zaokrąglona (reguła 6)."""
        assert bd['side_left'].height == SIDE_H
        assert bd['side_right'].height == SIDE_H

    def test_side_height_less_than_front(self, bd):
        """Boki niższe od frontu (reguła 6: top_gap=50mm)."""
        assert bd['side_left'].height < bd['front'].height

    def test_box_width(self, bd):
        """box_W_ext = wnęka_W − 2×luz_boczny (reguła 13)."""
        assert bd['bottom'].width == pytest.approx(BOX_W)

    def test_box_depth_equals_nl(self, model, bd):
        """Głębokość skrzynki = NL prowadnicy, SKL=NL (reguła 17)."""
        assert bd['bottom'].depth == pytest.approx(model.slide_nl)

    def test_nl_is_largest_fitting(self, model):
        """Wybrane NL jest największym mieszczącym się w max_box_depth (reguła 17)."""
        assert model.slide_nl == NL
        assert model.slide_nl <= MAX_BOX_DEPTH
        assert model.slide_nl + 50 > MAX_BOX_DEPTH  # następne NL już nie mieści się

    def test_bottom_thickness(self, bd):
        """Dno MDF=18mm (reguła 7)."""
        assert bd['bottom'].height == pytest.approx(BOT)

    def test_side_depth(self, bd):
        """Głębokość boków = box_depth − mdf (reguła 16)."""
        assert bd['side_left'].depth == pytest.approx(SIDE_D)
        assert bd['side_right'].depth == pytest.approx(SIDE_D)

    def test_rear_width_equals_box_width(self, bd):
        """Tył ma pełną szerokość box_W_ext — taką samą jak dno (reguła 15)."""
        assert bd['rear'].width == pytest.approx(bd['bottom'].width)

    def test_rear_depth_equals_mdf(self, bd):
        """Grubość tylnej ścianki = MDF=18mm."""
        assert bd['rear'].depth == pytest.approx(MDF)

    def test_rear_height_equals_side_height(self, bd):
        """Tył ma tę samą wysokość co boki."""
        assert bd['rear'].height == pytest.approx(SIDE_H)

    def test_box_starts_behind_front_rule10(self, bd):
        """Skrzynka zaczyna się za tylną ścianą frontu: bottom.y = front.y + front.depth (reguła 10)."""
        front = bd['front']
        bottom = bd['bottom']
        assert bottom.pos[1] == pytest.approx(front.pos[1] + front.depth)

    def test_no_overlap_front_and_box(self, bd):
        """Front i skrzynka nie nachodzą na siebie (reguła 10)."""
        front = bd['front']
        bottom = bd['bottom']
        assert bottom.pos[1] >= front.pos[1] + front.depth - 1e-9

    def test_bottom_2mm_above_front(self, bd):
        """Dno 2mm wyżej niż spód frontu (reguła 12)."""
        assert bd['bottom'].pos[2] == pytest.approx(bd['front'].pos[2] + 2)

    def test_sides_sit_on_bottom(self, bd):
        """Boki stoją na dnie: side.z = bottom.z + bottom.height (reguła 12)."""
        bottom = bd['bottom']
        assert bd['side_left'].pos[2] == pytest.approx(bottom.pos[2] + bottom.height)
        assert bd['side_right'].pos[2] == pytest.approx(bottom.pos[2] + bottom.height)

    def test_rear_at_back_of_bottom(self, bd):
        """Tył przy tylnej krawędzi dna: rear.y = bottom.y + box_depth − mdf (reguła 15)."""
        bottom = bd['bottom']
        rear = bd['rear']
        assert rear.pos[1] == pytest.approx(bottom.pos[1] + bottom.depth - rear.depth)

    def test_rear_same_z_as_sides(self, bd):
        """Tył zaczyna się na tym samym Z co boki."""
        assert bd['rear'].pos[2] == pytest.approx(bd['side_left'].pos[2])

    def test_sides_same_y_start_as_bottom(self, bd):
        """Boki zaczynają się w tym samym Y co dno."""
        assert bd['side_left'].pos[1] == pytest.approx(bd['bottom'].pos[1])
        assert bd['side_right'].pos[1] == pytest.approx(bd['bottom'].pos[1])

    def test_sides_symmetric_within_bottom(self, bd):
        """Boki symetrycznie obejmują dno w osi X."""
        bottom = bd['bottom']
        sl = bd['side_left']
        sr = bd['side_right']
        assert sl.pos[0] == pytest.approx(bottom.pos[0])
        assert sr.pos[0] + sr.width == pytest.approx(bottom.pos[0] + bottom.width)

    def test_model_centered_at_origin(self, model):
        """X and Y centred at 0; Z bottom at 0 (floor)."""
        xs = [b.pos[0] for b in model.boards] + [b.pos[0] + b.width  for b in model.boards]
        ys = [b.pos[1] for b in model.boards] + [b.pos[1] + b.depth  for b in model.boards]
        zs = [b.pos[2] for b in model.boards] + [b.pos[2] + b.height for b in model.boards]
        assert (min(xs) + max(xs)) / 2 == pytest.approx(0)
        assert (min(ys) + max(ys)) / 2 == pytest.approx(0)
        assert min(zs) == pytest.approx(0)


# ══════════════════════════════════════════════════════════════════════════════
# Typy połączeń — reguły 18, 33
# ══════════════════════════════════════════════════════════════════════════════

class TestJointTypes:

    def _holes_to(self, bd_dict, src, partner):
        return [jh for jh in bd_dict[src].joint_holes if jh.partner == partner]

    def test_front_side_joints_are_dowels(self, bd):
        """Front ↔ Boki: kołki drewniane (reguła 18, 33)."""
        for side in ('side_left', 'side_right'):
            holes = self._holes_to(bd, 'front', side)
            assert holes, f"Brak otworów front↔{side}"
            assert all(jh.hole_type == 'dowel' for jh in holes)

    def test_front_bottom_joints_are_dowels(self, bd):
        """Front ↔ Dno: kołki drewniane (reguła 18, 23)."""
        holes = self._holes_to(bd, 'front', 'bottom')
        assert holes
        assert all(jh.hole_type == 'dowel' for jh in holes)

    def test_bottom_side_joints_are_confirmats(self, bd):
        """Dno ↔ Boki: konfirmaty (reguła 18, 19)."""
        for side in ('side_left', 'side_right'):
            holes = self._holes_to(bd, 'bottom', side)
            assert holes
            assert all(jh.hole_type == 'confirmat' for jh in holes)

    def test_rear_side_joints_are_confirmats(self, bd):
        """Tył ↔ Boki: konfirmaty (reguła 18, 20)."""
        for side in ('side_left', 'side_right'):
            holes = self._holes_to(bd, 'rear', side)
            assert holes
            assert all(jh.hole_type == 'confirmat' for jh in holes)

    def test_bottom_rear_joints_are_confirmats(self, bd):
        """Dno ↔ Tył: konfirmaty (reguła 18, 21)."""
        holes = self._holes_to(bd, 'bottom', 'rear')
        assert holes
        assert all(jh.hole_type == 'confirmat' for jh in holes)


# ══════════════════════════════════════════════════════════════════════════════
# Kierunki wiercenia — reguły 19, 20, 21, 22, 23
# ══════════════════════════════════════════════════════════════════════════════

class TestDrillingDirections:

    def test_bottom_side_drilled_from_below(self, bd):
        """Dno↔Bok: wiercone od spodu dna (-Z) przez dno w podstawę boku (reguła 19)."""
        for side in ('side_left', 'side_right'):
            holes = [jh for jh in bd['bottom'].joint_holes if jh.partner == side]
            assert all(jh.direction == '-z' for jh in holes)

    def test_bottom_rear_drilled_from_below(self, bd):
        """Dno↔Tył: wiercone od spodu dna (-Z) przez dno w podstawę tyłu (reguła 21)."""
        holes = [jh for jh in bd['bottom'].joint_holes if jh.partner == 'rear']
        assert all(jh.direction == '-z' for jh in holes)

    def test_rear_side_drilled_from_back(self, bd):
        """Tył↔Bok: wiercone od tylnej ściany tyłu (+Y) w czoło boku (reguła 20)."""
        for side in ('side_left', 'side_right'):
            holes = [jh for jh in bd['rear'].joint_holes if jh.partner == side]
            assert all(jh.direction == '+y' for jh in holes)

    def test_front_holes_only_from_back(self, bd):
        """Otwory frontu tylko od tylnej ściany (+Y): żadne wiercenie od czoła zewnętrznego (reguły 44, 45)."""
        for jh in bd['front'].joint_holes:
            assert jh.direction == '+y', (
                f"Front: niedozwolony kierunek wiercenia: {jh.direction}"
            )

    def test_side_dowels_from_front_face(self, bd):
        """Kołki w boku od czoła przedniego (-Y): bok↔front (reguła 22)."""
        for side in ('side_left', 'side_right'):
            holes = [jh for jh in bd[side].joint_holes
                     if jh.partner == 'front' and jh.hole_type == 'dowel']
            assert holes
            assert all(jh.direction == '-y' for jh in holes)


# ══════════════════════════════════════════════════════════════════════════════
# Minimalna liczba otworów — reguła 32
# ══════════════════════════════════════════════════════════════════════════════

class TestMinimumHoles:

    def test_each_joint_has_min_2_holes(self, model, bd):
        """Każde połączenie ma min 2 otwory (reguła 32)."""
        seen: set = set()
        for name_a, name_b in model.joints:
            pair = (name_a, name_b)
            if pair in seen:
                continue
            seen.add(pair)
            holes = [jh for jh in bd[name_a].joint_holes if jh.partner == name_b]
            assert len(holes) >= 2, (
                f"Połączenie {name_a}↔{name_b}: tylko {len(holes)} otworów"
            )

    def test_front_bottom_exactly_two_dowels(self, bd):
        """Front↔Dno: zawsze dokładnie 2 kołki (reguła 23)."""
        holes = [jh for jh in bd['front'].joint_holes if jh.partner == 'bottom']
        assert len(holes) == 2


# ══════════════════════════════════════════════════════════════════════════════
# Zasady rozmieszczenia — max 100mm od końca, max 300mm odstęp (reguły 36, 39)
# ══════════════════════════════════════════════════════════════════════════════

class TestHoleSpacing:

    def _check_spacing(self, positions, edge_length, label):
        assert positions[0] <= 100, f"{label}: pierwszy otwór za daleko od krawędzi ({positions[0]}mm)"
        assert edge_length - positions[-1] <= 100, (
            f"{label}: ostatni otwór za daleko od krawędzi ({edge_length - positions[-1]}mm)"
        )
        for i in range(len(positions) - 1):
            gap = positions[i + 1] - positions[i]
            assert gap <= 300, f"{label}: odstęp {gap}mm > 300mm między poz. {i} i {i+1}"

    def test_bottom_side_left_y(self, bd):
        """Dno↔Bok lewy: otwory wzdłuż głębokości boku (reguła 19, 36)."""
        side_left = bd['side_left']
        holes = [jh for jh in bd['bottom'].joint_holes if jh.partner == 'side_left']
        pos = sorted(jh.y - side_left.pos[1] for jh in holes)
        self._check_spacing(pos, SIDE_D, 'Dno↔Bok lewy')

    def test_bottom_side_right_y(self, bd):
        """Dno↔Bok prawy: analogicznie."""
        side_right = bd['side_right']
        holes = [jh for jh in bd['bottom'].joint_holes if jh.partner == 'side_right']
        pos = sorted(jh.y - side_right.pos[1] for jh in holes)
        self._check_spacing(pos, SIDE_D, 'Dno↔Bok prawy')

    def test_rear_side_left_z(self, bd):
        """Tył↔Bok lewy: otwory wzdłuż wysokości boku (reguła 20, 36)."""
        side_left = bd['side_left']
        holes = [jh for jh in bd['rear'].joint_holes if jh.partner == 'side_left']
        pos = sorted(jh.z - side_left.pos[2] for jh in holes)
        self._check_spacing(pos, SIDE_H, 'Tył↔Bok lewy')

    def test_rear_side_right_z(self, bd):
        """Tył↔Bok prawy: analogicznie."""
        side_right = bd['side_right']
        holes = [jh for jh in bd['rear'].joint_holes if jh.partner == 'side_right']
        pos = sorted(jh.z - side_right.pos[2] for jh in holes)
        self._check_spacing(pos, SIDE_H, 'Tył↔Bok prawy')

    def test_bottom_rear_x(self, bd):
        """Dno↔Tył: otwory wzdłuż szerokości dna (reguła 21, 36)."""
        bottom = bd['bottom']
        holes = [jh for jh in bottom.joint_holes if jh.partner == 'rear']
        pos = sorted(jh.x - bottom.pos[0] for jh in holes)
        self._check_spacing(pos, BOX_W, 'Dno↔Tył')

    def test_front_side_left_z(self, bd):
        """Front↔Bok lewy: kołki wzdłuż wysokości boku (reguła 22, 39)."""
        side_left = bd['side_left']
        holes = [jh for jh in bd['front'].joint_holes if jh.partner == 'side_left']
        pos = sorted(jh.z - side_left.pos[2] for jh in holes)
        self._check_spacing(pos, SIDE_H, 'Front↔Bok lewy')

    def test_front_side_right_z(self, bd):
        """Front↔Bok prawy: analogicznie."""
        side_right = bd['side_right']
        holes = [jh for jh in bd['front'].joint_holes if jh.partner == 'side_right']
        pos = sorted(jh.z - side_right.pos[2] for jh in holes)
        self._check_spacing(pos, SIDE_H, 'Front↔Bok prawy')

    def test_front_bottom_x(self, bd):
        """Front↔Dno: kołki wzdłuż szerokości dna (reguła 23, 39)."""
        bottom = bd['bottom']
        holes = [jh for jh in bd['front'].joint_holes if jh.partner == 'bottom']
        pos = sorted(jh.x - bottom.pos[0] for jh in holes)
        self._check_spacing(pos, BOX_W, 'Front↔Dno')

    def test_bottom_side_hole_count(self, bd):
        """Dla głębokości boku 932mm: 5 otworów (p=100,283,466,649,832)."""
        holes = [jh for jh in bd['bottom'].joint_holes if jh.partner == 'side_left']
        assert len(holes) == 5

    def test_rear_side_hole_count(self, bd):
        """Dla wysokości boku 245mm: 2 otwory (p=61,184)."""
        holes = [jh for jh in bd['rear'].joint_holes if jh.partner == 'side_left']
        assert len(holes) == 2

    def test_bottom_rear_hole_count(self, bd):
        """Dla szerokości box_W=371mm: 2 otwory (p=93,278)."""
        holes = [jh for jh in bd['bottom'].joint_holes if jh.partner == 'rear']
        assert len(holes) == 2


# ══════════════════════════════════════════════════════════════════════════════
# Lokalny układ współrzędnych — otwory w czole na środku grubości (reguły 41–43)
# ══════════════════════════════════════════════════════════════════════════════

class TestLocalCoordinates:

    def test_bottom_side_x_center_of_left_side_thickness(self, bd):
        """Dno↔Bok lewy: X otworu na środku grubości lewego boku (reguła 19, 42)."""
        bottom = bd['bottom']
        holes = [jh for jh in bottom.joint_holes if jh.partner == 'side_left']
        for jh in holes:
            local_x = jh.x - bottom.pos[0]
            assert local_x == pytest.approx(MDF / 2), (
                f"Dno↔Bok lewy X={local_x}, oczekiwano {MDF/2}"
            )

    def test_bottom_side_x_center_of_right_side_thickness(self, bd):
        """Dno↔Bok prawy: X otworu na środku grubości prawego boku (reguła 19, 42)."""
        bottom = bd['bottom']
        side_right = bd['side_right']
        expected_local_x = side_right.pos[0] - bottom.pos[0] + MDF / 2
        holes = [jh for jh in bottom.joint_holes if jh.partner == 'side_right']
        for jh in holes:
            local_x = jh.x - bottom.pos[0]
            assert local_x == pytest.approx(expected_local_x), (
                f"Dno↔Bok prawy X={local_x}, oczekiwano {expected_local_x}"
            )

    def test_side_czoło_holes_at_center_of_thickness(self, bd):
        """Otwory kołkowe w czole boku (direction='-y') na środku grubości w X (reguła 22, 42)."""
        for side_name in ('side_left', 'side_right'):
            side = bd[side_name]
            holes = [jh for jh in side.joint_holes if jh.direction == '-y']
            assert holes, f"{side_name}: brak otworów w czole"
            for jh in holes:
                local_x = jh.x - side.pos[0]
                assert local_x == pytest.approx(MDF / 2), (
                    f"{side_name} czoło: local_x={local_x}, oczekiwano {MDF/2}"
                )

    def test_bottom_czoło_holes_at_center_of_thickness(self, bd):
        """Kołek w czole dna (direction='-y') na środku grubości dna w Z (reguła 23, 42)."""
        bottom = bd['bottom']
        holes = [jh for jh in bottom.joint_holes
                 if jh.partner == 'front' and jh.direction == '-y']
        assert holes
        for jh in holes:
            local_z = jh.z - bottom.pos[2]
            assert local_z == pytest.approx(BOT / 2), (
                f"Dno czoło: local_z={local_z}, oczekiwano {BOT/2}"
            )

    def test_bottom_rear_y_at_center_of_rear_depth(self, bd):
        """Dno↔Tył: Y otworu na środku głębokości tylnej ścianki (reguła 21)."""
        bottom = bd['bottom']
        rear = bd['rear']
        expected_local_y = rear.pos[1] - bottom.pos[1] + MDF / 2
        holes = [jh for jh in bottom.joint_holes if jh.partner == 'rear']
        for jh in holes:
            local_y = jh.y - bottom.pos[1]
            assert local_y == pytest.approx(expected_local_y), (
                f"Dno↔Tył Y={local_y}, oczekiwano {expected_local_y}"
            )

    def test_rear_side_x_at_center_of_side_thickness(self, bd):
        """Tył↔Bok lewy: X otworu na środku grubości boku (reguła 20, 42)."""
        rear = bd['rear']
        side_left = bd['side_left']
        expected_local_x = side_left.pos[0] - rear.pos[0] + MDF / 2
        holes = [jh for jh in rear.joint_holes if jh.partner == 'side_left']
        for jh in holes:
            local_x = jh.x - rear.pos[0]
            assert local_x == pytest.approx(expected_local_x)

    def test_hole_positions_integer_mm_along_joint_edge(self, bd):
        """Pozycje otworów to całkowita liczba mm od rogu deski wzdłuż krawędzi łączenia (reguły 41–43)."""
        checks = [
            # (board, partner, axis, reference_pos)
            ('bottom', 'side_left',  'y', bd['side_left'].pos[1]),
            ('bottom', 'side_right', 'y', bd['side_right'].pos[1]),
            ('rear',   'side_left',  'z', bd['side_left'].pos[2]),
            ('rear',   'side_right', 'z', bd['side_right'].pos[2]),
            ('bottom', 'rear',       'x', bd['bottom'].pos[0]),
            ('front',  'side_left',  'z', bd['side_left'].pos[2]),
            ('front',  'bottom',     'x', bd['bottom'].pos[0]),
        ]
        for src, partner, axis, ref in checks:
            holes = [jh for jh in bd[src].joint_holes if jh.partner == partner]
            for jh in holes:
                val = getattr(jh, axis)
                offset = val - ref
                assert abs(offset - round(offset)) < 1e-9, (
                    f"{src}↔{partner} oś {axis}: offset={offset} nie jest całkowity"
                )


# ══════════════════════════════════════════════════════════════════════════════
# Estetyka — reguły 44, 45
# ══════════════════════════════════════════════════════════════════════════════

class TestAesthetics:

    def test_front_holes_only_from_internal_face(self, bd):
        """Wszystkie otwory frontu od tylnej (wewnętrznej) ściany, direction='+y' (reguła 44, 45)."""
        for jh in bd['front'].joint_holes:
            assert jh.direction == '+y', (
                f"Front: otwór od niedozwolonej strony: direction={jh.direction!r}"
            )

    def test_front_hole_y_at_back_face(self, bd):
        """Otwory frontu leżą na tylnej ścianie frontu (nie poza frontem)."""
        front = bd['front']
        back_y = front.pos[1] + front.depth
        for jh in front.joint_holes:
            assert abs(jh.y - back_y) < 1e-9, (
                f"Front: otwór poza tylną ścianą: jh.y={jh.y}, back_y={back_y}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# Prowadnice — reguły 26, 29, 30
# ══════════════════════════════════════════════════════════════════════════════

class TestSlideMount:

    def test_slide_model_for_deep_niche(self, model):
        """Dla wnęki >600mm stosować wzmocnioną prowadnicę GTV-H53 (reguła 26)."""
        assert ND > 600
        assert model.slide_model == 'GTV-H53'

    def test_slide_nl_matches_model(self, model):
        """NL prowadnicy prawidłowo dobrane."""
        assert model.slide_nl == NL

    def test_slide_mount_z_50mm_from_bottom(self, bd):
        """Otwory montażowe na boku: spód prowadnicy 50mm od spodu dna (reguła 29)."""
        bottom = bd['bottom']
        for side_name in ('side_left', 'side_right'):
            side = bd[side_name]
            assert side.holes, f"{side_name}: brak otworów montażowych prowadnicy"
            for hole in side.holes:
                z_from_bottom = hole.z - bottom.pos[2]
                assert z_from_bottom == pytest.approx(50.0), (
                    f"{side_name}: wysokość montażu = {z_from_bottom}mm, oczekiwano 50mm"
                )

    def test_slide_holes_within_nl_range(self, model, bd):
        """Otwory montażowe mieszczą się w zakresie NL (reguła 30)."""
        for side_name in ('side_left', 'side_right'):
            side = bd[side_name]
            for hole in side.holes:
                y_rel = hole.y - side.pos[1]
                assert 0 <= y_rel <= model.slide_nl, (
                    f"{side_name}: Y otworu {y_rel:.1f}mm poza NL={model.slide_nl}mm"
                )

    def test_slide_holes_present_on_both_sides(self, bd):
        """Otwory montażowe na obu bokach skrzynki."""
        assert bd['side_left'].holes
        assert bd['side_right'].holes
