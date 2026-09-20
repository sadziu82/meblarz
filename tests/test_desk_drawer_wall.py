from pathlib import Path

import pytest
import yaml

from parts.desk_drawer_wall import load_desk_drawer_wall
from export_meblepl import export


YAML_PATH = Path(__file__).parent / 'fixtures' / 'desk_drawer_wall.yaml'


@pytest.fixture(scope='module')
def model():
    return load_desk_drawer_wall(str(YAML_PATH))


@pytest.fixture(scope='module')
def boards(model):
    return {board.name: board for board in model.boards}


def test_drawer_tower_and_desk_are_present(model, boards):
    assert model.drawer_count == 4
    assert 'desk_top' in boards
    assert 'tower_left_side' in boards
    assert len([name for name in boards if name.startswith('tower_drawer_') and name.endswith('_front')]) == 4


def test_keyboard_tray_has_own_travel(boards):
    tray = boards['keyboard_tray']
    assert tray.movable
    assert tray.travel == pytest.approx(250)


def test_handles_and_led_grooves_are_exportable(boards):
    front = boards['tower_drawer_0_front']
    assert len([hole for hole in front.holes if hole.kind == 'handle']) == 2
    assert boards['desk_top'].grooves[0]['kind'] == 'led'
    assert boards['tower_drawer_rail_0'].grooves[0]['kind'] == 'led'


def test_configured_storage_elements_are_present(boards):
    assert 'tower_back' in boards
    assert not any(name.startswith('overhead_cabinet_') for name in boards)
    assert 'overhead_shelf_1_0' in boards


def test_led_groove_is_written_to_dxf(tmp_path):
    _, _, dxf_dir = export(YAML_PATH, tmp_path)
    desk_dxf = next(dxf_dir.glob('*desk_top--minus-z.dxf'))
    content = desk_dxf.read_text(encoding='ascii')
    assert 'GROOVE_LED_W12_D4' in content
    assert '\nARC\n' in content


def test_rear_alignment_and_full_height_side(boards):
    rear = boards['upper_top'].pos[1] + boards['upper_top'].depth
    for name in ('desk_left_side', 'desk_top', 'desk_low_shelf', 'overhead_shelf_0_0',
                 'overhead_shelf_1_0', 'upper_top'):
        board = boards[name]
        assert board.pos[1] + board.depth == pytest.approx(rear)
    left, top, tower = (boards[name] for name in ('desk_left_side', 'desk_top', 'tower_left_side'))
    assert left.height == boards['module_bridge'].pos[2]
    assert top.pos[0] == pytest.approx(left.pos[0] + left.width)
    assert top.pos[0] + top.width == pytest.approx(tower.pos[0])
    assert top.pos[1] < tower.pos[1]  # extra desktop depth extends towards the user
    assert boards['keyboard_tray'].pos[1] == pytest.approx(top.pos[1])


@pytest.mark.parametrize('supports', [1, 2])
@pytest.mark.parametrize('span,side', [('full', 'left'), ('partial', 'left'), ('partial', 'right')])
def test_low_shelf_supports_touch_desktop_and_shelf(tmp_path, supports, span, side):
    config = yaml.safe_load(YAML_PATH.read_text())
    low = config['desk_drawer_wall']['desk']['low_shelf']
    low.update(supports=supports, span=span, side=side, width=600)
    path = tmp_path / 'desk.yaml'
    path.write_text(yaml.safe_dump(config))
    boards = {b.name: b for b in load_desk_drawer_wall(str(path)).boards}
    top, shelf = boards['desk_top'], boards['desk_low_shelf']
    legs = [b for b in boards.values() if b.name.startswith('desk_low_shelf_support_')]
    assert len(legs) == supports
    for leg in legs:
        assert leg.pos[2] == pytest.approx(top.pos[2] + top.height)
        assert leg.pos[2] + leg.height == pytest.approx(shelf.pos[2])
        assert shelf.pos[0] <= leg.pos[0] <= shelf.pos[0] + shelf.width - leg.width
        assert leg.pos[1] == pytest.approx(shelf.pos[1])


