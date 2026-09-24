from pathlib import Path

import pytest
import yaml

from export_meblepl import (export, IncompleteMachiningError, write_meblepl_csv,
                            write_drilling_sheet, write_dxf_files, _dxf_drills)
from parts.kitchen_tall_unit import load_kitchen_tall_unit
from parts.drawer import Board, Hole
from parts.joinery import add_panel_joints, add_adjacent_cabinet_ties
from parts.machining import validate_drilling
from viewer import _movable_group


PROJECT = Path(__file__).parents[1] / 'projects/kitchen_tall_unit.yaml'


def load(tmp_path, change=None):
    config = yaml.safe_load(PROJECT.read_text())
    if change:
        change(config['kitchen_tall_unit'])
    path = tmp_path / 'kitchen.yaml'
    path.write_text(yaml.safe_dump(config))
    model = load_kitchen_tall_unit(path)
    return model, {b.name: b for b in model.boards}, path


@pytest.mark.parametrize('side', ['left', 'right'])
def test_complete_hinge_templates_and_lift_top(tmp_path, side):
    _, boards, _ = load(tmp_path, lambda c: c['left_column']['fridge']['fronts'].update(hinge_side=side))
    for name, count in [('fridge_lower_door', 2), ('fridge_upper_door', 3),
                        ('right_upper_left_door', 2), ('right_upper_right_door', 2)]:
        door = boards[name]
        cups = [h for h in door.holes if h.kind == 'hinge_cup']
        screws = [h for h in door.holes if h.kind == 'hinge_screw']
        assert len(cups) == count and len(screws) == 2 * count
        for cup, a, b in zip(cups, screws[::2], screws[1::2]):
            assert (cup.diameter, cup.depth, cup.direction) == (35, 12, '+y')
            assert abs(cup.x - a.x) == 9.5
            assert b.z - a.z == 45
            assert min(cup.x - door.pos[0], door.pos[0] + door.width - cup.x) == 20.5
    for name in ('kitchen_left_side', 'kitchen_left_right_side', 'kitchen_right_left_side', 'kitchen_right_side'):
        plate = [h for h in boards[name].holes if h.kind == 'hinge_plate']
        assert all(h.y - boards[name].pos[1] == 37 for h in plate)
        assert all(b.z - a.z == 32 for a, b in zip(plate[::2], plate[1::2]))
    top = boards['kitchen_top']
    plate = [h for h in top.holes if h.kind == 'hinge_plate']
    assert len(plate) == 4
    assert all(h.direction == '-z' and h.z == top.pos[2] for h in plate)
    assert plate[1].x - plate[0].x == 32

    for name in ('fridge_lower_door', 'fridge_upper_door'):
        door = boards[name]
        for i, fraction in enumerate((.25, .75)):
            connector = boards[f'{name}_sliding_connector_{i}']
            assert (connector.width, connector.height, connector.depth) == (90, 38, 12)
            assert connector.pos[0] + connector.width / 2 == pytest.approx(
                door.pos[0] + door.width * (.75 if side == 'left' else .25))
            assert connector.pos[2] + connector.height / 2 == pytest.approx(
                door.pos[2] + fraction * door.height)
            assert connector.pos[1] == door.pos[1] + door.depth
            assert connector.motion_parent == name and not connector.fabrication


def test_axis_cutlist_drilling_and_stationary_runners(tmp_path):
    model, boards, path = load(tmp_path)
    side = boards['kitchen_right_left_side']
    runner_holes = [h for h in side.holes if h.kind == 'axis_runner']
    assert len(runner_holes) == 9
    assert {h.y - side.pos[1] for h in runner_holes} == {37, 261, 389}
    for i, height in enumerate((199, 116, 84)):
        prefix = f'kitchen_drawer_{i}'
        bottom, rear, front = (boards[f'{prefix}_{part}'] for part in ('bottom', 'rear', 'front'))
        assert (bottom.width, bottom.depth, bottom.height) == (489, 576, 16)
        assert (rear.width, rear.height, rear.depth) == (477, height, 16)
        assert rear.pos[1] == bottom.pos[1] + bottom.depth
        assert rear.pos[0] - bottom.pos[0] == 6
        holes = [h for h in front.holes if h.kind == 'axis_front']
        assert len(holes) == (8 if i == 0 else 4)
        assert min(h.z - front.pos[2] for h in holes) == 47.5
        assert {h.x - front.pos[0] for h in holes} == {31.5, 564.5}
        assert all((h.diameter, h.depth) == (2, 12) for h in holes)
        assert len([h for h in rear.holes if h.kind == 'axis_rear']) == (4 if i == 2 else 6)
        fixed = boards[f'{prefix}_runner_left_0']
        moving = boards[f'{prefix}_runner_left_2']
        assert not fixed.movable and moving.movable
        assert _movable_group(moving) == prefix
        assert boards[f'{prefix}_axis_pro_left'].depth == 593
    with pytest.raises(IncompleteMachiningError):
        export(path, tmp_path / 'out')
    assert any('AXIS_RUNNER' in layer for _, layer in _dxf_drills(runner_holes[0]))


