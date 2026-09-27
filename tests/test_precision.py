from pathlib import Path
import pytest
from parts.precision import mm
from parts.materials import apply_finishes
from parts.drawer import Board, Hole
from parts.meble_pl_plan import make_plan
from export import _number


@pytest.mark.parametrize('value,expected', [(80.25,80.3), (80.249999999999,80.3),
                                          (80.24,80.2), (-80.25,-80.3), (3.2,3.2)])
def test_decimal_rounding(value, expected):
    assert mm(value) == expected
    assert float(_number(value)) == expected


def test_hole_rounding_is_local_and_keeps_spacing():
    board = Board('front', 596, 160.5, 18, (12.35, 0, 659.25))
    board.holes = [Hole(board.pos[0]+x,18,board.pos[2]+80.25,5,18,'+y','handle',True)
                   for x in (218,378)]
    apply_finishes([board], {})
    assert board.pos == (12.4,0,659.3)
    for hole in board.holes:
        assert hole.z-board.pos[2] == pytest.approx(80.3)
    assert board.holes[1].x-board.holes[0].x == pytest.approx(160)


def test_kitchen_plan_never_sends_hundredths():
    plan = make_plan(Path(__file__).resolve().parents[1]/'projects/kitchen_tall_unit.yaml')
    for group in plan['groups']:
        for board in group['boards']:
            values = [board[k] for k in ('width','height','thickness')]
            values += [value for hole in board['drills'] for value in hole.values()
                       if isinstance(value, (int,float))]
            for value in values:
                assert value*10 == pytest.approx(round(value*10)), (board['name'],value)
    top = next(b for g in plan['groups'] for b in g['boards'] if b['name']=='kitchen_drawer_2_front')
    handles = [h for h in top['drills'] if h['srednica']==5 and h['glebokosc']=='przelot']
    assert len(handles)==2
    assert all(h['wsp_y']==80.3 for h in handles)
