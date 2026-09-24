from pathlib import Path

import yaml
import pytest

from export_meblepl import export, IncompleteMachiningError, _dxf_file, _drilling_rows, _dxf_drills
from parts.kitchen_tall_unit import load_kitchen_tall_unit
from parts.kitchen_ventilation import (guide_rectangles, guide_marker_points,
                                       routable_guide_rectangles)
from viewer import _movable_group


PROJECT = Path(__file__).parents[1] / 'projects/kitchen_tall_unit.yaml'


def test_plinth_front_inset_uses_existing_parameter_and_keeps_rear_edge(tmp_path):
    config = yaml.safe_load(PROJECT.read_text())
    path = tmp_path / 'plinth.yaml'
    for inset in (0, 10, 20):
        config['kitchen_tall_unit']['plinth']['inset_front'] = inset
        path.write_text(yaml.safe_dump(config))
        boards = {b.name: b for b in load_kitchen_tall_unit(str(path)).boards}
        front = boards['kitchen_plinth_front']
        carcass = boards['kitchen_bottom']
        assert (front.pos[1] - carcass.pos[1], front.depth) == (inset, 18)
        for name in ('kitchen_plinth_left', 'kitchen_plinth_right'):
            side = boards[name]
            assert side.pos[1] == front.pos[1] + front.depth
            assert side.pos[1] + side.depth == carcass.pos[1] + carcass.depth
        assert any(g['kind'] == 'ventilation_cut_guide' for g in front.grooves)

    config['kitchen_tall_unit']['plinth']['inset_front'] = 600
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='plinth.inset_front'):
        load_kitchen_tall_unit(str(path))


@pytest.mark.parametrize('top', ['shared', 'separate'])
@pytest.mark.parametrize('bottom', ['shared', 'separate'])
def test_independent_end_panel_modes(tmp_path, top, bottom):
    config = yaml.safe_load(PROJECT.read_text())
    config['kitchen_tall_unit']['panels'] = {'top': top, 'bottom': bottom}
    path = tmp_path / 'panels.yaml'
    path.write_text(yaml.safe_dump(config))
    model = load_kitchen_tall_unit(str(path))
    for end, mode, z in [('top', top, config['kitchen_tall_unit']['height'] - 18), ('bottom', bottom, 100)]:
        panels = [b for b in model.boards if b.name.startswith(f'kitchen_{end}')]
        assert len(panels) == (1 if mode == 'shared' else 2)
        assert [b.width for b in panels] == ([1350] if mode == 'shared' else [750, 600])
        assert all((b.height, b.depth, b.pos[2]) == (18, 610, z) for b in panels)
        assert all(b.fabrication and not b.movable for b in panels)
        if mode == 'separate':
            assert panels[0].pos[0] + panels[0].width == panels[1].pos[0]
    with pytest.raises(IncompleteMachiningError):
        export(path, tmp_path / 'export')
    assert not (tmp_path / 'export').exists()
    boards = {board.name: board for board in model.boards}
    grille = boards['kitchen_plinth_front']
    assert any(g['kind'] == 'ventilation_cut_guide' for g in grille.grooves)
    assert len([h for h in grille.holes if h.kind == 'ventilation_cut_marker']) == 6
    for name in ('kitchen_top', 'kitchen_bottom'):
        mode = top if name.endswith('top') else bottom
        panel = boards[name if mode == 'shared' else name + '_left']
        guide, = [g for g in panel.grooves if g['kind'] == 'ventilation_cut_guide']
        assert (guide['outline'], guide['face'], guide['width'], guide['height']) == ('rear_u', '+z', 500, 40)
        assert len(guide_rectangles(guide)) == 3
        assert len(routable_guide_rectangles(panel, guide)) == 1
        assert len(guide_marker_points(panel, guide)) == 6


def test_invalid_panel_mode_is_rejected(tmp_path):
    config = yaml.safe_load(PROJECT.read_text())
    config['kitchen_tall_unit']['panels']['bottom'] = 'invalid'
    path = tmp_path / 'invalid.yaml'
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='panels.bottom'):
        load_kitchen_tall_unit(str(path))


