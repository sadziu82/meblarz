from pathlib import Path
import pytest
import yaml
from parts.desk_drawer_wall import load_desk_drawer_wall
from export_meblepl import export

PROJECT = Path(__file__).parents[1]/'projects/desk_drawer_wall.yaml'

@pytest.mark.parametrize('kind,thickness,depth', [('hdf_3',3,303),('mdf_3',3,303),('board_18',18,300)])
def test_drawer_bottom_variants(tmp_path,kind,thickness,depth):
    config=yaml.safe_load(PROJECT.read_text())
    config['desk_drawer_wall']['drawer_tower']['drawers']['bottom']['type']=kind
    path=tmp_path/'model.yaml'
    path.write_text(yaml.safe_dump(config))
    model=load_desk_drawer_wall(str(path))
    boards={b.name:b for b in model.boards}
    for index in range(5):
        prefix=f'tower_drawer_{index}_'
        bottom=boards[prefix+'bottom']
        front=boards[prefix+'front']
        assert (bottom.width,bottom.height,bottom.depth)==(538,thickness,depth)
        for name in ('side_left','side_right','rear'):
            side=boards[prefix+name]
            assert side.pos[2]==bottom.pos[2]+bottom.height
        if thickness==3:
            groove,=[g for g in front.grooves if g['kind']=='drawer_bottom']
            assert groove['depth']==3 and groove['span_z']==3
            assert bottom.pos[1]==front.pos[1]+front.depth-3
            assert front.pos[0]+groove['x']==bottom.pos[0]
            assert front.pos[2]+groove['z']==bottom.pos[2]
            assert not bottom.joint_holes
            assert len(bottom.holes)>=6
            for hole in bottom.holes:
                assert hole.through and hole.diameter==3 and hole.depth==3
                assert any(h.x==hole.x and h.y==hole.y and h.z==hole.z+3
                           and h.diameter==2 and h.depth==13
                           for name in ('side_left','side_right','rear')
                           for h in boards[prefix+name].holes)
        else:
            assert bottom.joint_holes
            assert not any(g['kind']=='drawer_bottom' for g in front.grooves)
    _,md,dxf=export(path,tmp_path/'export')
    assert 'MDF' not in md.read_text()
    assert 'Materiał: HDF biały' in md.read_text()
    assert ('Materiał: HDF, grubość 3 mm; dno szuflady.' in md.read_text()) == (thickness==3)
    assert ('Frez pod dno HDF' in md.read_text()) == (thickness==3)
    assert len([p for p in dxf.glob('*.dxf') if 'GROOVE_BOTTOM_W3_D3' in p.read_text()]) == (5 if thickness==3 else 0)
