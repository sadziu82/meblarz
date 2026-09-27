from parts.meble_pl_verify import compare_plan
from cutting import Shutdown, StopRequested, progress
import pytest


@pytest.fixture
def form():
    hole = dict(kind='face', powierzchnia='B', wsp_x=20, wsp_y=30, srednica=8, glebokosc=11)
    plan = {'groups': [dict(material={'meble_pl': {'decor': 'H1318', 'structure': 'ST10'}},
                           thickness=18, boards=[dict(name='front', width=400, height=200,
                                                     edges={}, drills=[hole], grain=2)])]}
    values = {'plyta_kod_produktu_1': 'code', 'nazwa_formatki_1_1': 'front',
              'szer_1_1': '400.0', 'wys_1_1': '200', 'ilosc_1_1': '1',
              'typ_frontu_1_1': 'nawierty_dowolne'}
    values.update({'wiercenia_w_plaszczyznie_1_1_1_'+k: str(v) for k, v in hole.items() if k != 'kind'})
    fields = [dict(id=k, value=v) for k, v in values.items()]
    fields += [dict(id='plyta_grubosc_1', text='18,0 mm'),
               dict(id='sloje_1_1_2', checked=True),
               dict(id='wiercenie_w_plaszczyznie_1_1', checked=True)]
    return plan, dict(fields=fields, titles={'1': 'EGGER H1318 ST10'})


def test_equal_and_numeric_formatting(form):
    assert compare_plan(*form) == []


@pytest.mark.parametrize('field,value,message', [
    ('szer_1_1', '401', 'szer'), ('ilosc_1_1', '2', 'ilosc'),
    ('wiercenia_w_plaszczyznie_1_1_1_wsp_x', '21', 'brak nawiertu'),
    ('wiercenia_w_plaszczyznie_1_1_1_powierzchnia', 'A', 'brak nawiertu'),
    ('wiercenia_w_plaszczyznie_1_1_1_glebokosc', 'przelot', 'brak nawiertu'),
])
def test_changes(form, field, value, message):
    plan, snapshot = form
    next(e for e in snapshot['fields'] if e['id'] == field)['value'] = value
    assert any(message in e for e in compare_plan(plan, snapshot))


def test_extra_and_missing_holes(form):
    plan, snapshot = form
    rows = [e for e in snapshot['fields'] if e['id'].startswith('wiercenia_w_')]
    snapshot['fields'] += [dict(e, id=e['id'].replace('_1_1_1_', '_1_1_2_')) for e in rows]
    assert any('nadmiarowy' in e for e in compare_plan(plan, snapshot))
    snapshot['fields'] = [e for e in snapshot['fields'] if not e['id'].startswith('wiercenia_w_')]
    assert any('brak nawiertu' in e for e in compare_plan(plan, snapshot))


def test_disabled_drilling_not_counted(form):
    plan, snapshot = form
    next(e for e in snapshot['fields'] if e['id'] == 'wiercenie_w_plaszczyznie_1_1')['checked'] = False
    assert any('brak nawiertu' in e for e in compare_plan(plan, snapshot))


def test_extra_board_and_unverified_groove(form):
    plan, snapshot = form
    snapshot['fields'] += [dict(id='nazwa_formatki_1_2', value='extra'), dict(id='wregowanie_1_1', checked=True)]
    errors = compare_plan(plan, snapshot)
    assert any('nadmiarowa formatka' in e for e in errors)
    assert any('wręgowanie' in e for e in errors)


def test_repeated_signal_deferred_and_restored():
    import signal
    previous = signal.getsignal(signal.SIGINT)
    with Shutdown().installed() as shutdown:
        signal.raise_signal(signal.SIGINT)
        signal.raise_signal(signal.SIGINT)
        with pytest.raises(StopRequested):
            shutdown.check()
    assert signal.getsignal(signal.SIGINT) == previous


def test_progress_each_hole(capsys):
    for i in range(4):
        progress('Nawierty w czole', i, 3)
    output = capsys.readouterr().out
    for i in range(4):
        assert f'{i}/3' in output


def test_material_and_edges(form):
    plan, snapshot = form
    snapshot['titles']['1'] = 'EGGER H1318 ST9'
    snapshot['fields'].append(dict(id='obrzeze_left_1_1', checked=True))
    errors = compare_plan(plan, snapshot)
    assert any('ST10' in e for e in errors)
    assert any('obrzeże left' in e for e in errors)


def test_unnamed_extra_board(form):
    plan, snapshot = form
    snapshot['fields'] += [dict(id='nazwa_formatki_1_2', value=''), dict(id='szer_1_2', value='200')]
    assert any('nadmiarowa formatka' in e for e in compare_plan(plan, snapshot))


def test_wrong_grain_is_reported(form):
    plan, snapshot = form
    next(e for e in snapshot['fields'] if e['id']=='sloje_1_1_2')['checked']=False
    snapshot['fields'].append(dict(id='sloje_1_1_1',checked=True))
    assert any('słoje' in error for error in compare_plan(plan,snapshot))


def test_material_alias_requires_exact_verified_sku():
    from parts.meble_pl_verify import material_errors
    spec = dict(decor='U0164',structure='ST9',manufacturer='Kronospan',
                product_codes={16:'P16ST41MEB11.U0164.ST9.KRO'})
    title = 'Płyta meblowa 0164 ST9 2800x2070 16 mm (u963)'
    assert material_errors(spec,16,title,'P16ST41MEB11.U0164.ST9.KRO') == []
    assert material_errors(spec,16,title,'P16ST41MEB11.U963.ST9')
    assert material_errors(spec,16,title,'')
    assert material_errors(spec,18,title,'P16ST41MEB11.U0164.ST9.KRO')


def test_saved_verification_accepts_alias_but_rejects_wrong_sku(form):
    plan,snapshot=form
    plan['groups'][0]['material']['meble_pl']['product_codes']={18:'confirmed-code'}
    snapshot['titles']['1']='Alias'
    field=next(e for e in snapshot['fields'] if e['id']=='plyta_kod_produktu_1')
    field['value']='confirmed-code'
    assert compare_plan(plan,snapshot)==[]
    field['value']='other-code'
    assert any('kod produktu' in e for e in compare_plan(plan,snapshot))


@pytest.mark.parametrize('flag,accepted', [('0',True), ('1',False), (None,False)])
def test_missing_grain_controls_only_allowed_for_explicitly_grainless_material(form,flag,accepted):
    plan,snapshot=form
    snapshot['fields']=[e for e in snapshot['fields'] if not e['id'].startswith('sloje_')]
    if flag is not None:
        snapshot['fields'].append(dict(id='plyta_sloje_1',value=flag))
    errors=compare_plan(plan,snapshot)
    assert (not errors) == accepted