def test_ventilation_guides_are_parametric_and_keep_full_boards(tmp_path):
    config = yaml.safe_load(PROJECT.read_text())
    vent = config['kitchen_tall_unit']['fridge_ventilation']
    vent['guide'] = {'width': 4.3, 'depth': 3}
    vent['openings']['plinth'] = {'width': 450, 'height': 35, 'bottom_offset': 25}
    for name, depth in [('bottom', 45), ('middle', 50), ('top', 35)]:
        vent['openings'][name] = {'width': 450, 'depth': depth}
    path = tmp_path / 'vent.yaml'
    path.write_text(yaml.safe_dump(config))
    boards = {b.name: b for b in load_kitchen_tall_unit(str(path)).boards}
    for name, depth in [('kitchen_bottom', 45), ('fridge_top_divider', 50), ('kitchen_top', 35)]:
        board = boards[name]
        guide, = [g for g in board.grooves if g['kind'] == 'ventilation_cut_guide']
        assert (guide['width'], guide['height'], guide['groove_width'], guide['depth']) == (450, depth, 4.3, 3)
        assert guide['y'] + guide['height'] == board.depth
        assert board.width == (714 if name == 'fridge_top_divider' else 1350)
        assert len(guide_rectangles(guide)) == 3
        assert len(guide_marker_points(board, guide)) in (4, 6)
    plinth = boards['kitchen_plinth_front']
    guide, = [g for g in plinth.grooves if g['kind'] == 'ventilation_cut_guide']
    assert (guide['width'], guide['height'], guide['z']) == (450, 35, 25)
    assert plinth.width == 1350
    back = boards['fridge_upper_back']
    assert back.pos[1] - boards['kitchen_top'].pos[1] == 532
    assert boards['kitchen_top'].pos[1] + 610 - 50 - (back.pos[1] + back.depth) == 10

    vent['upper_back']['clearance'] = 15
    path.write_text(yaml.safe_dump(config))
    changed = {b.name: b for b in load_kitchen_tall_unit(str(path)).boards}
    assert changed['fridge_upper_back'].pos[1] == back.pos[1] - 5

    vent['upper_back']['clearance'] = -1
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='upper_back'):
        load_kitchen_tall_unit(str(path))

    vent['enabled'] = False
    path.write_text(yaml.safe_dump(config))
    disabled = load_kitchen_tall_unit(str(path))
    assert not any(g['kind'] == 'ventilation_cut_guide' for b in disabled.boards for g in b.grooves)
    assert not any(h.kind == 'ventilation_cut_marker' for b in disabled.boards for h in b.holes)
    assert not any(b.name == 'fridge_upper_back' for b in disabled.boards)


def test_ventilation_guide_dxf_keeps_rectangular_board_outline(tmp_path):
    boards = {b.name: b for b in load_kitchen_tall_unit(str(PROJECT)).boards}
    for name, direction, count in [('kitchen_plinth_front', '-y', 8),
                                   ('kitchen_top', '+z', 4)]:
        board = boards[name]
        grooves = [g for g in board.grooves if g['kind'] == 'ventilation_cut_guide']
        markers = [h for h in board.holes if h.kind == 'ventilation_cut_marker']
        path = tmp_path / f'{name}.dxf'
        _dxf_file(board, direction, markers, grooves, path)
        content = path.read_text()
        assert content.count('\n8\nGROOVE_VENT_GUIDE_W3.2_D2\n') == count
        assert content.count('\n8\nVENT_CUT_MARKER_D3_DEPTH2\n') == 6
        assert content.count('\n8\nOUTLINE\n') == 4
        assert 'CUTOUT_VENT' not in content


def test_ventilation_marker_rows_start_and_end_five_mm_from_unroutable_groove():
    boards = {b.name: b for b in load_kitchen_tall_unit(str(PROJECT)).boards}
    plinth = boards['kitchen_plinth_front']
    top = boards['kitchen_top']
    plinth_points = guide_marker_points(plinth, plinth.grooves[0])
    top_points = guide_marker_points(top, top.grooves[0])
    assert {z for _, z in plinth_points} == {35, 50, 65}
    assert {y for _, y in top_points} == {575, 590, 605}
    assert {x for x, _ in plinth_points} == {125, 625}
    assert {x for x, _ in top_points} == {125, 625}
    for board in (plinth, top):
        markers = [h for h in board.holes if h.kind == 'ventilation_cut_marker']
        assert len(markers) == 6
        assert all((h.diameter, h.depth, h.through) == (3, 2, False) for h in markers)
        rows = [row for row in _drilling_rows(board)
                if row[0] == 'znacznik ręcznego wycięcia wentylacji']
        assert len(rows) == 6
        assert all(row[-1] == 'Ø3, głębokość 2 mm' for row in rows)


