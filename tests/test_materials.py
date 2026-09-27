import csv
from pathlib import Path
import pytest
from parts.drawer import Board, _shift_boards, load_drawer
from parts.materials import apply_finishes, csv_edging, edge_outline
from export import write_meblepl_csv

ROOT = Path(__file__).resolve().parents[1]


def test_drawer_finish_matches_configured_supplier_cut_list(tmp_path):
    model = load_drawer(str(ROOT / 'projects/drawer.yaml'))
    panels = {b.name: b for b in model.boards if b.material_id}
    assert set(panels) == {'front', 'bottom', 'side_left', 'side_right', 'rear'}
    assert all(Path(b.material_texture).is_file() for b in panels.values())
    assert panels['front'].edgebands == dict.fromkeys(['left', 'right', 'top', 'bottom'], .8)
    assert panels['bottom'].edgebands == {'left': .8, 'right': .8}
    assert csv_edging(panels['bottom']) == ('', '=')
    assert csv_edging(panels['front']) == ('=', '=')
    assert csv_edging(panels['side_left']) == ('-', '')
    shifted = _shift_boards(list(panels.values()), 1, 2, 3)
    assert shifted[0].material_texture == panels[shifted[0].name].material_texture
    assert shifted[0].edgebands == panels[shifted[0].name].edgebands
    path = tmp_path / 'cut.csv'
    write_meblepl_csv(model, path)
    rows = list(csv.reader(path.open(), delimiter=';'))[1:]
    assert [(r[0],r[1],r[3],r[7]) for r in rows] == [
        ('front','404','367','2'), ('bottom','371','950','2'),
        ('side_left','932','245','1'), ('side_right','932','245','1'),
        ('rear','371','245','2')]
    assert [(r[0], r[2], r[4]) for r in rows] == [
        ('front', '=', '='), ('bottom', '', '='), ('side_left', '-', ''),
        ('side_right', '-', ''), ('rear', '-', '=')]


def test_unfinished_panels_export_no_accidental_single_edge():
    board = Board('shelf', 600, 18, 300, (0, 0, 0))
    assert csv_edging(board) == ('', '')
    with pytest.raises(ValueError, match='not a narrow'):
        apply_finishes([board], {'material': {'edge_banding': {'boards': {'shelf': ['top']}}}})
    with pytest.raises(ValueError, match='matches no board'):
        apply_finishes([board], {'material': {'edge_banding': {'boards': {'typo': ['front']}}}})
    points = edge_outline(board, 'front')
    assert {p[1] for p in points} == {-.35}
    assert {p[0] for p in points} == {0, 600}
    assert {p[2] for p in points} == {0, 18}


def test_automatic_contacts_union_and_partial_exposure():
    from parts.materials import automatic_edgebands
    shelf = Board('shelf', 600, 18, 300, (0, 0, 100), movable=False)
    left = Board('left', 18, 100, 300, (-18, 0, 90), movable=False)
    # Two boards together hide the right edge; neither is sufficient alone.
    r1 = Board('right1', 18, 100, 150, (600, 0, 90), movable=False)
    r2 = Board('right2', 18, 100, 150, (600, 150, 90), movable=False)
    automatic_edgebands([shelf, left, r1, r2], .8)
    assert set(shelf.edgebands) == {'front'}
    r2.pos = (600, 151, 90)  # a 1 mm gap must not be treated as a full contact
    automatic_edgebands([shelf, left, r1, r2], .8)
    assert set(shelf.edgebands) == {'front', 'right'}


def test_floor_rear_visibility_and_independent_motion():
    from parts.materials import automatic_edgebands
    outer = Board('outer', 18, 700, 600, (0, 0, 0), movable=False)
    inner = Board('inner', 18, 700, 600, (300, 0, 0), movable=False)
    right = Board('right', 18, 700, 600, (600, 0, 0), movable=False)
    automatic_edgebands([outer, inner, right], .8, rear_edges='visible_sides')
    assert 'rear' in outer.edgebands and 'rear' in right.edgebands
    assert 'rear' not in inner.edgebands
    assert all('bottom' not in b.edgebands for b in (outer, inner, right))
    drawer = Board('drawer_0_side', 18, 100, 400, (18, 0, 18))
    roof = Board('roof', 400, 18, 400, (0, 0, 118), movable=False)
    automatic_edgebands([outer, drawer, roof], .8)
    assert 'top' in drawer.edgebands  # fixed roof must not conceal opened drawer
    moving_roof = Board('drawer_0_roof', 400, 18, 400, (0, 0, 118))
    automatic_edgebands([outer, drawer, moving_roof], .8)
    assert 'top' not in drawer.edgebands


