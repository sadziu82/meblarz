from pathlib import Path
import pytest
from parts.drawer import Board
from parts.desk_drawer_wall import _add_led_groove, load_desk_drawer_wall
from export_meblepl import export

@pytest.mark.parametrize('edge,direction', [('rear','+y'),('left','-x'),('right','+x')])
def test_wire_entry_axis_and_depth(edge,direction):
    board=Board('shelf',564,18,287,(10,20,30))
    cfg=dict(enabled=True,width=10,depth=4,offset=55,wire_entry=dict(enabled=True,edge=edge))
    _add_led_groove(board,cfg)
    hole,=board.holes
    assert (hole.diameter,hole.depth,hole.direction,hole.through)==(4,35,direction,False)
    assert hole.z==39
    assert board.grooves[0]['wire_entry']['bridge']==3
    if edge=='rear':
        assert hole.y==307
    else:
        assert hole.y==75
        assert hole.x==(10 if edge=='left' else 574)
    board=Board('shelf',564,18,287,(0,0,0))
    cfg['wire_entry']['enabled']=False
    _add_led_groove(board,cfg)
    assert not board.holes


def test_project_wiring_export(tmp_path):
    path=Path(__file__).parents[1]/'projects/desk_drawer_wall.yaml'
    model=load_desk_drawer_wall(str(path))
    lit=[b for b in model.boards if any(g['kind']=='led' for g in b.grooves)]
    assert lit
    for board in lit:
        assert not any(h.kind == 'led_wire_entry' for h in board.holes)
        leds = [g for g in board.grooves if g['kind'] == 'led']
        wires = [g for g in board.grooves if g['kind'] == 'led_wire']
        assert len(leds) == len(wires)
        for led, wire in zip(leds, wires):
            assert (wire['width'], wire['depth']) == (3.2, 3)
            assert wire['y'] == led['offset']
            assert wire['y'] + wire['span_y'] == board.depth
            assert wire['x'] == (10 if board.name == 'desk_top' else led['x'])
            assert wire['face'] == led['face']
    _,md,dxf=export(path,tmp_path)
    assert 'Rowek przewodu LED: 3.2 × 3 mm' in md.read_text()
    assert 'nawiert startowy' not in md.read_text()
    assert len([p for p in dxf.iterdir() if 'GROOVE_LED_WIRE_W3.2_D3' in p.read_text()])==len(lit)


@pytest.mark.parametrize('side', ['left', 'right'])
@pytest.mark.parametrize('margin', [0, 15])
def test_surface_channel_connects_to_stopped_led(side, margin):
    board = Board('shelf', 564, 18, 287, (10, 20, 30))
    _add_led_groove(board, dict(enabled=True, width=10, depth=4, offset=55,
        end_margin=margin, wire_groove=dict(enabled=True, side=side)))
    led, wire = board.grooves
    assert wire['x'] >= led['x']
    assert wire['x'] + wire['span_x'] <= led['x'] + led['span_x']
    assert wire['y'] == led['offset']
    assert wire['y'] + wire['span_y'] == board.depth
    assert not board.holes


def test_top_lighting_is_one_continuous_run():
    path = Path(__file__).parents[1] / 'projects/desk_drawer_wall.yaml'
    boards = {b.name: b for b in load_desk_drawer_wall(str(path)).boards}
    top = boards['upper_top']
    groove, = [g for g in top.grooves if g['kind'] == 'led']
    wire, = [g for g in top.grooves if g['kind'] == 'led_wire']
    assert groove['x'] == 0
    assert groove['span_x'] == top.width - 18
    assert groove['offset'] - groove['width']/2 == 50
    assert groove['face'] == '-z' and groove['depth'] == 4
    assert wire['x'] == groove['x']
    for board in boards.values():
        rebates = [(g['face'], g['edge']) for g in board.grooves if g['kind'] == 'back_rabbet']
        assert len(rebates) == len(set(rebates)), board.name