@pytest.mark.parametrize('top', ['shared', 'separate'])
@pytest.mark.parametrize('bottom', ['shared', 'separate'])
def test_joint_pairs_and_all_drills_stay_on_their_board(tmp_path, top, bottom):
    model, boards, _ = load(tmp_path, lambda c: c['panels'].update(top=top, bottom=bottom))
    assert len(model.joints) == 29
    assert ('kitchen_left_right_side', 'kitchen_right_left_side') in model.joints
    assert len([pair for pair in model.joints if 'fridge_upper_back' in pair]) == 4
    for board in boards.values():
        for h in board.holes + board.joint_holes:
            axis = 'xyz'.index(h.direction[-1])
            pos = [h.x, h.y, h.z]
            sizes = [board.width, board.depth, board.height]
            for n, (v, p, size) in enumerate(zip(pos, board.pos, sizes)):
                assert p <= v <= p + size, (board.name, h)
                if n == axis:
                    assert v == pytest.approx(p + size if h.direction[0] == '+' else p)
        for h in board.joint_holes:
            matches = [other for other in boards[h.partner].joint_holes
                       if other.partner == board.name and other.element != h.element
                       and other.hole_type == h.hole_type
                       and all(abs(getattr(other, a) - getattr(h, a)) < 1e-6
                               for a in 'xyz' if a != h.direction[-1])]
            assert len(matches) == 1, (board.name, h)
    for name in ('kitchen_left_side', 'kitchen_right_side'):
        assert all(h.hole_type == 'dowel' for h in boards[name].joint_holes if h.element == 1)
    assert {h.hole_type for h in boards['kitchen_right_left_side'].joint_holes} == {'confirmat', 'dowel'}


def test_column_tie_bores_follow_vertical_spacing_and_depth_offsets(tmp_path):
    _, boards, _ = load(tmp_path)
    left = boards['kitchen_left_right_side']
    right = boards['kitchen_right_left_side']
    through = [h for h in left.holes if h.kind == 'column_tie_through']
    other_through = [h for h in right.holes if h.kind == 'column_tie_through']
    assert len(through) == len(other_through) == 8
    assert sorted({h.z for h in through}) == [218, 912.5, 1607.5, 2302]
    assert {h.y-left.pos[1] for h in through} == {100, 510}
    assert all(h.x == left.pos[0] and h.direction == '-x'
               and (h.diameter, h.depth, h.through) == (3, 18, True) for h in through)
    assert all(h.x == right.pos[0] and h.direction == '-x'
               and (h.diameter, h.depth, h.through) == (3, 18, True) for h in other_through)
    assert {(h.y, h.z) for h in through} == {(h.y, h.z) for h in other_through}
    assert _dxf_drills(through[0]) == [(3, 'COLUMN_TIE_THROUGH_D3_THRU')]
    assert _dxf_drills(other_through[0]) == [(3, 'COLUMN_TIE_THROUGH_D3_THRU')]


