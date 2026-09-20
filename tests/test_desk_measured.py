from pathlib import Path

import pytest
import yaml

from parts.desk_drawer_wall import load_desk_drawer_wall
from export_meblepl import export

SOURCE = Path(__file__).parent / 'fixtures' / 'desk_measured.yaml'
PROJECT = Path(__file__).parents[1] / 'projects' / 'desk_drawer_wall.yaml'


@pytest.fixture
def boards():
    return {b.name: b for b in load_desk_drawer_wall(str(SOURCE)).boards}


def test_requested_dimensions(boards):
    top = boards['desk_top']
    assert (top.width, top.depth, top.pos[2]) == (1350, 600, 845)
    assert top.corner_radius == 200
    assert top.rounded_front_corners == (False, True)
    assert boards['tower_bottom'].width == 600
    assert boards['tower_bottom'].depth == 300
    assert boards['tower_drawer_top'].pos[2] == top.pos[2]
    assert boards['desk_low_shelf'].pos[2] - top.pos[2] - top.height == 80
    assert boards['module_bridge'].pos[2] + boards['module_bridge'].height == 1640
    assert boards['upper_top'].pos[2] + boards['upper_top'].height == 2400


def test_overlay_fronts_cover_sides_and_do_not_enter_carcass(boards):
    side = boards['tower_left_side']
    fronts = [boards[f'tower_drawer_{i}_front'] for i in range(4)]
    assert fronts[0].pos[2] == 3
    assert fronts[-1].pos[2] + fronts[-1].height == boards['desk_top'].pos[2] - 3
    for front in fronts:
        assert front.width == 594
        assert front.pos[0] == pytest.approx(side.pos[0] + 3)
        assert front.pos[1] + front.depth == pytest.approx(side.pos[1] - 2)
    for first, second in zip(fronts, fronts[1:]):
        assert second.pos[2] - first.pos[2] - first.height == pytest.approx(3)


def test_lower_storage_equal_spaces_and_secondary_setbacks(boards):
    bottom = boards['tower_drawer_top'].pos[2] + 18
    middle = boards['tower_shelf_0']
    ceiling = boards['module_bridge'].pos[2]
    assert middle.pos[2] - bottom == pytest.approx(ceiling - middle.pos[2] - 18)
    front = boards['tower_left_side'].pos[1]
    assert middle.pos[1] - front == 20
    for index, (lo, hi) in enumerate(((bottom, middle.pos[2]), (middle.pos[2] + 18, ceiling))):
        shelf = boards[f'tower_secondary_shelf_{index}']
        assert shelf.pos[1] - front == 70
        assert shelf.pos[2] - lo == pytest.approx(2 * (hi - shelf.pos[2] - 18))


def test_upper_four_columns_three_equal_and_middle_shelf(boards):
    shelves = [b for b in boards.values() if b.name.startswith('overhead_shelf_')]
    assert sorted(b.width for b in shelves) == [186, 564, 564, 564]
    floor = boards['module_bridge'].pos[2] + 18
    ceiling = boards['upper_top'].pos[2]
    for shelf in shelves:
        assert shelf.pos[2] - floor == pytest.approx(ceiling - shelf.pos[2] - 18)


def test_white_backs_fit_rear_rabbets(boards, tmp_path):
    for back_name, left_name, right_name in (
        ('tower_back', 'tower_left_side', 'tower_right_side'),
        ('upper_tower_back', 'upper_divider', 'upper_right_side'),
    ):
        back, left, right = (boards[n] for n in (back_name, left_name, right_name))
        assert back.color[:3] == (0.95, 0.95, 0.95)
        assert back.width == 584
        assert back.depth == 3
        assert back.pos[0] == left.pos[0] + left.width - 10
        assert back.pos[0] + back.width == right.pos[0] + 10
        assert back.pos[1] + back.depth == left.pos[1] + left.depth
        for side in (left, right):
            rabbet = next(g for g in side.grooves if g['kind'] == 'back_rabbet')
            assert (rabbet['width'], rabbet['depth'], rabbet['face']) == (10, 3, '+y')
    _, md, dxf = export(SOURCE, tmp_path)
    assert 'Wręg pod plecy' in md.read_text()
    assert len([p for p in dxf.glob('*.dxf') if 'RABBET_BACK_W10_D3' in p.read_text()]) == 4