def test_ventilation_edge_limit_selects_grooves_instead_of_markers(tmp_path):
    config = yaml.safe_load(PROJECT.read_text())
    config['kitchen_tall_unit']['fridge_ventilation']['guide']['max_edge_offset'] = 130
    path = tmp_path / 'edge.yaml'
    path.write_text(yaml.safe_dump(config))
    boards = {b.name: b for b in load_kitchen_tall_unit(str(path)).boards}
    top = boards['kitchen_top']
    guide, = [g for g in top.grooves if g['kind'] == 'ventilation_cut_guide']
    assert len(routable_guide_rectangles(top, guide)) == 2
    assert len(guide_marker_points(top, guide)) == 3
    middle = boards['fridge_top_divider']
    guide, = [g for g in middle.grooves if g['kind'] == 'ventilation_cut_guide']
    assert len(routable_guide_rectangles(middle, guide)) == 3
    assert not guide_marker_points(middle, guide)


def test_two_column_appliance_layout_and_axis_drawers(tmp_path):
    model = load_kitchen_tall_unit(str(PROJECT))
    boards = {board.name: board for board in model.boards}
    assert (boards['kitchen_top'].width, boards['kitchen_top'].height,
                boards['kitchen_top'].depth) == (1350, 18, 610)
    fridge = boards['appliance_fridge_samsung_brb38g705dwwef']
    assert (fridge.width, fridge.height, fridge.depth) == (690, 1935, 520)
    freezer = boards['appliance_fridge_samsung_brb38g705dwwef_freezer_door']
    cooler = boards['appliance_fridge_samsung_brb38g705dwwef_refrigerator_door']
    assert cooler.pos[2] - freezer.pos[2] - freezer.height == 64
    assert fridge.pos[1] + fridge.depth - freezer.pos[1] == 550
    assert cooler.pos[2] + cooler.height == fridge.pos[2] + 1882
    assert not freezer.fabrication and not cooler.fabrication
    assert freezer.pos[2] - fridge.pos[2] == 50
    assert freezer.height == 621
    assert cooler.pos[2] - fridge.pos[2] == 735
    assert cooler.height == 1147
    lower_panel = boards['fridge_lower_door']
    upper_panel = boards['fridge_upper_door']
    lower_top = lower_panel.pos[2] + lower_panel.height
    assert upper_panel.pos[2] - lower_top == 3
    assert (upper_panel.pos[2] + lower_top) / 2 == (
        freezer.pos[2] + freezer.height + cooler.pos[2]) / 2
    assert boards['fridge_top_lift_door'].opening == 'lift_up'
    assert boards['fridge_lower_door'].opening == 'hinge_left'
    assert boards['fridge_upper_door'].opening == 'hinge_left'
    assert boards['fridge_lower_door'].height == 716.5
    assert boards['fridge_upper_door'].height == 1234.5
    assert boards['fridge_upper_door'].pos[2] + boards['fridge_upper_door'].height == 2057
    assert boards['fridge_top_lift_door'].pos[2] == 2060
    assert boards['fridge_top_lift_door'].width == 746
    assert _movable_group(boards['fridge_top_lift_door']) == 'fridge_top_lift_door'
    oven = boards['appliance_oven_electrolux_eoe7c31z']
    microwave = boards['appliance_microwave_electrolux_ems4253tmk']
    assert (oven.width, oven.height, oven.depth) == (560, 589, 550)
    assert (microwave.width, microwave.height, microwave.depth) == (560, 380, 357)
    fronts = [boards[f'kitchen_drawer_{i}_front'] for i in range(3)]
    assert [front.height for front in fronts] == [300, 250, 160.5]
    assert fronts[0].pos[2] == 103
    assert fronts[-1].pos[2] + fronts[-1].height == 819.5
    assert all(front.width == 596 and front.depth == 18 for front in fronts)
    rails = [b for b in boards.values() if b.name.startswith('kitchen_drawer_rail_')]
    assert len(rails) == 2
    for rail, lower, upper in zip(rails, fronts, fronts[1:]):
        assert (rail.width, rail.height, rail.depth) == (564, 18, 100)
        assert rail.fabrication and not rail.movable
        assert rail.pos[2] + rail.height / 2 == (lower.pos[2] + lower.height + upper.pos[2]) / 2
        assert rail.pos[1] >= lower.pos[1] + lower.depth
    for index in range(3):
        bottom = boards[f'kitchen_drawer_{index}_bottom']
        assert (bottom.width, bottom.height, bottom.depth) == (489, 16, 576)
        assert not boards[f'kitchen_drawer_{index}_axis_pro_left'].fabrication
    assert [boards[f'kitchen_drawer_{index}_axis_pro_left'].height for index in range(3)] == [200, 120, 86]
    oven_front = boards['appliance_oven_electrolux_eoe7c31z_front']
    microwave_front = boards['appliance_microwave_electrolux_ems4253tmk_front']
    assert microwave.pos[1] + microwave.depth - microwave_front.pos[1] == 377
    assert microwave_front.pos[1] + microwave_front.depth == microwave.pos[1]
    assert boards['right_microwave_upper_divider'].pos[2] - microwave.pos[2] == 380
    assert (oven_front.width, oven_front.height, oven_front.depth) == (596, 589, 20)
    assert (microwave_front.width, microwave_front.height, microwave_front.depth) == (595, 388, 20)
    assert oven_front.pos[2] == oven.pos[2] + 5
    assert microwave_front.pos[2] == microwave.pos[2] - 4.5
    assert oven_front.pos[2] - (fronts[-1].pos[2] + fronts[-1].height) == 8
    support = boards['right_drawer_top']
    assert support.pos[2] + support.height == oven.pos[2]
    assert oven_front.pos[2] + oven_front.height == oven.pos[2] + 594
    assert oven.pos[2] - (fronts[-1].pos[2] + fronts[-1].height) == 3
    divider = boards['right_oven_microwave_divider']
    assert divider.pos[2] - (support.pos[2] + support.height) == 590
    assert oven_front.pos[2] + oven_front.height - divider.pos[2] == 4
    assert microwave_front.pos[2] - (oven_front.pos[2] + oven_front.height) == 9.5
    assert len([board for board in boards.values() if board.name.startswith('right_upper_') and board.name.endswith('_door')]) == 2
    assert boards['right_upper_left_door'].pos[2] - (microwave_front.pos[2] + microwave_front.height) == 3
    assert boards['right_upper_left_door'].pos[2] + boards['right_upper_left_door'].height == yaml.safe_load(PROJECT.read_text())['kitchen_tall_unit']['height'] - 3
    assert not any(board.name == 'right_upper_divider' for board in boards.values())
    assert len([board for board in boards.values() if board.name.startswith('right_upper_shelf_')]) == 1
    assert 'appliance_oven_electrolux_eoe7c31z_front_glass' in boards
    assert 'appliance_microwave_electrolux_ems4253tmk_front_control_panel' in boards
    assert boards['appliance_oven_electrolux_eoe7c31z_front_photo'].texture.endswith('eoe7c31z_front.png')
    assert not boards['appliance_microwave_electrolux_ems4253tmk_front_photo'].fabrication
    for name in ('fridge_lower_door', 'fridge_upper_door', 'right_upper_left_door', 'right_upper_right_door'):
        assert boards[name].opening in ('hinge_left', 'hinge_right')
    for name in ('right_upper_left_door', 'right_upper_right_door'):
        assert any(h.kind == 'hinge_cup' and h.diameter == 35 for h in boards[name].holes)
    for name in ('fridge_lower_door', 'fridge_upper_door'):
        assert any(h.kind == 'hinge_cup' for h in boards[name].holes)
    assert len([b for b in boards.values() if 'sliding_connector' in b.name]) == 4
    assert not any(h.kind == 'gas_lift_mount' for b in boards.values() for h in b.holes)
    grille, = [g for g in boards['kitchen_plinth_front'].grooves if g['kind'] == 'ventilation_cut_guide']
    assert (grille['width'], grille['height'], grille['groove_width'], grille['depth']) == (500, 40, 3.2, 2)
    assert len(guide_rectangles(grille)) == 4
    middle, = [g for g in boards['fridge_top_divider'].grooves if g['kind'] == 'ventilation_cut_guide']
    assert (middle['width'], middle['height'], middle['y']) == (500, 40, 570)
    back = boards['fridge_upper_back']
    assert (back.width, back.height, back.depth, back.pos[1] - boards['kitchen_top'].pos[1]) == (714, 326, 18, 542)
    assert boards['kitchen_top'].pos[1] + middle['y'] - (back.pos[1] + back.depth) == 10
    assert back.fabrication and not back.movable
    assert back.color == boards['kitchen_left_side'].color
    assert {h.partner for h in back.joint_holes} == {
        'kitchen_left_side', 'kitchen_left_right_side', 'kitchen_top', 'fridge_top_divider'}
    with pytest.raises(IncompleteMachiningError):
        export(PROJECT, tmp_path / 'export')
    legs = [b for b in boards.values() if b.name.startswith('kitchen_leg_')]
    assert len(legs) == 32
    assert all(not b.fabrication and not b.movable for b in legs)
    for column in ('left', 'right'):
        bottom = boards['kitchen_bottom']
        for side in ('left', 'right'):
            for row in ('front', 'rear'):
                prefix = f'kitchen_leg_{column}_{side}_{row}'
                foot, plate = boards[f'{prefix}_foot'], boards[f'{prefix}_plate']
                assert foot.pos[2] == 0
                assert foot.preview_shape == 'cylinder_z'
                assert plate.pos[2] + plate.height == bottom.pos[2]
                assert bottom.pos[0] <= plate.pos[0] < plate.pos[0] + plate.width <= bottom.pos[0] + bottom.width
                assert bottom.pos[1] + 18 <= plate.pos[1] < plate.pos[1] + plate.depth <= bottom.pos[1] + bottom.depth


