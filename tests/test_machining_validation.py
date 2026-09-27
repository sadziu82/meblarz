"""Construction rules shared by every generator and production writer."""
from pathlib import Path
from collections import defaultdict
import pytest
import yaml

from export import _load_model, write_meblepl_csv, write_drilling_sheet, write_dxf_files
from parts.drawer import Board, Hole, JointHole
from parts.joinery import supplement_confirmat_dowels
from parts.machining import validate_drilling, finalize_boards

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('direction', ['+x', '-x', '+y', '-y', '+z', '-z'])
def test_bore_radius_must_fit_whole_panel(direction):
    board = Board('panel', 100, 100, 100, (10, 20, 30), movable=False)
    axis = 'xyz'.index(direction[-1])
    cross = (axis + 1) % 3
    point = [v + 50 for v in board.pos]
    point[axis] = board.pos[axis] + (100 if direction[0] == '+' else 0)
    point[cross] = board.pos[cross] + 1
    hole = Hole(*point, 10, 5, direction)
    board.holes = [hole]
    with pytest.raises(ValueError, match='panel: bore crosses board edge'):
        validate_drilling([board])
    setattr(hole, 'xyz'[cross], board.pos[cross] + 5)
    validate_drilling([board])  # Tangency is permitted.
    setattr(hole, 'xyz'[cross], board.pos[cross] + 99)
    with pytest.raises(ValueError, match='crosses board edge'):
        validate_drilling([board])


@pytest.mark.parametrize('diameter,depth', [(0, 5), (-3, 5), (5, 100), (5, float('nan'))])
def test_invalid_bore_dimensions(diameter, depth):
    board = Board('front', 100, 100, 18, (0, 0, 0))
    board.holes = [Hole(50, 0, 50, diameter, depth, '-y')]
    with pytest.raises(ValueError, match='invalid bore depth/diameter'):
        validate_drilling([board])


@pytest.mark.parametrize('filename', ['drawer.yaml', 'dresser.yaml', 'desk_drawer_wall.yaml'])
def test_yaml_with_handle_deeper_than_front_is_rejected(tmp_path, filename):
    cfg = yaml.safe_load((ROOT / 'projects' / filename).read_text())
    front = (cfg['desk_drawer_wall']['drawer_tower']['drawers']['front']
             if filename == 'desk_drawer_wall.yaml' else cfg['front'])
    front['handle'] = dict(hole_spacing=160, hole_diameter=5, hole_depth=100, vertical='center')
    path = tmp_path / filename
    path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError, match='invalid bore depth/diameter for handle'):
        _load_model(path)


@pytest.mark.parametrize('writer', ['csv', 'drilling', 'dxf'])
def test_every_writer_revalidates_mutated_model(tmp_path, writer):
    model = _load_model(ROOT / 'projects/drawer.yaml')
    front = next(b for b in model.boards if b.name == 'front')
    front.holes.append(Hole(front.pos[0] + 50, front.pos[1], front.pos[2] + 50,
                            5, 100, '-y', 'handle'))
    with pytest.raises(ValueError, match='invalid bore depth/diameter'):
        if writer == 'csv':
            write_meblepl_csv(model, tmp_path / 'cut.csv')
        elif writer == 'drilling':
            write_drilling_sheet(model, tmp_path / 'drilling.md', 'test.yaml')
        else:
            write_dxf_files(model, tmp_path / 'dxf')
    assert not list(tmp_path.iterdir())


def test_finalization_checks_rounded_dimensions():
    board = Board('panel', 100, 100, 18, (0, 0, 0))
    # Before rounding these cylinders are tangent. Independently rounding the
    # centres and diameters makes them intersect (distance 5.1, radii sum 5.15).
    board.holes = [Hole(20.05, 0, 50, 5.06, 5, '-y'),
                   Hole(25.19, 0, 50, 5.22, 5, '-y')]
    validate_drilling([board])
    with pytest.raises(ValueError, match='Kolizja nawiertów'):
        finalize_boards([board], {})


@pytest.mark.parametrize('filename', ['drawer.yaml', 'dresser.yaml', 'desk_drawer_wall.yaml', 'kitchen_tall_unit.yaml'])
def test_all_generators_complete_large_confirmat_gaps(filename):
    model = _load_model(ROOT / 'projects' / filename)
    by_name = {b.name: b for b in model.boards}
    for board in model.boards:
        groups = defaultdict(list)
        for h in board.joint_holes:
            if h.element == 1:
                groups[(h.partner, h.direction[-1])].append(h)
        for (partner, normal), holes in groups.items():
            screws = [h for h in holes if h.hole_type == 'confirmat']
            if len(screws) < 2:
                continue
            axis = max((a for a in 'xyz' if a != normal),
                       key=lambda a: max(getattr(h, a) for h in screws) - min(getattr(h, a) for h in screws))
            screws.sort(key=lambda h: getattr(h, axis))
            for a, b in zip(screws, screws[1:]):
                if getattr(b, axis) - getattr(a, axis) <= 200 + 1e-6:
                    continue
                midpoint = (getattr(a, axis) + getattr(b, axis)) / 2
                dowels = [h for h in holes if h.hole_type == 'dowel'
                          and abs(getattr(h, axis) - midpoint) <= .251]
                assert len(dowels) == 1, (filename, board.name, partner, midpoint)
                dowel = dowels[0]
                assert any(h.element == 2 and h.partner == board.name and h.hole_type == 'dowel'
                           and (h.x, h.y, h.z) == pytest.approx((dowel.x, dowel.y, dowel.z))
                           for h in by_name[partner].joint_holes)
    validate_drilling(model.boards)


@pytest.mark.parametrize('gap,limit,count', [(200, 200, 0), (201, 200, 1), (201, 250, 0)])
def test_supplement_preserves_screws_and_is_idempotent(gap, limit, count):
    bottom = Board('bottom', 400, 18, 400, (0, 0, 0), movable=False)
    side = Board('side', 18, 100, 400, (0, 0, 18), movable=False)
    for y in (50, 50 + gap):
        bottom.joint_holes.append(JointHole(9, y, 0, '-z', 1, 'side'))
        side.joint_holes.append(JointHole(9, y, 18, '-z', 2, 'bottom'))
    original = list(bottom.joint_holes)
    for _ in range(2):
        supplement_confirmat_dowels([bottom, side], {'dowel_between_confirmats_above': limit})
    assert bottom.joint_holes[:2] == original
    assert len(bottom.joint_holes) == len(side.joint_holes) == 2 + count
    validate_drilling([bottom, side])


def test_legacy_opposed_shelves_are_rejected_without_explicit_policy(tmp_path):
    cfg = yaml.safe_load((ROOT / 'tests/fixtures/desk_measured.yaml').read_text())
    cfg['desk_drawer_wall'].pop('joinery')
    path = tmp_path / 'opposed.yaml'
    path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError, match='Kolizja nawiertów'):
        _load_model(path)