def test_all_generators_enable_automatic_edging_without_yaml_lists():
    from export import _load_model
    for path in (ROOT / 'projects').glob('*.yaml'):
        model = _load_model(path)
        assert any(b.edgebands for b in model.boards), path
        assert not any(b.edgebands for b in model.boards if not b.fabrication or 'slide_' in b.name)


def test_overrides_and_thin_hdf():
    shelf = Board('shelf', 600, 18, 300, (0, 0, 100), movable=False)
    back = Board('back', 600, 800, 3, (0, 300, 0), movable=False)
    apply_finishes([shelf, back], {})
    assert not back.edgebands and shelf.edgebands
    apply_finishes([shelf, back], {'material': {'edge_banding': {'boards': {'shelf': []}}}})
    assert not shelf.edgebands
    apply_finishes([shelf, back], {'material': {'edge_banding': {'automatic': False}}})
    assert not shelf.edgebands and not back.edgebands


def test_adjacent_carcasses_hide_rear_edges_of_shared_cheeks():
    from parts.materials import automatic_edgebands
    boards = [Board(f'side_{i}', 18, 700, 600, (x, 0, 0), movable=False)
              for i, x in enumerate((0, 582, 600, 1182))]
    automatic_edgebands(boards, .8, rear_edges='visible_sides')
    assert ['rear' in b.edgebands for b in boards] == [True, False, False, True]


def test_rounded_front_outline_follows_the_actual_corner():
    board = Board('desk', 1350, 18, 600, (0, 0, 800),
                  corner_radius=200, rounded_front_corners=(False, True))
    outline = edge_outline(board, 'front', offset=0)
    assert (1350, 0, 0) not in outline
    assert outline[0] == (0, 0, 0)
    assert (1350, 200, 0) in outline


def test_rear_edging_is_opt_in():
    side = Board('side', 18, 700, 600, (0, 0, 0), movable=False)
    apply_finishes([side], {})
    assert 'rear' not in side.edgebands
    apply_finishes([side], {'material': {'edge_banding': {'band_rear_edges': True}}})
    assert 'rear' in side.edgebands
    assert 'bottom' not in side.edgebands
    apply_finishes([side], {'material': {'edge_banding': {'band_rear_edges': False}}})
    assert 'rear' not in side.edgebands


@pytest.mark.parametrize('board,axes,grain,texture', [
    (Board('deep_shelf', 300, 18, 600, (0,0,0)), (0,1,2), 2, (0,1)),
    (Board('tall_front', 300, 900, 18, (0,0,0)), (0,2,1), 2, (0,2)),
    (Board('short_side', 18, 200, 900, (0,0,0)), (1,2,0), 1, (2,1)),
    (Board('tall_side', 18, 2000, 600, (0,0,0)), (1,2,0), 1, (2,1)),
])
def test_installed_orientation_and_grain(board, axes, grain, texture):
    from parts.materials import panel_axes, grain_code, texture_axes
    from export import _cut_dimensions
    assert panel_axes(board) == axes
    assert grain_code(board) == grain
    assert texture_axes(board) == texture
    dimensions = (board.width, board.depth, board.height)
    assert _cut_dimensions(board) == tuple(dimensions[i] for i in axes)


@pytest.mark.parametrize('board', [
    Board('shelf', 600, 18, 300, (0,0,0)),
    Board('front', 400, 800, 18, (0,0,0)),
    Board('side', 18, 900, 600, (0,0,0)),
])
def test_banded_texture_follows_every_edge(board):
    from parts.materials import FACE_AXES, panel_axes, texture_axes, face_texture_axes
    normal = panel_axes(board)[2]
    for face, (face_axis, _) in FACE_AXES.items():
        if face_axis == normal:
            assert face_texture_axes(board, face) == texture_axes(board)
            continue
        board.edgebands[face] = .8
        along, across = face_texture_axes(board, face)
        assert across == normal
        assert along not in (normal, face_axis)
        # Changing the panel grain must not make banding run across the edge.
        assert sorted((along, across, face_axis)) == [0, 1, 2]