def test_leg_height_follows_plinth_and_can_be_disabled(tmp_path):
    config = yaml.safe_load(PROJECT.read_text())
    config['kitchen_tall_unit']['plinth']['height'] = 120
    path = tmp_path / 'legs.yaml'
    path.write_text(yaml.safe_dump(config))
    model = load_kitchen_tall_unit(str(path))
    plates = [b for b in model.boards if b.name.startswith('kitchen_leg_') and b.name.endswith('_plate')]
    assert len(plates) == 8
    assert all(b.pos[2] + b.height == 120 for b in plates)
    config['kitchen_tall_unit']['legs']['enabled'] = False
    path.write_text(yaml.safe_dump(config))
    disabled = load_kitchen_tall_unit(str(path))
    assert not any(b.name.startswith('kitchen_leg_') for b in disabled.boards)
    assert not any(h.kind == 'kitchen_leg_mount' for b in disabled.boards for h in b.holes)


@pytest.mark.parametrize('bottom_mode', ['shared', 'separate'])
def test_kitchen_leg_fixing_pattern_follows_each_bottom_panel(tmp_path, bottom_mode):
    config = yaml.safe_load(PROJECT.read_text())
    config['kitchen_tall_unit']['panels']['bottom'] = bottom_mode
    path = tmp_path / 'leg_pattern.yaml'
    path.write_text(yaml.safe_dump(config))
    model = load_kitchen_tall_unit(str(path))
    boards = {b.name: b for b in model.boards}
    bottoms = [b for b in model.boards if b.name.startswith('kitchen_bottom')]
    assert len(bottoms) == (1 if bottom_mode == 'shared' else 2)
    assert sum(len([h for h in b.holes if h.kind == 'kitchen_leg_mount']) for b in bottoms) == 32
    for bottom in bottoms:
        leg_holes = [h for h in bottom.holes if h.kind == 'kitchen_leg_mount']
        assert all(_dxf_drills(h) == [(2.5, 'KITCHEN_LEG_MOUNT_D2.5_DEPTH12')]
                   for h in leg_holes)
        assert len([row for row in _drilling_rows(bottom)
                    if row[0] == 'mocowanie nóżki kuchennej']) == len(leg_holes)
    for column, width in (('left', 750), ('right', 600)):
        bottom = boards['kitchen_bottom' if bottom_mode == 'shared' else f'kitchen_bottom_{column}']
        start_on_bottom = 750 if bottom_mode == 'shared' and column == 'right' else 0
        for side_name, centre_x in (('left', start_on_bottom + 65),
                                    ('right', start_on_bottom + width - 65)):
            for row in ('front', 'rear'):
                plate = boards[f'kitchen_leg_{column}_{side_name}_{row}_plate']
                cx = plate.pos[0] + plate.width / 2
                cy = plate.pos[1] + plate.depth / 2
                assert (plate.width, plate.depth, cx - bottom.pos[0]) == (78, 83, centre_x)
                holes = [h for h in bottom.holes if h.kind == 'kitchen_leg_mount'
                         and abs(h.x-cx) <= 32 and abs(h.y-cy) <= 32]
                assert len(holes) == 4
                assert {(h.x-cx, h.y-cy) for h in holes} == {
                    (-32, -32), (-32, 32), (32, -32), (32, 32)}
                assert all((h.z, h.direction, h.diameter, h.depth, h.through) ==
                           (bottom.pos[2], '-z', 2.5, 12, False) for h in holes)