def test_static_boards_do_not_intersect(model):
    boards = [b for b in model.boards if not b.movable]
    for index, first in enumerate(boards):
        for second in boards[index + 1:]:
            overlap = [min(a + da, b + db) - max(a, b)
                       for a, da, b, db in zip(first.pos, (first.width, first.depth, first.height),
                                              second.pos, (second.width, second.depth, second.height))]
            assert not all(length > 1e-6 for length in overlap), (first.name, second.name, overlap)


def test_overhead_shelves_fit_between_sides(boards):
    for shelf in (b for b in boards.values() if b.name.startswith('overhead_shelf_')):
        left, right = ((boards['upper_divider'], boards['upper_right_side']) if shelf.name.endswith('_tower')
                       else (boards['upper_left_side'], boards['upper_divider']))
        assert shelf.pos[0] == pytest.approx(left.pos[0] + left.width)
        assert shelf.pos[0] + shelf.width == pytest.approx(right.pos[0])
        assert shelf.pos[2] + shelf.height <= left.pos[2] + left.height


def test_module_bridge_is_one_board_and_sides_touch_it(boards):
    bridge = boards['module_bridge']
    assert bridge.width == 2200
    for name in ('desk_left_side', 'tower_left_side', 'tower_right_side'):
        side = boards[name]
        assert side.pos[2] + side.height == pytest.approx(bridge.pos[2])
    for name in ('upper_left_side', 'upper_divider', 'upper_right_side'):
        side = boards[name]
        assert side.pos[2] == pytest.approx(bridge.pos[2] + bridge.height)
        assert side.pos[2] + side.height == pytest.approx(boards['upper_top'].pos[2])


def test_low_shelf_thirds_and_side_fasteners(boards):
    shelf = boards['desk_low_shelf']
    for index in range(2):
        support = boards[f'desk_low_shelf_support_{index}']
        assert support.pos[0] + support.width / 2 == pytest.approx(shelf.pos[0] + (index + 1) * shelf.width / 3)
    for side in ('desk_left_side', 'tower_left_side'):
        assert len([h for h in shelf.joint_holes if h.partner == side]) >= 2
        assert len([h for h in boards[side].joint_holes if h.partner == shelf.name]) >= 2


@pytest.mark.parametrize('position,offset', [('center', 250), ('offset', 100), ('offset', 450)])
def test_keyboard_position_hangers_and_slide_clearance(tmp_path, position, offset):
    config = yaml.safe_load(YAML_PATH.read_text())
    config['desk_drawer_wall']['desk']['keyboard_tray'].update(position=position, offset_left=offset)
    path = tmp_path / 'desk.yaml'
    path.write_text(yaml.safe_dump(config))
    boards = {b.name: b for b in load_desk_drawer_wall(str(path)).boards}
    tray, top = boards['keyboard_tray'], boards['desk_top']
    if position == 'center':
        assert tray.pos[0] + tray.width / 2 == pytest.approx(top.pos[0] + top.width / 2)
    else:
        assert tray.pos[0] - top.pos[0] == pytest.approx(offset)
    left, right = boards['keyboard_hanger_left'], boards['keyboard_hanger_right']
    assert tray.pos[0] - (left.pos[0] + left.width) == pytest.approx(12.5)
    assert right.pos[0] - (tray.pos[0] + tray.width) == pytest.approx(12.5)
    for hanger in (left, right):
        assert not hanger.movable
        assert hanger.pos[2] + hanger.height == pytest.approx(top.pos[2])
        assert len(hanger.holes) >= 2
        assert len([h for h in hanger.joint_holes if h.partner == top.name]) >= 2
    assert len(tray.holes) >= 4


def test_keyboard_offset_rejects_overlap_with_sides(tmp_path):
    config = yaml.safe_load(YAML_PATH.read_text())
    config['desk_drawer_wall']['desk']['keyboard_tray'].update(position='offset', offset_left=0)
    path = tmp_path / 'desk.yaml'
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='must fit between desk sides'):
        load_desk_drawer_wall(str(path))