def test_column_tie_yaml_can_change_or_disable_bores(tmp_path):
    def change(c):
        c['joinery']['column_ties'].update(first_above_bottom=150, last_below_top=120,
                                           front_offset=90, rear_offset=110)
    _, boards, _ = load(tmp_path, change)
    side = boards['kitchen_left_right_side']
    bores = [h for h in side.holes if h.kind == 'column_tie_through']
    assert min(h.z for h in bores) == 268
    assert max(h.z for h in bores) == 2282
    assert {h.y-side.pos[1] for h in bores} == {90, 500}

    _, boards, _ = load(tmp_path, lambda c: c['joinery']['column_ties'].update(enabled=False))
    assert not any(h.kind.startswith('column_tie_') for b in boards.values() for h in b.holes)

    with pytest.raises(ValueError, match='column_ties cannot meet'):
        load(tmp_path, lambda c: c['joinery']['column_ties'].update(min_spacing=700,
                                                                    max_spacing=710))



def test_adjacent_cabinet_ties_cover_every_pair_but_not_internal_partitions():
    cheeks = [
        Board('a_right', 18, 2284, 600, (282, 0, 118), movable=False,
              cabinet_id='a', cabinet_side='right'),
        Board('b_left', 18, 2284, 600, (300, 0, 118), movable=False,
              cabinet_id='b', cabinet_side='left'),
        Board('b_partition', 18, 2284, 600, (450, 0, 118), movable=False,
              cabinet_id='b'),
        Board('b_right', 18, 2284, 600, (582, 0, 118), movable=False,
              cabinet_id='b', cabinet_side='right'),
        Board('c_left', 18, 2200, 500, (600, 50, 200), movable=False,
              cabinet_id='c', cabinet_side='left'),
        Board('d_left', 18, 2284, 600, (1000, 0, 118), movable=False,
              cabinet_id='d', cabinet_side='left'),
    ]
    assert add_adjacent_cabinet_ties(cheeks) == [('a_right', 'b_left'),
                                                 ('b_right', 'c_left')]
    assert not cheeks[2].holes and not cheeks[5].holes
    assert len(cheeks[0].holes) == len(cheeks[1].holes) == 8
    assert len(cheeks[3].holes) == len(cheeks[4].holes) == 8
    assert {(h.y, h.z) for h in cheeks[3].holes} == {(h.y, h.z) for h in cheeks[4].holes}
    assert {h.y for h in cheeks[4].holes} == {150, 450}
    assert all(h.through and h.diameter == 3 for b in cheeks for h in b.holes)
    validate_drilling(cheeks)


def test_handles_follow_fronts_and_are_centred(tmp_path):
    model, boards, _ = load(tmp_path)
    fronts = [b for b in boards.values() if any(h.kind == 'handle' for h in b.holes)]
    assert len(fronts) == 8
    for front in fronts:
        a, b = [h for h in front.holes if h.kind == 'handle']
        assert (a.x - b.x)**2 + (a.z - b.z)**2 == 160**2
        assert a.through and b.through and a.diameter == b.diameter == 5
        preview = boards[f'{front.name}_handle_bar']
        assert not preview.fabrication and preview.motion_parent == front.name
        assert _movable_group(preview) == _movable_group(front)
        if front.name.startswith('kitchen_drawer_'):
            assert (a.x + b.x) / 2 == front.pos[0] + front.width / 2
            assert a.z == b.z == front.pos[2] + front.height / 2
        elif front.opening.startswith('hinge_'):
            edge = front.pos[0] + front.width if front.opening == 'hinge_left' else front.pos[0]
            assert abs(a.x - edge) == 50
        else:
            assert a.z == front.pos[2] + 50


@pytest.mark.parametrize('change, message', [
    (lambda c: c.update(depth=550), 'NL'),
    (lambda c: c['right_column']['drawers']['axis_pro'].update(variants=['D', 'B', 'D']), 'clear height'),
    (lambda c: c['right_column']['drawers']['axis_pro'].update(bottom_thickness=18), '16 mm'),
    (lambda c: c['handles'].update(door_edge_offset=1), 'Handle does not fit'),
])
def test_impossible_hardware_settings_rejected(tmp_path, change, message):
    with pytest.raises(ValueError, match=message):
        load(tmp_path, change)


def test_axis_nl_changes_panels_and_boring(tmp_path):
    _, boards, _ = load(tmp_path, lambda c: c['right_column']['drawers']['axis_pro'].update(nl=450))
    assert boards['kitchen_drawer_0_bottom'].depth == 426
    side = boards['kitchen_right_side']
    assert {h.y - side.pos[1] for h in side.holes if h.kind == 'axis_runner'} == {37, 229}


