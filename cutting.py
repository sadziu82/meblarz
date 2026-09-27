#!/usr/bin/env python3
"""Populate a reviewable Meble.pl draft in a visible browser; never place an order."""
import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import re
import signal
from contextlib import contextmanager
import sys
import time

from export import MEBLEPL_HEADER, _number
from parts.meble_pl_plan import make_plan, save_plan
from parts.meble_pl_verify import compare_plan, material_errors

URL = 'https://www.meble.pl/rozkroj,plyty-meblowe'


class ConfiguratorError(RuntimeError):
    pass


class StopRequested(Exception):
    pass


class Shutdown:
    """Never raise inside Playwright's greenlet; stop at safe checkpoints."""
    def __init__(self):
        self.requested = False

    def signal(self, *_):
        if not self.requested:
            print('\nKończenie bieżącej operacji i zamykanie przeglądarki…', flush=True)
        self.requested = True

    def check(self):
        if self.requested:
            raise StopRequested()

    @contextmanager
    def installed(self):
        previous = signal.signal(signal.SIGINT, self.signal)
        try:
            yield self
        finally:
            signal.signal(signal.SIGINT, previous)


def progress(label, done, total):
    filled = 24 * done // total
    bar = '#' * filled + '-' * (24-filled)
    end = '\n' if done == total or not sys.stdout.isatty() else '\r'
    print(f'    {label}: [{bar}] {done}/{total}', end=end, flush=True)