@pytest.mark.parametrize('thickness', [18, 20])
def test_five_drawers_with_centred_through_handles(tmp_path, thickness):
    config = yaml.safe_load(SOURCE.read_text())
    drawers = config['desk_drawer_wall']['drawer_tower']['drawers']
    drawers['count'] = 5
    drawers['front']['handle'].update(vertical='center', hole_depth='through')
    config['material']['drawer_thickness'] = thickness
    source = tmp_path / 'five.yaml'
    source.write_text(yaml.safe_dump(config))
    model = load_desk_drawer_wall(str(source))
    fronts = [b for b in model.boards if b.name.startswith('tower_drawer_') and b.name.endswith('_front')]
    assert len(fronts) == 5
    for front in fronts:
        holes = [h for h in front.holes if h.kind == 'handle']
        assert len(holes) == 2
        assert (holes[0].x + holes[1].x) / 2 == pytest.approx(front.pos[0] + front.width / 2)
        assert abs(holes[0].x - holes[1].x) == pytest.approx(160)
        for hole in holes:
            assert hole.z == pytest.approx(front.pos[2] + front.height / 2)
            assert hole.depth == thickness
            assert hole.through
    _, md, dxf = export(source, tmp_path / 'export')
    assert 'na wylot' in md.read_text()
    assert len([p for p in dxf.glob('*.dxf') if 'HANDLE_D5_THRU' in p.read_text()]) == 5


def test_project_backs_meet_in_bridge_and_leave_drawers_open(tmp_path):
    boards = {b.name: b for b in load_desk_drawer_wall(str(PROJECT)).boards}
    lower, upper = boards['tower_back'], boards['upper_tower_back']
    bridge, floor = boards['module_bridge'], boards['tower_drawer_top']
    assert lower.pos[2] == floor.pos[2] + 6
    assert lower.pos[2] + lower.height == bridge.pos[2] + 6
    assert upper.pos[2] == bridge.pos[2] + 12
    assert (lower.width, lower.height, upper.width, upper.height) == (588, 777, 582, 760)
    assert floor.depth == 310
    # Every board/back intersection must lie entirely in the corresponding cut.
    for back in (lower, upper):
        for board in boards.values():
            if board is back:
                continue
            lo = [max(a, b) for a, b in zip(back.pos, board.pos)]
            hi = [min(a + size_a, b + size_b) for a, size_a, b, size_b in
                  zip(back.pos, (back.width, back.depth, back.height),
                      board.pos, (board.width, board.depth, board.height))]
            if any(b - a < 1e-6 for a, b in zip(lo, hi)):
                continue
            assert any(g['kind'] == 'back_rabbet' and
                       board.pos[0] + g['x'] <= lo[0] and
                       board.pos[0] + g['x'] + g['span_x'] >= hi[0] and
                       board.pos[2] + g['z'] <= lo[2] and
                       board.pos[2] + g['z'] + g['span_z'] >= hi[2] and
                       lo[1] >= board.pos[1] + board.depth - g['depth']
                       for g in board.grooves), (back.name, board.name)
    for name in ('tower_left_side', 'tower_right_side'):
        side = boards[name]
        groove = next(g for g in side.grooves if g['kind'] == 'back_rabbet')
        assert side.pos[2] + groove['z'] == lower.pos[2]
    fronts = [boards[f'tower_drawer_{i}_front'] for i in range(5)]
    assert [f.height for f in fronts] == [164] * 5
    assert all(f.width == 594 for f in fronts)
    for board in boards.values():
        if board.fabrication and 'slide_' not in board.name:
            assert all(value == round(value) for value in (board.width, board.height, board.depth)), board.name
        for hole in board.holes:
            if hole.kind == 'handle':
                assert hole.z - board.pos[2] == round(hole.z - board.pos[2])
                assert abs(hole.z - board.pos[2] - board.height / 2) <= 0.5
    assert fronts[0].pos[2] == 16
    assert boards['tower_bottom'].pos[2] + boards['tower_bottom'].height - fronts[0].pos[2] == 2
    assert fronts[-1].pos[2] + fronts[-1].height == pytest.approx(floor.pos[2] + 3)
    for first, second in zip(fronts, fronts[1:]):
        assert second.pos[2] - first.pos[2] - first.height == pytest.approx(3)
    _, md, dxf = export(PROJECT, tmp_path)
    assert '588 × 777' in md.read_text() or '777 × 588' in md.read_text()
    assert len([p for p in dxf.glob('*.dxf') if 'RABBET_BACK_W' in p.read_text()]) == 10
    bridge_dxf = next(p for p in dxf.glob('*module_bridge*.dxf') if 'RABBET_BACK_W' in p.read_text())
    # Two continuous rectangles: one per rear edge, four lines each.
    assert bridge_dxf.read_text().count('8\nRABBET_BACK_W6_D3.2\n') == 8
    assert 'RABBET_BACK_W12_D3.2' not in bridge_dxf.read_text()