def test_kitchen_leg_model_and_height_are_validated(tmp_path):
    config = yaml.safe_load(PROJECT.read_text())
    path = tmp_path / 'legs.yaml'
    config['kitchen_tall_unit']['legs']['model'] = 'unknown'
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='Unknown kitchen leg model'):
        load_kitchen_tall_unit(str(path))
    config['kitchen_tall_unit']['legs']['model'] = 'EMUCA-BONE-2024417'
    config['kitchen_tall_unit']['plinth']['height'] = 150
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='adjustment range'):
        load_kitchen_tall_unit(str(path))


def test_microwave_side_cutout_is_centred_behind_appliance_and_marked_from_inside():
    boards = {board.name: board for board in load_kitchen_tall_unit(str(PROJECT)).boards}
    side = boards['kitchen_right_side']
    appliance = boards['appliance_microwave_electrolux_ems4253tmk']
    guide, = [g for g in side.grooves if g['kind'] == 'manual_cutout_guide']
    assert (guide['face'], guide['y'], guide['span_y'], guide['span_z']) == ('-x', 490, 120, 280)
    assert side.pos[2] + guide['z'] == appliance.pos[2] + 50
    assert side.pos[2] + guide['z'] + guide['span_z'] == appliance.pos[2] + 330
    assert side.pos[1] + guide['y'] >= appliance.pos[1] + appliance.depth
    marks = [h for h in side.holes if h.kind == 'manual_cutout_marker']
    assert len(marks) == 12
    assert all((h.x, h.direction, h.diameter, h.depth, h.through) ==
               (side.pos[0], '-x', 3, 2, False) for h in marks)
    bottom_points = {h.y-side.pos[1] for h in marks if h.z == appliance.pos[2] + 50}
    assert {495, 605} <= bottom_points
    side_points = {h.z for h in marks if h.y-side.pos[1] == 490}
    assert {appliance.pos[2] + 55, appliance.pos[2] + 325} <= side_points
    assert all(h.y < side.pos[1] + side.depth for h in marks)
    assert len(bottom_points) == len(side_points) == 4


