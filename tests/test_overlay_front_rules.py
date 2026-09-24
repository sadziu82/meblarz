from pathlib import Path

import pytest
import yaml

from parts.dresser import load_dresser
from parts.drawer import load_drawer
from parts.front_rules import split_front_heights
from parts.kitchen_tall_unit import load_kitchen_tall_unit

PROJECTS = Path(__file__).resolve().parents[1] / 'projects'


def test_dresser_overlay_reveals(tmp_path):
    cfg = yaml.safe_load((PROJECTS / 'dresser.yaml').read_text())
    cfg['front']['mount'] = 'overlay'
    cfg['drawers']['distribution'] = 'equal'
    path = tmp_path / 'dresser.yaml'
    path.write_text(yaml.safe_dump(cfg))
    boards = {b.name: b for b in load_dresser(str(path)).boards}
    fronts = [boards[f'drawer_{i}_front'] for i in range(cfg['drawers']['count'])]
    side = boards['carcass_left_side']
    assert fronts[0].pos[0] - side.pos[0] == 2
    assert fronts[0].width == cfg['carcass']['width'] - 4
    assert fronts[0].pos[2] == cfg['plinth']['height'] + 3
    assert fronts[-1].pos[2] + fronts[-1].height == cfg['carcass']['height'] - 3
    for a, b in zip(fronts, fronts[1:]):
        assert b.pos[2] - a.pos[2] - a.height == 3


def test_standalone_overlay_dimensions(tmp_path):
    cfg = yaml.safe_load((PROJECTS / 'drawer.yaml').read_text())
    cfg['front']['mount'] = 'overlay'
    cfg['front']['carcass_thickness'] = 18
    path = tmp_path / 'drawer.yaml'
    path.write_text(yaml.safe_dump(cfg))
    front = next(b for b in load_drawer(str(path)).boards if b.name == 'front')
    assert front.width == cfg['niche']['width'] + 36 - 4
    assert front.height == cfg['niche']['height'] + 36 - 6


def test_double_doors_have_two_mm_centre_gap():
    b = {b.name: b for b in load_kitchen_tall_unit(str(PROJECTS / 'kitchen_tall_unit.yaml')).boards}
    left, right = b['right_upper_left_door'], b['right_upper_right_door']
    assert left.width == right.width == 297
    assert right.pos[0] - left.pos[0] - left.width == 2
    assert left.pos[0] - b['kitchen_right_left_side'].pos[0] == 2
    assert b['kitchen_right_side'].pos[0] + 18 - right.pos[0] - right.width == 2


def test_half_mm_distribution_preserves_total():
    heights = split_front_heights(821, 5)
    assert sum(heights) == 821
    assert max(heights) - min(heights) <= 0.5
    with pytest.raises(ValueError):
        split_front_heights(821.2, 5)