class Configurator:
    def __init__(self, page, output, shutdown=None):
        self.shutdown = shutdown or Shutdown()
        self.page, self.output = page, Path(output)
        self.expected = {}
        cookie = page.locator('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowallSelection')
        page.add_locator_handler(cookie, lambda: cookie.click())
        quote_dialog = page.locator('.ui-dialog').filter(has=page.locator('#warstwa_wybor_typu'))
        page.add_locator_handler(quote_dialog, lambda: quote_dialog.locator('.ui-dialog-titlebar-close').click())
        self.pending = set()
        page.on('request', lambda r: self.pending.add(r) if '/go/ajaxRequest' in r.url else None)
        page.on('requestfinished', lambda r: self.pending.discard(r))
        page.on('requestfailed', lambda r: self.pending.discard(r))
        page.set_default_timeout(20000)

    def settle(self):
        self.shutdown.check()
        # The site debounces coordinate edits for 900 ms, then replaces the row.
        self.page.wait_for_timeout(1100)
        deadline=time.monotonic()+30
        while self.pending or self.page.locator('.blockUI.blockOverlay:visible').count():
            if time.monotonic()>deadline: raise ConfiguratorError('Przekroczono czas odpowiedzi konfiguratora')
            self.page.wait_for_timeout(100)
        self.shutdown.check()
        error = self.page.locator('#form-error:visible')
        if error.count():
            raise ConfiguratorError(error.inner_text())

    def set_values(self, fields, trigger):
        """Fill one complete UI row before firing its normal change/validation event."""
        self.shutdown.check()
        self.page.evaluate('''({fields,trigger}) => {
            for (const [id,value] of Object.entries(fields)) {
                const e=document.getElementById(id);
                if (!e || !['INPUT','SELECT'].includes(e.tagName)) throw Error('Missing field '+id);
                if (e.tagName==='SELECT' && !Array.from(e.options).some(o=>o.value===value))
                    throw Error('Unsupported option '+id+'='+value);
                e.value=value;
            }
            document.getElementById(trigger).dispatchEvent(new Event('change',{bubbles:true}));
        }''', dict(fields=fields,trigger=trigger))
        self.settle()
        for key,value in fields.items():
            actual = self.page.locator('#'+key).input_value()
            if actual != value:
                raise ConfiguratorError(f'Formularz zmienił {key}: {value!r} → {actual!r}')
        self.expected.update({k:dict(value=v) for k,v in fields.items()})

    def remember(self, element_id, value=None, checked=None):
        self.expected[element_id] = dict(value=value) if checked is None else dict(checked=checked)

    def select_material(self, p, group):
        if p > 1 and not self.page.locator(f'#div_plyta_{p}').count():
            self.page.get_by_role('button',name='Dodaj płytę',exact=True).click()
        elif not self.page.locator('.probka-kont:visible').count():
            self.page.locator(f'#div_plyta_{p}').get_by_role('button',name='zmień płytę',exact=True).click()
        spec = group['material']['meble_pl']
        tiles = self.page.locator('.probka-kont:visible').filter(
            has_text=str(spec['decor'])).filter(has_text=str(spec['structure']))
        tiles.first.wait_for()
        # The catalogue also contains hidden duplicate tiles, excluded above.
        if tiles.count()!=1:
            raise ConfiguratorError(f'Niejednoznaczny wybór płyty: {spec}; znaleziono {tiles.count()}')
        tiles.click();self.settle()
        color_dialog = self.page.locator('.ui-dialog[aria-describedby="dialog-zmiana-plyty"]:visible')
        if color_dialog.count():
            color_dialog.get_by_role('button',name='TAK',exact=True).click()
            self.settle()
            info = self.page.locator('#dialog-info-ok:visible')
            if info.count():
                info.click();self.settle()
        thickness = self.page.locator(f'#plyta_grubosc_{p}')
        choices = thickness.locator('option').evaluate_all('(es)=>es.map(e=>({value:e.value,text:e.textContent}))')
        match = [o for o in choices if float(o['text'].strip().split()[0].replace(',','.'))==group['thickness']]
        if len(match)!=1:
            raise ConfiguratorError(f"{spec['decor']} {spec['structure']}: brak grubości {group['thickness']:g} mm. Dostępne: {[o['text'].strip() for o in choices]}")
        if thickness.input_value()!=match[0]['value']:
            thickness.select_option(match[0]['value']);self.settle()
        self.remember(f'plyta_grubosc_{p}',value=match[0]['value'])
        title = self.page.locator(f'#plyta_nazwa_{p}').inner_text()
        code = self.page.locator(f'#plyta_kod_produktu_{p}').input_value()
        errors = material_errors(spec,group['thickness'],title,code)
        if errors:
            raise ConfiguratorError('Wybrano inną płytę: '+'; '.join(errors))
        self.remember(f'plyta_kod_produktu_{p}',value=code)
        print(f'Płyta {p}: {title}, {group["thickness"]:g} mm',flush=True)

    def expand_all(self):
        expand=self.page.get_by_text('Rozwiń wszystkie formatki',exact=False)
        while expand.count() and expand.first.is_visible():
            expand.first.click();self.settle()

    def import_rectangles(self,p,group):
        path=self.output/f'plyta-{p}.csv'
        with path.open('w',newline='') as f:
            writer=csv.writer(f,delimiter=';')
            writer.writerow(MEBLEPL_HEADER)
            for b in group['boards']:
                writer.writerow([b['name'],_number(b['width']),'',_number(b['height']),'',
                                 _number(b['thickness']),'1',str(b['grain'])])
        self.page.locator(f'#rodzaj_importu_formatek_{p}_1').check()
        self.page.locator(f'#fileupload_{p}').set_input_files(str(path.resolve()))
        self.page.wait_for_function('''({p,count}) => {
            const input=document.getElementById('nazwa_formatki_'+p+'_'+count);
            return input && input.value!=='';
        }''',arg=dict(p=p,count=len(group['boards'])))
        self.settle()
        self.expand_all()
        grain_flag=self.page.locator(f'#plyta_sloje_{p}')
        no_grain=bool(grain_flag.count() and grain_flag.input_value()=='0')
        if no_grain:
            self.remember(f'plyta_sloje_{p}',value='0')
            print(f'  Płyta {p}: materiał bez kierunku słojów — wybór kierunku nie dotyczy.',flush=True)
        for i,b in enumerate(group['boards'],1):
            for key,value in [('szer',_number(b['width'])),('wys',_number(b['height'])),
                              ('ilosc','1'),('nazwa_formatki',b['name'])]:
                field=f'{key}_{p}_{i}'
                if self.page.locator('#'+field).input_value()!=value:
                    raise ConfiguratorError(f'Błąd importu formatki {b["name"]}: {field}')
                self.remember(field,value=value)
            if no_grain:
                continue
            grain_field=f'sloje_{p}_{i}_{b['grain']}'
            grain=self.page.locator('#'+grain_field)
            if not grain.count():
                raise ConfiguratorError(f'{b["name"]}: brak wyboru słojów i brak oznaczenia materiału bezkierunkowego')
            if not grain.is_checked():
                grain.check();self.settle()
            self.remember(grain_field,checked=True)

    def edging(self,p,i,b):
        for edge in ('top','right','bottom','left'):
            key=f'obrzeze_{edge}_{p}_{i}'
            selected=edge in b['edges']
            checkbox=self.page.locator('#'+key)
            if not checkbox.count():
                if selected: raise ConfiguratorError(f'{b["name"]}: materiał nie oferuje obrzeży')
                continue
            if checkbox.is_checked()!=selected:
                checkbox.set_checked(selected);self.settle()
            self.remember(key,checked=selected)
        if b['edges']:
            band=next(iter(b['edges'].values()))
            radios=self.page.locator(f'input[name="obrzeze_gr[{p}][{i}][all]"]')
            choices=radios.evaluate_all('(es)=>es.map(e=>({id:e.id,value:e.value}))')
            chosen=[r for r in choices if float(r['value'].split('_')[0])==band]
            if len(chosen)!=1: raise ConfiguratorError(f'{b["name"]}: niedostępne obrzeże {band} mm')
            radio=self.page.locator('#'+chosen[0]['id'])
            if not radio.is_checked(): radio.check();self.settle()
            self.remember(chosen[0]['id'],checked=True)

    def drilling(self,p,i,b):
        if not b['drills']:return
        self.page.locator(f'#div_nawierty_dowolne_{p}_{i}').click();self.settle()
        for kind,suffix in [('face','plaszczyznie'),('edge','czole')]:
            holes=[d for d in b['drills'] if d['kind']==kind]
            if not holes:continue
            self.page.locator(f'#wiercenie_w_{suffix}_{p}_{i}').check();self.settle()
            self.remember(f'wiercenie_w_{suffix}_{p}_{i}',checked=True)
            label = 'Nawierty na płaszczyźnie' if kind == 'face' else 'Nawierty w czole'
            progress(label, 0, len(holes))
            for n,hole in enumerate(holes,1):
                self.shutdown.check()
                prefix=f'wiercenia_w_{suffix}_{p}_{i}_{n}_'
                if n>1:
                    self.page.locator(f'''div[onclick="dodajNawiert('{p}','{i}','wiercenia_w_{suffix}');"]''').click()
                    self.settle()
                fields={prefix+k:(_number(v) if isinstance(v,(int,float)) else v)
                        for k,v in hole.items() if k!='kind'}
                self.set_values(fields,prefix+'glebokosc')
                progress(label, n, len(holes))

    def verify(self):
        errors=self.page.evaluate('''expected=>Object.entries(expected).flatMap(([id,want])=>{
            const e=document.getElementById(id);
            if(!e)return [id+': brak pola'];
            return Object.entries(want).filter(([key,value])=>e[key]!==value)
                .map(([key,value])=>id+': '+e[key]+' != '+value);
        })''',self.expected)
        if errors:raise ConfiguratorError('Weryfikacja zapisu nie powiodła się:\n'+'\n'.join(errors[:20]))
        (self.output/'verified-fields.json').write_text(json.dumps(self.expected,ensure_ascii=False,indent=2))

    def verify_saved(self, plan, url):
        self.page.goto(url, wait_until='domcontentloaded')
        self.page.locator('[id^="plyta_kod_produktu_"]').first.wait_for(state='attached')
        self.expand_all()
        self.shutdown.check()
        snapshot = self.page.evaluate("""() => ({
            fields: Array.from(document.querySelectorAll('input,select')).map(e => ({
                id:e.id, name:e.name, value:e.value, checked:e.checked,
                text:e.tagName==='SELECT' ? e.selectedOptions[0]?.text : null})),
            titles: Object.fromEntries(Array.from(document.querySelectorAll('[id^="plyta_nazwa_"]'))
                .map(e=>[e.id.split('_').pop(),e.textContent]))
        })""")
        errors = compare_plan(plan, snapshot)
        (self.output/'odczyt.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
        messages = ['Rozkrój różni się od planu.' if errors else 'Rozkrój zgodny z planem.',
                    'Sprawdzono materiały, formatki, ilości, słoje, obrzeża i dostępne nawierty.']
        messages.extend(plan.get('manual_finishing', []))
        if plan['manual']:
            messages.append(f'Pozostałe operacje do wykonania osobno: {len(plan["manual"])}. Szczegóły w raport.md.')
        if plan['unresolved']:
            messages.append(f'Brakujące dane obróbki: {len(plan["unresolved"])}. Szczegóły w raport.md.')
        scope = '\n'.join(messages)
        report = self.output/'weryfikacja.md'
        report.write_text(f'# Weryfikacja rozkroju\n\n{url}\n\n{scope}\n\n' +
                          '\n'.join('- '+e for e in errors))
        print(f'Weryfikacja: {len(errors)} różnic. Raport: {report}', flush=True)
        if errors:
            raise ConfiguratorError('Rozkrój różni się od YAML-a:\n'+'\n'.join(errors[:20]))
        print(scope, flush=True)

    def prepare_recreate(self, plan):
        self.expand_all()
        # Keep the original form locally before replacing any rows/materials.
        (self.output/'przed-odtworzeniem.html').write_text(self.page.content())
        (self.output/'przed-odtworzeniem-url.txt').write_text(self.page.url)
        self.page.screenshot(path=str(self.output/'przed-odtworzeniem.png'))
        fields = self.page.locator('input,select').evaluate_all(
            '(es)=>es.map(e=>({id:e.id,name:e.name,value:e.value,checked:e.checked}))')
        (self.output/'przed-odtworzeniem-pola.json').write_text(json.dumps(fields,ensure_ascii=False,indent=2))
        ids = self.page.locator('[id^="div_plyta_"]').evaluate_all(
            '(es)=>es.map(e=>Number(e.id.split("_").pop())).filter(Number.isFinite)')
        # Imports replace all boards in retained groups; remove obsolete groups too.
        for p in sorted(ids,reverse=True):
            if p <= len(plan['groups']):
                continue
            self.shutdown.check()
            self.page.once('dialog', lambda dialog: dialog.accept())
            self.page.locator(f'[onclick="usunPlyte(\'{p}\');"]').click()
            self.settle()
        self.expected.clear()
        print('Odtwarzanie rozkroju: zastępuję wszystkie formatki danymi z YAML-a.',flush=True)

    def run(self,plan,calculate=True,recreate_url=None):
        self.page.goto(recreate_url or URL,wait_until='domcontentloaded')
        cookie=self.page.get_by_role('button',name='Allow selection',exact=True)
        try:
            cookie.wait_for(timeout=5000);cookie.click()
        except Exception:
            pass
        if recreate_url:
            self.page.locator('[id^="plyta_kod_produktu_"]').first.wait_for(state='attached')
            self.prepare_recreate(plan)
        for p,group in enumerate(plan['groups'],1):
            self.select_material(p,group)
            self.import_rectangles(p,group)
            for i,b in enumerate(group['boards'],1):
                print(f'  {i}/{len(group["boards"])} {b["name"]}: {len(b["drills"])} nawiertów',flush=True)
                self.edging(p,i,b)
                self.drilling(p,i,b)
            self.verify()
        if calculate:
            self.page.get_by_text('Przelicz koszty',exact=False).click()
            print('Przeliczanie kosztów szkicu…',flush=True)
            self.page.get_by_text('Podsumowanie kosztów zlecenia:',exact=False).wait_for(timeout=180000)
            self.expand_all()
            self.verify()
            collapse=self.page.get_by_text('Zwiń wszystkie formatki',exact=False)
            if collapse.count() and collapse.first.is_visible():collapse.first.click()
            self.page.get_by_text('Podsumowanie kosztów zlecenia:',exact=False).scroll_into_view_if_needed()
        if recreate_url:
            result_url = self.page.url
            self.verify_saved(plan,result_url)
            source_id = re.search(r'/rozkroj,r(\d+)',recreate_url).group(1)
            result_match = re.search(r'/rozkroj,r(\d+)',result_url)
            same_id = bool(result_match and result_match.group(1)==source_id)
            result = dict(source_url=recreate_url,result_url=result_url,same_id=same_id)
            (self.output/'odtworzenie.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
            if not same_id:
                print(f'Meble.pl nadało nowy numer rozkroju. Adres źródłowy: {recreate_url}\n'
                      f'Odtworzony rozkrój: {result_url}. Nie nadpisano starego adresu.',flush=True)
        (self.output/'wynik.txt').write_text(self.page.url+'\n\n'+self.page.locator('body').inner_text())
        self.page.screenshot(path=str(self.output/'podglad.png'))
        print(f'Gotowe: {self.page.url}\nRaport: {self.output / "raport.md"}',flush=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vendor', required=True, choices=['meble.pl'],
                        help='dostawca rozkroju (wymagany)')
    parser.add_argument('project',type=Path)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--recreate', metavar='URL', help='Zastąp wszystkie formatki istniejącego rozkroju danymi z YAML-a')
    mode.add_argument('--verify', metavar='URL', help='Porównaj istniejący rozkrój z YAML-em bez zmieniania formularza')
    parser.add_argument('--dry-run',action='store_true',help='Tylko walidacja i lokalny raport, bez przeglądarki')
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--no-calculate',action='store_true',help='Wypełnij formularz bez wyliczania wyceny')
    parser.add_argument('--close',action='store_true',help='Zamknij przeglądarkę po zakończeniu (np. do testów)')
    parser.add_argument('--headless',action='store_true',help='Bez GUI; implikuje --close')
    args=parser.parse_args(argv)
    for name in ('verify','recreate'):
        url=getattr(args,name)
        if url and not re.fullmatch(r'https://(?:www\.)?meble\.pl/rozkroj,r\d+(?:,\d+)?/?', url):
            parser.error(f'--{name} wymaga adresu https://www.meble.pl/rozkroj,rNUMER')
    if args.verify and args.dry_run:
        parser.error('--verify nie można łączyć z --dry-run')
    if args.recreate and args.no_calculate:
        parser.error('--recreate wymaga przeliczenia, aby zapisać odtworzony rozkrój')
    try:
        plan=make_plan(args.project)
        output=save_plan(plan,args.output_dir or Path('exports')/(args.project.stem+'-meblepl-'+datetime.now().strftime('%Y%m%d-%H%M%S')))
    except (ValueError,OSError,KeyError) as exc:
        print(f'Błąd projektu: {exc}',file=sys.stderr);return 2
    print(f'SZKIC: {sum(len(g["boards"]) for g in plan["groups"])} formatek; '
          f'{len(plan["manual"])} operacji osobno; {len(plan["unresolved"])} braków danych.\n'
          f'Raport: {output / "raport.md"}. Eksport produkcyjny zachowuje dotychczasową walidację.',flush=True)
    if args.dry_run:return 0
    if not args.headless and not os.environ.get('DISPLAY'):
        print('Brak DISPLAY. Przykład: DISPLAY=:98 python cutting.py --vendor meble.pl projekt.yaml',file=sys.stderr);return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('Zainstaluj: python -m pip install -r requirements.txt; python -m playwright install chromium',file=sys.stderr);return 2
    exit_code=0
    with Shutdown().installed() as shutdown, sync_playwright() as p:
        context=None
        try:
            context=p.chromium.launch_persistent_context(str((output/'browser-profile').resolve()),
                headless=args.headless, no_viewport=True, accept_downloads=True,
                args=['--start-fullscreen'], handle_sigint=False)
            page=context.pages[0] if context.pages else context.new_page()
            configurator = Configurator(page,output,shutdown)
            shutdown.check()
            if args.verify:
                configurator.verify_saved(plan,args.verify)
            else:
                configurator.run(plan,not args.no_calculate,args.recreate)
        except StopRequested:
            exit_code=130
        except Exception as exc:
            exit_code=1
            print(f'Przerwano: {exc}\nNie złożono zamówienia.',file=sys.stderr,flush=True)
            (output/'blad.txt').write_text(str(exc))
            if context and context.pages:
                page=context.pages[0]
                try:
                    page.screenshot(path=str(output/'blad.png'))
                    (output/'blad.html').write_text(page.content())
                except Exception:pass
        finally:
            if context:
                if not (args.close or args.headless or shutdown.requested):
                    print('Przeglądarka pozostaje otwarta do sprawdzenia. Ctrl+C kończy skrypt.',flush=True)
                    try:
                        while context.pages and not shutdown.requested:
                            context.pages[0].wait_for_timeout(1000)
                    except Exception:pass
                try: context.close()
                except Exception: pass
    return exit_code


if __name__=='__main__':
    raise SystemExit(main())
