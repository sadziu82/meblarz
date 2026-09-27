from pathlib import Path
import pytest
import yaml
from parts.shelves import shelf_geometry
from parts.kitchen_tall_unit import load_kitchen_tall_unit
from parts.desk_drawer_wall import load_desk_drawer_wall

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('value', [0, 10, 25])
def test_kitchen_shelf_setback_preserves_rear_and_structural_panels(tmp_path, value):
    cfg = yaml.safe_load((ROOT/'projects/kitchen_tall_unit.yaml').read_text())
    cfg['shelf_front_setback'] = value
    path = tmp_path/'kitchen.yaml';path.write_text(yaml.safe_dump(cfg))
    boards = {b.name:b for b in load_kitchen_tall_unit(str(path)).boards}
    side = boards['kitchen_right_side']
    shelf = boards['right_upper_shelf_0']
    assert shelf.pos[1]-side.pos[1] == value
    assert shelf.depth == side.depth-value
    assert shelf.pos[1]+shelf.depth == pytest.approx(side.pos[1]+side.depth)
    divider = boards['right_microwave_upper_divider']
    assert divider.depth == side.depth
    assert divider.pos[1] == side.pos[1]
    assert all(shelf.pos[1] <= h.y <= shelf.pos[1]+shelf.depth for h in shelf.joint_holes)


def test_desk_default_and_explicit_shelves(tmp_path):
    cfg = yaml.safe_load((ROOT/'projects/desk_drawer_wall.yaml').read_text())
    cfg.pop('shelf_front_setback', None)
    section = cfg['desk_drawer_wall']['drawer_tower']['upper_shelves']
    section.pop('front_setback', None);section.pop('depth', None)
    path = tmp_path/'desk.yaml';path.write_text(yaml.safe_dump(cfg))
    boards = {b.name:b for b in load_desk_drawer_wall(str(path)).boards}
    front = boards['tower_left_side'].pos[1]
    assert boards['tower_shelf_0'].pos[1]-front == 10
    assert boards['tower_secondary_shelf_0'].pos[1]-front == 70
    assert boards['overhead_shelf_0_0'].pos[1]-front == 20


def test_local_precedence_rear_clearance_and_invalid_sizes():
    assert shelf_geometry(300, {}, 10, 3) == (10, 287)
    assert shelf_geometry(300, {'front_setback':20}, 10, 3) == (20, 277)
    assert shelf_geometry(300, {'depth':200}, 10, 3) == (97, 200)
    for setback in [-1, 297, float('nan')]:
        with pytest.raises(ValueError):
            shelf_geometry(300, {'front_setback':setback}, 10, 3)
