from pathlib import Path

import pytest
import yaml

from parts.drawer import _resolve_handle, _load_slides_db
from parts.desk_drawer_wall import load_desk_drawer_wall
from export_meblepl import export

PROJECT = Path(__file__).parents[1] / 'projects/desk_drawer_wall.yaml'


@pytest.mark.parametrize('model,spacing', [
    ('GOODHOME-ATOMIA-293-BLACK', 256),
    ('GTV-UA-337-160-BLACK', 160),
    ('GTV-UA-337-320-ALUMINIUM', 320),
])
def test_library_handle_drilling(tmp_path, model, spacing):
    cfg = yaml.safe_load(PROJECT.read_text())
    cfg['desk_drawer_wall']['drawer_tower']['drawers']['front']['handle']['model'] = model
    path = tmp_path / 'handle.yaml'
    path.write_text(yaml.safe_dump(cfg))
    m = load_desk_drawer_wall(str(path))
    fronts = [b for b in m.boards if b.name.startswith('tower_drawer_') and b.name.endswith('_front')]
    assert len(fronts) == 5
    for b in fronts:
        holes = [h for h in b.holes if h.kind == 'handle']
        assert abs(holes[0].x - holes[1].x) == spacing
        assert (holes[0].x + holes[1].x) / 2 == b.pos[0] + b.width / 2
        assert all(h.through and h.depth == 18 and h.diameter == 3 for h in holes)
    assert _resolve_handle({'model': model, 'hole_diameter': 4})['hole_diameter'] == 4


def test_sevroll_depth_clearance_and_independent_drill_patterns(tmp_path):
    cfg = yaml.safe_load(PROJECT.read_text())
    cfg['desk_drawer_wall']['drawer_tower']['drawers']['slides']['model'] = 'SEVROLL-04897'
    source = tmp_path / 'sevroll.yaml'
    source.write_text(yaml.safe_dump(cfg))
    m = load_desk_drawer_wall(str(source))
    b = {b.name: b for b in m.boards}
    assert m.slide_nl == 300 and m.max_travel == 268
    side = b['tower_drawer_0_side_left']
    carcass = b['tower_left_side']
    bottom = b['tower_drawer_0_bottom']
    assert carcass.depth == 310
    assert bottom.depth == 303  # 300 mm box plus 3 mm tongue inside front groove
    assert side.depth == 282  # full-width rear panel occupies the remaining 18 mm
    assert bottom.width == 538  # 600 - 2*18 - 2*13
    assert side.pos[0] - carcass.pos[0] - carcass.width == 13
    assert carcass.pos[1] + carcass.depth - bottom.pos[1] - bottom.depth == 12
    assert [h.y - side.pos[1] for h in side.holes if h.kind == 'slide'] == [35, 204]
    assert [h.y - side.pos[1] for h in carcass.holes if h.z == side.holes[0].z] == [37, 133]
    _, md, dxf = export(source, tmp_path)
    assert 'GoodHome Atomia' in md.read_text()
    assert '268 mm' in md.read_text()
    assert len([p for p in dxf.glob('*.dxf') if 'HANDLE_D3_THRU' in p.read_text()]) == 5


def test_gtv_alternative_and_undermount_guard(tmp_path):
    cfg = yaml.safe_load(PROJECT.read_text())
    slide = cfg['desk_drawer_wall']['drawer_tower']['drawers']['slides']
    path = tmp_path / 'gtv.yaml'
    slide['model'] = 'GTV-PK-L-H45-300-B'
    path.write_text(yaml.safe_dump(cfg))
    assert load_desk_drawer_wall(str(path)).max_travel == 296
    slide['model'] = 'GTV-PB-G10HX300-H'
    path.write_text(yaml.safe_dump(cfg))
    assert _load_slides_db()[slide['model']]['max_side_thickness_mm'] == 16
    with pytest.raises(ValueError, match='dolnego montażu'):
        load_desk_drawer_wall(str(path))


def test_handle_preview_matches_holes_and_is_not_cut_list(tmp_path):
    model = load_desk_drawer_wall(str(PROJECT))
    boards = {b.name: b for b in model.boards}
    for index in range(5):
        prefix = f'tower_drawer_{index}_'
        front = boards[prefix+'front']
        bar = boards[prefix+'handle_bar']
        assert (bar.width, bar.height) == (293, 23)
        assert front.pos[1]-bar.pos[1] == 20.5
        assert bar.pos[0]+bar.width/2 == front.pos[0]+front.width/2
        for n, hole in enumerate(h for h in front.holes if h.kind == 'handle'):
            mount = boards[prefix+f'handle_mount_{n}']
            assert mount.pos[0]+mount.width/2 == hole.x
            assert mount.pos[2]+mount.height/2 == hole.z
            assert mount.pos[1]+mount.depth == front.pos[1]
            assert mount.movable and not mount.fabrication
        assert bar.movable and not bar.fabrication
    csv, md, dxf = export(PROJECT, tmp_path)
    assert 'handle_bar' not in csv.read_text()
    assert 'handle_mount' not in csv.read_text()
    assert not any('handle_bar' in p.name or 'handle_mount' in p.name for p in dxf.iterdir())
