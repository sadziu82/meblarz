import csv
from pathlib import Path

from export_meblepl import MEBLEPL_HEADER, export


YAML_PATH = Path(__file__).parent / 'fixtures' / 'dresser.yaml'


def test_export_creates_meblepl_cut_list_and_drilling_sheet(tmp_path):
    csv_path, drilling_path, dxf_dir = export(YAML_PATH, tmp_path)

    with csv_path.open(newline='', encoding='utf-8') as source:
        rows = list(csv.reader(source, delimiter=';'))

    assert rows[0] == MEBLEPL_HEADER
    assert rows[1:]
    assert all(len(row) == len(MEBLEPL_HEADER) for row in rows)
    assert all('slide_' not in row[0] for row in rows[1:])
    assert any(row[0] == 'drawer_0_front' for row in rows[1:])

    drilling_sheet = drilling_path.read_text(encoding='utf-8')
    assert '## drawer_0_side_left' in drilling_sheet
    assert 'prowadnica' in drilling_sheet
    assert 'konfirmat' in drilling_sheet

    dxf_files = list(dxf_dir.glob('*.dxf'))
    assert dxf_files
    dxf = dxf_files[0].read_text(encoding='ascii')
    assert '\nLINE\n' in dxf
    assert '\nCIRCLE\n' in dxf
    assert 'OUTLINE' in dxf
