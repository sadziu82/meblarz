from pathlib import Path
import pytest
from cutting import main

PROJECT = Path(__file__).resolve().parents[1] / 'projects/drawer.yaml'
URL = 'https://www.meble.pl/rozkroj,r12345678'


@pytest.mark.parametrize('flags', [
    ['--verify', URL, '--recreate', URL],
    ['--recreate', 'https://example.org/rozkroj,r123'],
    ['--recreate', URL, '--no-calculate'],
])
def test_invalid_recreate_arguments(flags):
    with pytest.raises(SystemExit) as error:
        main(['--vendor', 'meble.pl', str(PROJECT), *flags])
    assert error.value.code == 2


def test_recreate_dry_run_is_local(tmp_path):
    assert main(['--vendor', 'meble.pl', str(PROJECT), '--recreate', URL, '--dry-run',
                 '--output-dir', str(tmp_path)]) == 0
    assert (tmp_path / 'plan.json').exists()
    assert not (tmp_path / 'browser-profile').exists()


def test_recreate_removes_obsolete_material_groups_and_backs_up(tmp_path):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    from cutting import Configurator
    with sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip("Chromium not installed")
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content('''
                <script>function usunPlyte(p) {
                    if(confirm('Usunąć?')) document.getElementById('div_plyta_'+p).remove();
                }</script>
                <div id="div_plyta_1"><input id="nazwa_formatki_1_1" value="original"></div>
                <div id="div_plyta_2"><button onclick="usunPlyte('2');">Usuń</button></div>
                <div id="div_plyta_3"><button onclick="usunPlyte('3');">Usuń</button></div>
            ''')
            configurator = Configurator(page, tmp_path)
            configurator.prepare_recreate({'groups': [{}]})
            assert page.locator('[id^="div_plyta_"]').count() == 1
            assert 'div_plyta_3' in (tmp_path/'przed-odtworzeniem.html').read_text()
            assert 'original' in (tmp_path/'przed-odtworzeniem-pola.json').read_text()
        finally:
            browser.close()