def test_reject_overlapping_back_rabbets(tmp_path):
    config = yaml.safe_load(PROJECT.read_text())
    config['desk_drawer_wall']['drawer_tower']['back']['rabbet']['shared_width'] = 10
    source = tmp_path / 'invalid.yaml'
    source.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='half'):
        load_desk_drawer_wall(str(source))


def test_project_keyboard_clearance_and_gtv_xp_mounting(tmp_path):
    model = load_desk_drawer_wall(str(PROJECT))
    boards = {b.name: b for b in model.boards}
    tray, top = boards['keyboard_tray'], boards['desk_top']
    assert (tray.width, tray.depth, tray.height) == (1000, 500, 18)
    assert tray.pos[1] - top.pos[1] == 30
    assert top.pos[2] - tray.pos[2] - tray.height == 100
    assert tray.pos[0] + tray.width / 2 == top.pos[0] + top.width / 2
    assert tray.travel == 400
    assert tray.pos[1] + tray.depth <= top.pos[1] + top.depth
    left, right = boards['keyboard_hanger_left'], boards['keyboard_hanger_right']
    assert tray.pos[0] - left.pos[0] - left.width == pytest.approx(13)
    assert right.pos[0] - tray.pos[0] - tray.width == pytest.approx(13)
    for hanger in (left, right):
        assert hanger.pos[2] + hanger.height == top.pos[2]
        assert hanger.pos[1] - tray.pos[1] == 70
        assert (hanger.width, hanger.height, hanger.depth) == (18, 132, 400)
        assert [h.y - hanger.pos[1] for h in hanger.holes] == [37, 101, 197]
    assert sorted({h.y - tray.pos[1] for h in tray.holes}) == [105, 265, 362]
    assert all(h.depth == 10 and h.diameter == 3 for h in tray.holes)
    for side in ('left', 'right'):
        slide = boards[f'keyboard_tray_slide_{side}_outer']
        assert slide.pos[1] == boards[f'keyboard_hanger_{side}'].pos[1]
        assert slide.depth == 400
    _, md, _ = export(PROJECT, tmp_path)
    assert 'GTV Versalite Plus 400' in md.read_text()
    assert 'wymaga potwierdzenia' in md.read_text()


def test_desk_stiffeners_clear_keyboard_and_have_paired_joints():
    boards = {b.name: b for b in load_desk_drawer_wall(str(PROJECT)).boards}
    top, tray = boards['desk_top'], boards['keyboard_tray']
    rear = boards['tower_left_side'].pos[1] + boards['tower_left_side'].depth
    for key, offset, z in (('above_top', 0, 863), ('floor', 100, 0)):
        panel = boards[f'desk_stiffener_{key}']
        assert (panel.width, panel.height, panel.depth) == (1350, 130 if key == 'above_top' else 100, 18)
        assert panel.pos[2] == z
        assert rear - panel.pos[1] - panel.depth == offset
        for h in panel.joint_holes:
            partner = boards[h.partner]
            assert any(p.partner == panel.name and p.hole_type == h.hole_type
                       and all(getattr(p, axis) == getattr(h, axis)
                               for axis in 'xyz' if axis != h.direction[-1])
                       for p in partner.joint_holes)
            assert partner.pos[2] <= h.z <= partner.pos[2] + partner.height
    assert 'desk_stiffener_under_top' not in boards
    panel = boards['desk_stiffener_above_top']
    assert panel.pos[2] == top.pos[2] + top.height
    low = boards['desk_low_shelf']
    assert low.pos[1] + low.depth == panel.pos[1]
    assert low.depth == 180
    for support in (b for b in boards.values() if b.name.startswith('desk_low_shelf_support_')):
        assert support.pos[1] + support.depth == panel.pos[1]
    for name in ('keyboard_tray', 'keyboard_hanger_left', 'keyboard_hanger_right'):
        board = boards[name]
        assert board.pos[2] + board.height <= panel.pos[2]
    assert tray.travel - (tray.pos[1] - top.pos[1]) == 370