def test_microwave_side_cutout_dxf_marks_inner_face_without_cutting_board(tmp_path):
    boards = {board.name: board for board in load_kitchen_tall_unit(str(PROJECT)).boards}
    side = boards['kitchen_right_side']
    markers = [h for h in side.holes if h.kind == 'manual_cutout_marker']
    guides = [g for g in side.grooves if g['kind'] == 'manual_cutout_guide']
    path = tmp_path / 'right_side_inner.dxf'
    _dxf_file(side, '-x', markers, guides, path)
    content = path.read_text()
    assert content.count('\n8\nMANUAL_CUT_MARKER_D3_DEPTH2\n') == 12
    assert content.count('\n8\nMANUAL_CUT_GUIDE_NOT_TOOLPATH\n') == 4
    assert content.count('\n8\nOUTLINE\n') == 4
    rows = [row for row in _drilling_rows(side)
            if row[0] == 'znacznik ręcznego wycięcia za mikrofalą']
    assert len(rows) == 12
    assert all(row[4:] == ('-x', 'Ø3, głębokość 2 mm') for row in rows)


def test_microwave_side_cutout_yaml_dimensions_and_validation(tmp_path):
    config = yaml.safe_load(PROJECT.read_text())
    cutout = config['kitchen_tall_unit']['right_column']['microwave']['side_cutout']
    cutout.update(depth=100, height=200, rear_offset=10)
    path = tmp_path / 'with_cutout.yaml'
    path.write_text(yaml.safe_dump(config))
    boards = {board.name: board for board in load_kitchen_tall_unit(str(path)).boards}
    guide, = [g for g in boards['kitchen_right_side'].grooves if g['kind'] == 'manual_cutout_guide']
    assert (guide['y'], guide['span_y'], guide['span_z']) == (500, 100, 200)
    assert len([h for h in boards['kitchen_right_side'].holes
                if h.kind == 'manual_cutout_marker']) == 16
    assert boards['kitchen_right_side'].pos[2] + guide['z'] == (
        boards['appliance_microwave_electrolux_ems4253tmk'].pos[2] + 90)
    cutout['enabled'] = False
    path.write_text(yaml.safe_dump(config))
    disabled = {board.name: board for board in load_kitchen_tall_unit(str(path)).boards}
    assert not any(g['kind'] == 'manual_cutout_guide'
                   for g in disabled['kitchen_right_side'].grooves)
    cutout.update(enabled=True, height=400)
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='Microwave side cutout'):
        load_kitchen_tall_unit(str(path))
