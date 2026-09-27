import pytest
from export import main as export_main
from cutting import main as cutting_main


@pytest.mark.parametrize('main', [export_main, cutting_main])
@pytest.mark.parametrize('vendor', [[], ['--vendor', 'unknown']])
def test_vendor_required_and_validated_before_reading_project(main, vendor, capsys):
    with pytest.raises(SystemExit) as error:
        main(['missing-project.yaml', *vendor])
    assert error.value.code == 2
    assert '--vendor' in capsys.readouterr().err


def test_export_with_vendor(tmp_path):
    from pathlib import Path
    source=Path(__file__).resolve().parents[1]/'projects/drawer.yaml'
    export_main([str(source),'--vendor','meble.pl','--output-dir',str(tmp_path)])
    assert (tmp_path/'drawer-meblepl.csv').exists()


@pytest.mark.parametrize('flags', [
    ['--verify', 'https://example.org/rozkroj,r123'],
    ['--verify', 'https://www.meble.pl/rozkroj,r12345678', '--dry-run'],
])
def test_verify_arguments_rejected_before_loading_project(flags):
    with pytest.raises(SystemExit) as error:
        cutting_main(['missing.yaml', '--vendor', 'meble.pl', *flags])
    assert error.value.code == 2
