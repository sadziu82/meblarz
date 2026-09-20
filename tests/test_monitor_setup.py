from pathlib import Path
import math
import pytest
import yaml
from parts.desk_drawer_wall import load_desk_drawer_wall
from export_meblepl import export

PROJECT = Path(__file__).parents[1] / 'projects/desk_drawer_wall.yaml'


def test_trial_fits_and_is_excluded_from_fabrication(tmp_path):
    model = load_desk_drawer_wall(str(PROJECT))
    boards = {b.name: b for b in model.boards}
    shelf = boards['desk_low_shelf']
    panel = boards['desk_stiffener_above_top']
    assert panel.pos[2]+panel.height - shelf.pos[2]-shelf.height == 32
    displays = [boards[f'monitor_preview_display_{i}'] for i in range(2)]
    for b in displays:
        assert not b.fabrication and not b.movable
        assert b.pos[2] - shelf.pos[2] - shelf.height == 50
        assert b.pos[2]+b.height < boards['module_bridge'].pos[2]
    def corners(b):
        c, s = math.cos(math.radians(b.yaw)), math.sin(math.radians(b.yaw))
        return [(b.pos[0]+c*x-s*y, b.pos[1]+s*x+c*y)
                for x in (0, b.width) for y in (0, b.depth)]
    left, right = map(corners, displays)
    assert displays[0].yaw == 5 and displays[1].yaw == -5
    assert min(x for x, y in left) - shelf.pos[0] == pytest.approx(10)
    assert min(x for x, y in right) - max(x for x, y in left) == pytest.approx(10)
    # Outer front edges are nearer the seated user than the inner edges.
    assert left[0][1] < left[2][1]
    assert right[2][1] < right[0][1]
    hole, = [h for h in shelf.holes if h.kind == 'monitor_trial']
    base = boards['monitor_preview_base']
    assert hole.x == base.pos[0]+base.width/2
    assert hole.y == base.pos[1]+base.depth/2
    assert hole.x == pytest.approx(shelf.pos[0]+shelf.width/2)
    assert shelf.pos[0]+shelf.width-max(x for x, y in right) == pytest.approx(98.30595944)
    def endpoints(board):
        c, s = math.cos(math.radians(board.yaw)), math.sin(math.radians(board.yaw))
        start = (board.pos[0]-s*board.depth/2, board.pos[1]+c*board.depth/2)
        return start, (start[0]+c*board.width, start[1]+s*board.width)
    for index in range(2):
        inner = boards[f'monitor_preview_arm_{index}_inner']
        outer = boards[f'monitor_preview_arm_{index}_outer']
        assert inner.width == pytest.approx(183.75)
        assert outer.width == pytest.approx(183.75)
        assert endpoints(inner)[0] == pytest.approx((hole.x, hole.y))
        assert endpoints(inner)[1] == pytest.approx(endpoints(outer)[0])
        vesa = boards[f'monitor_preview_vesa_{index}']
        c, s = math.cos(math.radians(vesa.yaw)), math.sin(math.radians(vesa.yaw))
        assert endpoints(outer)[1] == pytest.approx((vesa.pos[0]+57*c-6*s, vesa.pos[1]+57*s+6*c))
    assert endpoints(boards['monitor_preview_arm_1_inner'])[1][1] > hole.y
    csv, md, dxfs = export(PROJECT, tmp_path)
    assert 'monitor_preview' not in csv.read_text()
    assert 'monitor_preview' not in md.read_text()
    assert 'NIE jest eksportowany' in md.read_text()
    assert not any('monitor_preview' in p.name for p in dxfs.iterdir())
    from export_meblepl import _drilling_rows
    assert all(row[0] != 'prowadnica' for row in _drilling_rows(shelf))


def test_disable_and_invalid_position(tmp_path):
    config = yaml.safe_load(PROJECT.read_text())
    setup = config['desk_drawer_wall']['desk']['monitor_setup']
    path = tmp_path/'trial.yaml'
    setup['enabled'] = False
    path.write_text(yaml.safe_dump(config))
    model = load_desk_drawer_wall(str(path))
    assert not any(b.name.startswith('monitor_preview') for b in model.boards)
    assert not any(h.kind == 'monitor_trial' for b in model.boards for h in b.holes)
    setup.update(enabled=True, rear_offset=0)
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='base must fit'):
        load_desk_drawer_wall(str(path))
