from copy import deepcopy
from pathlib import Path
import pytest
from parts.drawer import Board
from parts.meble_pl_grooves import board_grooves, convert_rectangle
from parts.meble_pl_plan import make_plan
from parts.meble_pl_verify import compare_plan
from export import _load_model
from parts.kitchen_ventilation import routable_guide_rectangles

ROOT = Path(__file__).resolve().parents[1]


def horizontal():
    return Board('shelf', 600, 18, 400, (0, 0, 0), movable=False)


@pytest.mark.parametrize('low,high,edge,offset,x1,x2', [
    ([0, 10, 0], [600, 13.2, 3], 'bottom', 10, 0, 0),
    ([15, 386.8, 0], [575, 390, 3], 'top', 10, 15, 25),
    ([10, 20, 0], [13.2, 370, 3], 'left', 10, 30, 20),
    ([586.8, 0, 0], [590, 350, 3], 'right', 10, 50, 0),
])
def test_edges_end_margins_and_face(low, high, edge, offset, x1, x2):
    g = convert_rectangle(horizontal(), low, high)
    assert g['powierzchnia'] == 'B'
    assert g['wregowanie_bok'] == edge
    assert g['wregowanie_odleglosc'] == offset
    assert (g['wregowanie_x1'], g['wregowanie_x2']) == (x1, x2)
    assert g['wregowanie_przelot_x1'] == (x1 == 0)
    assert g['wregowanie_przelot_x2'] == (x2 == 0)
    assert g['wregowanie_rodzaj'] == ('nprzelot' if x1 or x2 else 'przelot')


def test_back_rebates_are_machined_from_broad_face_with_swapped_width_depth():
    side = Board('side', 18, 800, 310, (0, 0, 0))
    side.grooves = [dict(kind='back_rabbet', face='+y', width=12, depth=3.2,
                         x=6, z=100, span_x=12, span_z=700)]
    grooves, manual = board_grooves(side)
    assert not manual
    assert len(grooves) == 1
    g = grooves[0]
    assert (g['powierzchnia'], g['wregowanie_bok']) == ('A', 'right')
    assert (g['wregowanie_szerokosc'], g['wregowanie_glebokosc']) == (3.2, 12)
    assert (g['wregowanie_x1'], g['wregowanie_x2']) == (0, 100)
    side.grooves[0].update(x=0, span_x=6, width=6)
    assert board_grooves(side)[0][0]['powierzchnia'] == 'B'


@pytest.mark.parametrize('low,high,reason', [
    ([0, 10, 0], [600, 20, 4], 'Szerokość 10'),
    ([0, 10.4, 0], [600, 13.6, 3], 'Odległość'),
    ([0, 51, 0], [600, 54.2, 3], 'Odległość'),
    ([0, 10, 0], [600, 13.2, 3.2], 'Głębokość'),
    ([0, 10, 0], [601, 13.2, 3], 'poza formatkę'),
    ([0, 10, 0], [80, 13.2, 3], 'Za krótki'),
    ([0, 10, 0], [600, 13.2, 18], 'Głębokość'),
])
def test_unsupported_geometry_is_never_silently_changed(low, high, reason):
    with pytest.raises(ValueError, match=reason):
        convert_rectangle(horizontal(), low, high)


def test_duplicate_face_edge_goes_to_manual_instead_of_losing_a_segment():
    b = horizontal()
    b.grooves = [dict(kind='led', face='-z', width=3.2, depth=3, offset=11.6,
                      x=x, span_x=150) for x in (0, 300)]
    automatic, manual = board_grooves(b)
    assert not automatic
    assert len(manual) == 2
    assert all('tej samej powierzchni' in e['reason'] for e in manual)


def test_kitchen_ventilation_snapping_is_shared_by_preview_export_and_plan():
    project = ROOT / 'projects/kitchen_tall_unit.yaml'
    model = _load_model(project)
    plan = make_plan(project)
    planned = {b['name']: b for g in plan['groups'] for b in g['boards']}
    assert sum(len(b['grooves']) for b in planned.values()) == 3
    plinth_manual = [op for op in plan['manual'] if op['board'] == 'kitchen_plinth_front' and op['operation'] == 'ventilation_cut_guide']
    assert len(plinth_manual) == 2
    assert all('75 mm' in op['reason'] for op in plinth_manual)
    for b in model.boards:
        for groove in b.grooves:
            if groove['kind'] != 'ventilation_cut_guide':
                continue
            rects = routable_guide_rectangles(b, groove)
            height = b.height if groove['face'] == '-y' else b.depth
            offsets = [round(min(y1, height-y2), 5) for _, y1, _, y2 in rects]
            if b.name != 'kitchen_plinth_front':
                assert offsets == [g['wregowanie_odleglosc'] for g in planned[b.name]['grooves']]
            assert all(v == int(v) for v in offsets)
            original = deepcopy(groove)
            original['integer_edge_offsets'] = False
            before = routable_guide_rectangles(b, original)
            for old, new in zip(before, rects):
                assert old[0] == new[0] and old[2] == new[2]
                assert new[3]-new[1] == pytest.approx(3.2)
                assert abs(new[1]-old[1]) <= .5


