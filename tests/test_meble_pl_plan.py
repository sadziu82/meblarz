from pathlib import Path
import pytest
import yaml
from parts.drawer import Board, Hole
from parts.materials import material_selections
from parts.meble_pl_plan import make_plan, drill, save_plan
from export import export, IncompleteMachiningError
from cutting import main

ROOT=Path(__file__).resolve().parents[1]


def test_drawer_plan_supported_operations_and_exact_edges(tmp_path):
    plan=make_plan(ROOT/'projects/drawer.yaml')
    assert len(plan['groups'])==1
    boards={b['name']:b for b in plan['groups'][0]['boards']}
    assert sum(len(b['drills']) for b in boards.values())==64
    assert len(plan['manual'])==0
    assert boards['side_left']['edges']=={'top':.8}
    assert boards['rear']['edges']=={'left':.8,'right':.8,'top':.8}
    assert {d['powierzchnia'] for d in boards['front']['drills']}=={'B'}
    assert any(d.get('wsp_x')==93 and d.get('wsp_y')==941 for d in boards['bottom']['drills'])
    save_plan(plan,tmp_path)
    assert 'Pogłębienia pod łby' in (tmp_path/'raport.md').read_text()
    edge_pilots=[d for b in boards.values() for d in b['drills'] if d['kind']=='edge' and d['srednica']==4]
    assert len(edge_pilots)==16
    assert all(d['glebokosc']==35 for d in edge_pilots)
    slide_marks=[d for b in boards.values() for d in b['drills'] if d['kind']=='face' and d['srednica']==3 and d['glebokosc']!='przelot']
    assert len(slide_marks)==20
    assert all(d['glebokosc']==3 for d in slide_marks)
    confirmat_through_holes=[d for b in boards.values() for d in b['drills'] if d['glebokosc']=='przelot']
    assert len(confirmat_through_holes)==16
    assert all(d['srednica']==5 for d in confirmat_through_holes)


def test_kitchen_missing_materials_fails_before_browser(tmp_path,capsys):
    config=yaml.safe_load((ROOT/'projects/kitchen_tall_unit.yaml').read_text())
    del config['kitchen_tall_unit']['material']['boards_by_thickness'][18]
    project=tmp_path/'kitchen.yaml'
    project.write_text(yaml.safe_dump(config))
    assert main(['--vendor', 'meble.pl', str(project),'--dry-run',
                 '--output-dir',str(tmp_path/'out')])==2
    assert 'Brak wyboru płyty dla grubości: 18 mm.' in capsys.readouterr().err
    assert not (tmp_path/'out').exists()


def test_each_thickness_explicit_and_manufacturing_gate_unchanged(tmp_path):
    config=yaml.safe_load((ROOT/'projects/kitchen_tall_unit.yaml').read_text())
    material=config['kitchen_tall_unit']['material']
    material.pop('boards_by_thickness', None)
    material['board']='EGGER-H1318-ST10'
    project=tmp_path/'kitchen.yaml';project.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError,match='16 mm'):
        make_plan(project)
    material['boards_by_thickness']={16:dict(name='Wybrana biała 16 mm',
        meble_pl=dict(decor='W1000',structure='ST9',manufacturer='EGGER'))}
    project.write_text(yaml.safe_dump(config))
    plan=make_plan(project)
    assert {g['thickness'] for g in plan['groups']}=={16,18}
    sixteen=next(g for g in plan['groups'] if g['thickness']==16)
    assert len(sixteen['boards'])==6
    assert plan['unresolved']
    assert not any('connector' in b['name'] for g in plan['groups'] for b in g['boards'])
    with pytest.raises(IncompleteMachiningError):export(project,tmp_path/'production')


def test_axis_mapping_front_back_and_edge_centres():
    # Side remains upright: u=Y, v=Z, broad A face has normal +X.
    b=Board('side',18,700,600,(100,200,300),movable=False)
    h=Hole(100,250,400,3,12,'-x')
    d,error=drill(b,h,3,12)
    assert error is None and (d['wsp_x'],d['wsp_y'],d['powierzchnia'])==(50,100,'B')
    h.x=118;h.direction='+x'
    assert drill(b,h,3,12)[0]['powierzchnia']=='A'
    h=Hole(109,250,1000,8,27,'+z')
    d,error=drill(b,h,8,27)
    assert error is None and (d['krawedz'],d['odleglosc_x'])==('top',50)
    h.x=108
    assert drill(b,h,8,27)[0] is None


def test_invalid_or_unsupported_operations_are_not_rounded():
    b=Board('front',400,300,18,(0,0,0))
    h=Hole(50,18,50,2.5,10,'+y')
    assert drill(b,h,2.5,10)[0] is None
    assert drill(b,h,5,4.5)[0] is None
    assert drill(b,h,5,18,True)[0]['glebokosc']=='przelot'
    assert material_selections({'board':'EGGER-H1318-ST10','thickness':18}).keys()=={18}


def test_axis_bottom_fixing_is_reported_as_assembly_work(tmp_path):
    plan=make_plan(ROOT/'projects/kitchen_tall_unit.yaml')
    assert {i['operation'] for i in plan['unresolved']} == {'fridge_slider_mount','plinth_clip_mount'}
    assert any('AXIS PRO' in note and 'podczas montażu' in note for note in plan['manual_finishing'])
    save_plan(plan,tmp_path)
    assert 'dna trzech szuflad przykręcić podczas montażu' in (tmp_path/'raport.md').read_text()


def test_plan_source_does_not_expose_local_directories(tmp_path):
    plan = make_plan(ROOT / 'projects/drawer.yaml')
    assert plan['source'] == 'projects/drawer.yaml'
    project = tmp_path / 'private-directory' / 'drawer.yaml'
    project.parent.mkdir()
    project.write_bytes((ROOT / 'projects/drawer.yaml').read_bytes())
    plan = make_plan(project)
    assert plan['source'] == 'drawer.yaml'
    save_plan(plan, tmp_path / 'report')
    assert str(tmp_path) not in (tmp_path / 'report' / 'plan.json').read_text()