def test_overhead_desk_backs_fit_rabbets_and_shelves():
    boards = {b.name: b for b in load_desk_drawer_wall(str(PROJECT)).boards}
    backs = [boards[f'upper_desk_back_{i}'] for i in range(3)]
    assert [b.width for b in backs] == [204, 576, 576]
    for back in backs:
        assert (back.height, back.depth) == (760, 3)
        assert back.color == (0.95, 0.95, 0.95, 1)
        assert back.pos[2] == 1634
        for board in boards.values():
            if board is back or not board.fabrication:
                continue
            lo = [max(a,b) for a,b in zip(back.pos, board.pos)]
            hi = [min(a+sa,b+sb) for a,sa,b,sb in zip(
                back.pos, (back.width,back.depth,back.height),
                board.pos, (board.width,board.depth,board.height))]
            if any(end-start < 1e-6 for start,end in zip(lo,hi)):
                continue
            assert any(g['kind'] == 'back_rabbet' and
                       board.pos[0]+g['x'] <= lo[0] and
                       board.pos[0]+g['x']+g['span_x'] >= hi[0] and
                       board.pos[2]+g['z'] <= lo[2] and
                       board.pos[2]+g['z']+g['span_z'] >= hi[2]
                       for g in board.grooves), board.name
    for left, right in zip(backs, backs[1:]+[boards['upper_tower_back']]):
        assert right.pos[0] - left.pos[0] - left.width == 6
    for b in boards.values():
        if b.name.startswith('overhead_shelf_'):
            assert b.depth == 287
    assert 'desk_back' not in boards


def test_desktop_led_stops_inside_rounded_outline(tmp_path):
    import math
    board = next(b for b in load_desk_drawer_wall(str(PROJECT)).boards if b.name == 'desk_top')
    groove, = [g for g in board.grooves if g['kind'] == 'led']
    start, end = groove['x'], groove['x']+groove['span_x']
    assert start == 0
    assert end < board.width-20
    for y in (groove['offset']-groove['width']/2, groove['offset']+groove['width']/2):
        edge = board.width-board.corner_radius+math.sqrt(board.corner_radius**2-(y-board.corner_radius)**2)
        assert edge-end >= 20
    _, md, dxf = export(PROJECT, tmp_path)
    assert f'Zakres lokalnego X: {int(start)}–{int(end)} mm' in md.read_text()
    path = next(p for p in dxf.glob('*desk_top*.dxf') if 'GROOVE_LED' in p.read_text())
    text = path.read_text()
    assert f'10\n{int(start)}\n' in text
    assert f'11\n{int(end)}\n' in text


def test_project_led_dimensions_and_clearances(tmp_path):
    boards = {b.name:b for b in load_desk_drawer_wall(str(PROJECT)).boards}
    drawer_lights = [boards[f'tower_drawer_rail_{i}'] for i in range(4)] + [boards['tower_drawer_top']]
    for board in drawer_lights:
        groove, = [g for g in board.grooves if g['kind']=='led']
        assert (groove['width'],groove['depth']) == (10,4)
        assert groove['offset']-groove['width']/2 == 20
        assert groove['x']==20
        assert board.width-groove['x']-groove['span_x']==20
    for name in ('tower_shelf_0','tower_secondary_shelf_0','tower_secondary_shelf_1',
                 'module_bridge','desk_low_shelf','overhead_shelf_0_0',
                 'overhead_shelf_0_0_bay1','overhead_shelf_0_0_bay2','overhead_shelf_0_0_tower'):
        board=boards[name]
        groove, = [g for g in board.grooves if g['kind']=='led']
        assert (groove['width'],groove['depth']) == (10,4)
        assert groove['offset']-groove['width']/2==50
        margin = 15 if name == 'module_bridge' else 0
        assert groove['x']==0
        assert board.width-groove['x']-groove['span_x']==margin
    assert not any(g['kind']=='led' for g in boards['keyboard_tray'].grooves)
    _,md,dxf=export(PROJECT,tmp_path)
    assert not any('keyboard_tray--' in p.name and 'GROOVE_LED' in p.read_text() for p in dxf.iterdir())
    assert any('tower_drawer_top' in p.name and 'GROOVE_LED_W10_D4' in p.read_text() for p in dxf.iterdir())