def form():
    groove = convert_rectangle(horizontal(), [15, 10, 0], [575, 13.2, 3])
    board = dict(name='shelf', width=600, height=400, grain=2, edges={}, drills=[], grooves=[groove])
    plan = dict(groups=[dict(material=dict(meble_pl=dict(decor='X', structure='Y')),
                            thickness=18, boards=[board])])
    fields = [dict(id='plyta_kod_produktu_1', value='code'),
              dict(id='plyta_grubosc_1', text='18 mm'),
              dict(id='nazwa_formatki_1_1', value='shelf'),
              dict(id='szer_1_1', value='600'), dict(id='wys_1_1', value='400'),
              dict(id='ilosc_1_1', value='1'), dict(id='sloje_1_1_2', checked=True),
              dict(id='typ_frontu_1_1', value='nawierty_dowolne'),
              dict(id='wregowanie_1_1', checked=True)]
    for key, val in groove.items():
        prefix = 'wregowania_1_1_1_' + key
        if key == 'wregowanie_rodzaj':
            fields.append(dict(id=prefix+'_'+val, checked=True))
        elif isinstance(val, bool):
            fields.append(dict(id=prefix, checked=val))
        else:
            fields.append(dict(id=prefix, value=str(val)))
    return plan, dict(fields=fields, titles={'1': 'X Y'})


def test_verify_grooves_exact_match():
    assert compare_plan(*form()) == []


@pytest.mark.parametrize('field,new', [('powierzchnia','A'),('wregowanie_bok','top'),
    ('wregowanie_szerokosc','4.2'),('wregowanie_glebokosc','4'),
    ('wregowanie_odleglosc','11'),('wregowanie_x1','25'),('wregowanie_x2','15')])
def test_verify_detects_changed_groove(field, new):
    plan, snapshot = form()
    next(e for e in snapshot['fields'] if e['id'] == 'wregowania_1_1_1_'+field)['value'] = new
    assert any('brak wręgu' in e for e in compare_plan(plan, snapshot))


def test_verify_detects_disabled_extra_and_changed_end_switches():
    plan, snapshot = form()
    next(e for e in snapshot['fields'] if e['id'] == 'wregowanie_1_1')['checked'] = False
    assert any('brak wręgu' in e for e in compare_plan(plan, snapshot))
    plan, snapshot = form()
    snapshot['fields'] += [dict(e, id=e['id'].replace('_1_1_1_', '_1_1_2_'))
                           for e in list(snapshot['fields']) if e['id'].startswith('wregowania_')]
    assert any('nadmiarowy/inny wręg' in e for e in compare_plan(plan, snapshot))
    plan, snapshot = form()
    next(e for e in snapshot['fields'] if e['id'].endswith('wregowanie_przelot_x1'))['checked'] = True
    assert any('brak wręgu' in e for e in compare_plan(plan, snapshot))


def test_browser_fills_multiple_grooves_and_verifies_round_trip(tmp_path):
    from cutting import Configurator, Shutdown
    sync = pytest.importorskip('playwright.sync_api').sync_playwright
    with sync() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip('Chromium not installed')
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content('''
              <input id="typ_frontu_1_1" value="nawierty_dowolne">
              <input type="checkbox" id="wregowanie_1_1">
              <div id="rows"></div>
              <div onclick="dodajNawiert('1','1','wregowania');">Add</div>
              <script>
              let count=0;
              function dodajNawiert() {
                const prefix='wregowania_1_1_'+(++count)+'_';
                let html='';
                for(const [key,values] of Object.entries({powierzchnia:['A','B'],
                  wregowanie_bok:['top','right','bottom','left'],
                  wregowanie_glebokosc:['2','3','4'],
                  wregowanie_szerokosc:['3.2','4.2','10.2'],
                  wregowanie_odleglosc:['0','10']})) {
                  html+='<select id="'+prefix+key+'">'+values.map(v=>'<option>'+v+'</option>').join('')+'</select>';
                }
                for(const end of ['x1','x2']) {
                  html+='<input id="'+prefix+'wregowanie_'+end+'" value="0">';
                  html+='<input type="checkbox" id="'+prefix+'wregowanie_przelot_'+end+'">';
                }
                for(const kind of ['przelot','nprzelot'])
                  html+='<input type="radio" name="mode'+count+'" id="'+prefix+'wregowanie_rodzaj_'+kind+'">';
                document.getElementById('rows').insertAdjacentHTML('beforeend',html);
              }
              dodajNawiert();
              </script>''')
            c = Configurator.__new__(Configurator)
            c.page, c.output, c.expected, c.shutdown = page, tmp_path, {}, Shutdown()
            c.settle = c.shutdown.check  # Local fixture has no network/debounce.
            a = convert_rectangle(horizontal(), [15, 10, 0], [575, 13.2, 3])
            b = convert_rectangle(horizontal(), [10, 0, 0], [13.2, 350, 3])
            c.grooving(1, 1, dict(grooves=[a, b]))
            c.verify()
            assert page.locator('#wregowania_1_1_1_wregowanie_x1').input_value() == '15'
            assert page.locator('#wregowania_1_1_2_wregowanie_x1').input_value() == '50'
            assert page.locator('#wregowania_1_1_2_wregowanie_przelot_x2').is_checked()
            assert page.locator('#wregowania_1_1_1_wregowanie_rodzaj_nprzelot').is_checked()
            assert (tmp_path / 'verified-fields.json').exists()
        finally:
            browser.close()


@pytest.mark.parametrize('height,offset,accepted', [(100,21,True),(100,22,False),(120,41,True),(120,42,False)])
def test_opposite_edge_clearance_observed_in_live_form(height, offset, accepted):
    b = Board('narrow', 600, 18, height, (0,0,0))
    if accepted:
        assert convert_rectangle(b, [0,offset,0], [600,offset+3.2,3])['wregowanie_odleglosc'] == offset
    else:
        with pytest.raises(ValueError, match='75 mm'):
            convert_rectangle(b, [0,offset,0], [600,offset+3.2,3])