def test_yaml_size_changes_recalculate_all_hardware(tmp_path):
    def change(c):
        c.update(height=2500, depth=650)
        c['right_column']['width'] = 650
        c['right_column']['upper_cabinet']['shelves'] = 2
    model, boards, path = load(tmp_path, change)
    assert boards['kitchen_top'].width == 1400
    assert boards['kitchen_drawer_0_bottom'].width == 539
    assert boards['kitchen_drawer_0_rear'].width == 527
    assert boards['kitchen_drawer_0_front'].width == 646
    assert len(model.joints) == 31
    front = boards['kitchen_drawer_0_front']
    a, b = [h for h in front.holes if h.kind == 'handle']
    assert (a.x + b.x) / 2 == front.pos[0] + 323
    upper = boards['right_upper_left_door']
    assert upper.pos[2] + upper.height == 2497
    assert len(boards['right_upper_shelf_1'].joint_holes) == 8
    with pytest.raises(IncompleteMachiningError):
        export(path, tmp_path / 'export')


def test_joinery_uses_contacts_not_board_names():
    left = Board('arbitrary_A', 18, 300, 300, (0, 0, 0), movable=False)
    right = Board('arbitrary_B', 18, 300, 300, (582, 0, 0), movable=False)
    shelf = Board('arbitrary_C', 564, 18, 300, (18, 0, 100), movable=False)
    assert set(add_panel_joints([left, right, shelf])) == {('arbitrary_A', 'arbitrary_C'), ('arbitrary_B', 'arbitrary_C')}
    assert len(shelf.joint_holes) == 4
    validate_drilling([left, right, shelf])
    # A real collision is rejected, not fixed by moving either bore.
    left.holes.append(Hole(18, 50, 109, 3, 10, '+x', 'axis_runner'))
    positions = [(h.x, h.y, h.z) for h in left.joint_holes]
    with pytest.raises(ValueError, match='Kolizja.*arbitrary_A.*axis_runner'):
        validate_drilling([left, right, shelf])
    assert positions == [(h.x, h.y, h.z) for h in left.joint_holes]


def test_opposed_contacts_use_the_existing_mixed_joint_rule():
    side = Board('shared', 18, 300, 300, (0, 0, 0), movable=False)
    a = Board('first', 300, 18, 300, (-300, 0, 100), movable=False)
    b = Board('second', 300, 18, 300, (18, 0, 100), movable=False)
    add_panel_joints([side, a, b])
    assert {h.hole_type for h in side.joint_holes} == {'confirmat', 'dowel'}
    validate_drilling([side, a, b])


@pytest.mark.parametrize('depth,expected', [(300, []), (301, [150.5]), (600, [175, 425])])
def test_dowels_between_confirmats_only_above_200_mm(depth, expected):
    side = Board('side', 18, 300, depth, (0, 0, 0), movable=False)
    top = Board('top', 100, 18, depth, (0, 0, 300), movable=False)
    add_panel_joints([side, top])
    dowels = [h for h in top.joint_holes if h.hole_type == 'dowel']
    assert [h.y for h in dowels] == expected
    for hole in dowels:
        assert hole.direction == '-z' and hole.z == 300
        mate, = [h for h in side.joint_holes if h.hole_type == 'dowel' and h.y == hole.y]
        assert mate.direction == '+z' and mate.z == hole.z and mate.x == hole.x
    assert all(h.direction == '+z' and h.z == 318 for h in top.joint_holes
               if h.hole_type == 'confirmat')
    validate_drilling([side, top])


def test_incomplete_model_blocks_every_manufacturing_writer(tmp_path):
    model, boards, _ = load(tmp_path)
    assert {i['operation'] for i in model.machining_issues} == {
        'axis_bottom_fixing', 'gas_lift_mount', 'fridge_slider_mount', 'plinth_clip_mount'}
    assert all(name in boards for issue in model.machining_issues for name in issue['boards'])
    target = tmp_path / 'must_not_be_written'
    for write in (lambda: write_meblepl_csv(model, target),
                  lambda: write_drilling_sheet(model, target, 'test'),
                  lambda: write_dxf_files(model, target)):
        with pytest.raises(IncompleteMachiningError, match='AXIS PRO'):
            write()
        assert not target.exists()