def test_hidden_confirmats_and_dowelled_upper_feet(tmp_path):
    boards = {b.name: b for b in load_desk_drawer_wall(str(PROJECT)).boards}
    bridge, top = boards['module_bridge'], boards['upper_top']
    for name in ('upper_left_side', 'upper_right_side', 'upper_divider',
                 'upper_desk_divider_0', 'upper_desk_divider_1'):
        bottom = [h for h in bridge.joint_holes if h.partner == name and h.hole_type == 'dowel']
        upper = [h for h in top.joint_holes if h.partner == name]
        assert bottom and upper
        assert all(h.hole_type == 'dowel' and h.direction == '+z' for h in bottom)
        assert all(h.hole_type == 'confirmat' and h.direction == '+z'
                   and h.z == top.pos[2] + top.height for h in upper)
    for name in ('upper_desk_divider_0', 'upper_desk_divider_1', 'upper_divider'):
        shared = boards[name]
        shelf_holes = [h for h in shared.joint_holes if h.partner.startswith('overhead_shelf_')]
        assert {h.hole_type for h in shelf_holes} == {'confirmat', 'dowel'}
        for screw in (h for h in shelf_holes if h.hole_type == 'confirmat'):
            assert all(abs(screw.y-dowel.y) >= 20
                       for dowel in shelf_holes if dowel.hole_type == 'dowel')
    for h in bridge.joint_holes:
        if h.partner == 'desk_bridge_support':
            assert h.hole_type == 'dowel'
        elif h.partner in ('desk_left_side', 'tower_left_side', 'tower_right_side'):
            assert h.hole_type == 'confirmat' and h.direction == '+z'
    for board in boards.values():
        for h in board.joint_holes:
            if h.hole_type != 'confirmat' or h.element != 1:
                continue
            axis = h.direction[-1]
            partner = boards[h.partner]
            pilot, = [p for p in partner.joint_holes if p.partner == board.name
                      and p.element == 2 and p.hole_type == 'confirmat'
                      and all(getattr(p, a) == getattr(h, a) for a in 'xyz' if a != axis)]
            thickness = dict(x=board.width, y=board.depth, z=board.height)[axis]
            assert abs(getattr(pilot, axis)-getattr(h, axis)) == thickness
    _, _, dxf = export(PROJECT, tmp_path)
    top_file = next(p for p in dxf.glob('*upper_top*') if 'Drill from +z;' in p.read_text())
    assert 'COUNTERSINK_D11_DEPTH4.5' in top_file.read_text()


def test_desktop_attached_to_both_sides():
    boards = {b.name: b for b in load_desk_drawer_wall(str(PROJECT)).boards}
    top = boards['desk_top']
    for name in ('desk_left_side', 'tower_left_side'):
        side = boards[name]
        fasteners = [h for h in top.joint_holes if h.partner == name]
        assert len(fasteners) == 2
        assert all(h.element == 2 and h.hole_type == 'confirmat' for h in fasteners)
        for hole in fasteners:
            head, = [h for h in side.joint_holes if h.partner == top.name
                     and (h.y, h.z) == (hole.y, hole.z)]
            assert head.hole_type == 'confirmat'
            assert abs(head.x-hole.x) == side.width
            assert side.pos[1] <= hole.y <= side.pos[1]+side.depth
    shared = boards['tower_left_side']
    heads = [h for h in shared.joint_holes if h.partner == top.name]
    dowels = [h for h in shared.joint_holes if h.partner == 'tower_drawer_top']
    assert all(h.hole_type == 'dowel' for h in dowels)
    assert all(abs(h.y-d.y) >= 20 for h in heads for d in dowels)


def test_upper_rear_confirmats_are_accessible_behind_support():
    boards = {b.name: b for b in load_desk_drawer_wall(str(PROJECT)).boards}
    bridge, support = boards['module_bridge'], boards['desk_bridge_support']
    heads = [h for h in bridge.joint_holes if h.hole_type == 'confirmat'
             and h.partner.startswith('upper_')]
    assert {h.partner for h in heads} == {'upper_desk_divider_0', 'upper_desk_divider_1'}
    assert len(heads) == 2
    for head in heads:
        assert head.direction == '-z' and head.z == bridge.pos[2]
        assert head.y > support.pos[1]+support.depth+5.5
        assert bridge.pos[1]+bridge.depth-head.y == 30
        side = boards[head.partner]
        pilot, = [h for h in side.joint_holes if h.partner == bridge.name and h.hole_type == 'confirmat']
        assert (pilot.x, pilot.y) == (head.x, head.y)
        assert pilot.z == side.pos[2] and pilot.direction == '-z'
        assert len([h for h in side.joint_holes if h.partner == bridge.name and h.hole_type == 'dowel']) == 2
