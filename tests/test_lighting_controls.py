from pathlib import Path
import yaml
from parts.desk_drawer_wall import load_desk_drawer_wall
from export_meblepl import export

PROJECT = Path(__file__).parents[1] / 'projects/desk_drawer_wall.yaml'


def test_control_locations_are_fixed_and_not_fabrication(tmp_path):
    model = load_desk_drawer_wall(str(PROJECT))
    switches = [b for b in model.boards if b.name.endswith('_switch_location')]
    sensors = [b for b in model.boards if b.name.startswith('led_sensor_location_')]
    assert len(switches) == 5 and len(sensors) == 11
    for marker in switches + sensors:
        assert not marker.fabrication and not marker.movable
        assert not marker.holes and not marker.joint_holes
    csv, md, dxf = export(PROJECT, tmp_path/'export')
    assert '_switch_location' not in csv.read_text()
    assert 'led_sensor_location' not in csv.read_text()
    assert not any('location' in p.name for p in dxf.iterdir())
    assert 'zamknięta = LED wyłączony' in md.read_text()
    config = yaml.safe_load(PROJECT.read_text())
    config['desk_drawer_wall']['lighting_controls']['preview'] = False
    path = tmp_path/'without.yaml'
    path.write_text(yaml.safe_dump(config))
    without = load_desk_drawer_wall(str(path))
    assert [b for b in model.boards if b.fabrication] == [b for b in without.boards if b.fabrication]
    assert len(model.boards) - len(without.boards) == 16
