"""Read-only comparison of an expanded Meble.pl form with a generated draft."""
from collections import Counter
import json
import re


def normalized(value):
    try:
        return float(str(value).replace(',', '.'))
    except (ValueError, TypeError):
        return value


def material_errors(spec, thickness, title, product_code):
    """Prefer a verified exact SKU; catalogue and form names can differ."""
    codes = spec.get('product_codes', {})
    expected_code = codes.get(thickness, codes.get(str(thickness), codes.get(f'{thickness:g}')))
    if expected_code:
        return ([] if product_code == expected_code else
                [f'kod produktu {product_code!r}, oczekiwano {expected_code!r}'])
    errors = []
    for key in ('decor', 'structure', 'manufacturer'):
        token = spec.get(key)
        if token and not re.search(r'(?<![A-Za-z0-9])'+re.escape(str(token))+r'(?![A-Za-z0-9])', title, re.I):
            errors.append(f'brak {token!r} w nazwie {title!r}')
    return errors


def compare_plan(plan, snapshot):
    fields = {e['id']: e for e in snapshot['fields'] if e['id']}
    errors = []

    def value(key):
        return fields.get(key, {}).get('value')

    def checked(key):
        return fields.get(key, {}).get('checked', False)

    def check(label, actual, expected):
        if normalized(actual) != normalized(expected):
            errors.append(f'{label}: jest {actual!r}, oczekiwano {expected!r}')

    groups = sorted(k for k in fields if re.fullmatch(r'plyta_kod_produktu_\d+', k))
    check('Liczba płyt', len(groups), len(plan['groups']))
    for p, group in enumerate(plan['groups'], 1):
        title = snapshot['titles'].get(str(p), '')
        errors.extend(f'Płyta {p}: {error}' for error in material_errors(
            group['material']['meble_pl'], group['thickness'], title, value(f'plyta_kod_produktu_{p}')))
        thickness = fields.get(f'plyta_grubosc_{p}', {}).get('text') or ''
        check(f'Płyta {p}: grubość', thickness.strip().split(' ')[0], group['thickness'])
        actual_boards = {}
        for key in fields:
            match = re.fullmatch(rf'nazwa_formatki_{p}_(\d+)', key)
            if match:
                i = match[1]
                if value(key) or normalized(value(f'szer_{p}_{i}')) not in (None, '', 0):
                    actual_boards.setdefault(value(key), []).append(i)
        expected_names = Counter(b['name'] for b in group['boards'])
        actual_names = Counter({k: len(v) for k, v in actual_boards.items()})
        for name, count in (actual_names - expected_names).items():
            errors.append(f'Płyta {p}: nadmiarowa formatka {name!r} ({count})')
        for b in group['boards']:
            name = b['name']
            candidates = actual_boards.get(name, [])
            if not candidates:
                errors.append(f'Płyta {p}: brak formatki {name!r}')
                continue
            i = candidates.pop(0)
            suffix = f'{p}_{i}'
            for key, expected in [('szer', b['width']), ('wys', b['height']), ('ilosc', 1)]:
                check(f'{name}: {key}', value(f'{key}_{suffix}'), expected)
            if value(f'plyta_sloje_{p}') != '0':
                check(f'{name}: słoje (na '+('wysokość' if b['grain']==1 else 'szerokość')+')',
                      checked(f'sloje_{suffix}_{b["grain"]}'), True)
            for edge in ('top', 'right', 'bottom', 'left'):
                check(f'{name}: obrzeże {edge}', checked(f'obrzeze_{edge}_{suffix}'), edge in b['edges'])
            if b['edges']:
                if checked(f'rozne_obrzeza_{suffix}'):
                    errors.append(f'{name}: osobne ustawienia obrzeży wymagają ręcznej weryfikacji')
                selected = [e['value'].split('_')[0] for e in fields.values()
                            if e.get('name') == f'obrzeze_gr[{p}][{i}][all]' and e.get('checked')]
                check(f'{name}: grubość obrzeża', selected[0] if len(selected) == 1 else None,
                      next(iter(b['edges'].values())))
                check(f'{name}: dekor obrzeża', value(f'obrzeze_kolor_{suffix}_all'), value(f'plyta_kolor_{p}'))
                structure = [e['value'] for e in fields.values() if e.get('name') == f'plyta_struktura[{p}]' and e.get('checked')]
                check(f'{name}: struktura obrzeża', value(f'obrzeze_struktura_{suffix}_all'), structure[0] if len(structure) == 1 else None)
            if checked(f'wregowanie_{suffix}'):
                errors.append(f'{name}: wręgowanie wymaga osobnej weryfikacji (poza automatycznym planem)')
            mode = value(f'typ_frontu_{suffix}')
            if mode not in ('', None, 'nawierty_dowolne'):
                errors.append(f'{name}: nieobsługiwany szablon obróbki {mode!r}')
            actual_holes = []
            for kind, side in [('face', 'plaszczyznie'), ('edge', 'czole')]:
                if mode != 'nawierty_dowolne' or not checked(f'wiercenie_w_{side}_{suffix}'):
                    continue
                rows = {}
                for key in fields:
                    match = re.fullmatch(rf'wiercenia_w_{side}_{suffix}_(\d+)_(.+)', key)
                    if match:
                        rows.setdefault(match[1], {})[match[2]] = value(key)
                for row in rows.values():
                    if row.pop('typ_nawiertu', 'pojedynczy') != 'pojedynczy':
                        errors.append(f'{name}: wielowiert wymaga osobnej weryfikacji')
                    actual_holes.append(dict(kind=kind, **row))
            def signature(hole):
                return json.dumps({k: normalized(v) for k, v in hole.items()}, sort_keys=True, ensure_ascii=False)
            expected = Counter(map(signature, b['drills']))
            actual = Counter(map(signature, actual_holes))
            for label, delta in [('brak nawiertu', expected-actual), ('nadmiarowy/inny nawiert', actual-expected)]:
                for hole, count in delta.items():
                    errors.append(f'{name}: {label} ({count}×): {hole}')
    return errors
