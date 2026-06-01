# Meblarz

Narzędzie do parametrycznego projektowania mebli i wizualizacji 3D.

## Wymagania

```bash
# Debian/Ubuntu – sterownik OpenGL NVIDIA
sudo apt install libglx-nvidia0

# Środowisko Python
python3 -m venv venv
venv/bin/pip install PyQt6 PyOpenGL PyOpenGL_accelerate numpy PyYAML
```

## Uruchamianie

```bash
venv/bin/python viewer.py projekty/szuflada.yaml
venv/bin/python viewer.py projekty/komoda.yaml
```

Typ modelu wykrywany automatycznie po kluczach YAML (`niche` → szuflada, `carcass` → komoda).

## Sterowanie

| Skrót | Akcja |
|---|---|
| **Lewy drag** | Obracanie kamery |
| **Prawy drag** | Przesuwanie (pan, blokada osi) |
| **Kółko myszy** | Zoom |
| **Lewy klik** | Zaznaczenie elementu |
| `Shift` + strzałki | Obracanie kamery |
| Strzałki | Przesuwanie (pan) |
| `Ctrl` + `↑` / `↓` | Zoom in / out |
| `Home` | Reset widoku |
| `P` | Perspektywa / ortho |
| `N` | Wymiary zaznaczonego (kolejne N: +otwory) |
| `H` | Pomoc (lista skrótów) |
| `+` / `-` | Otwieranie / zamykanie szuflad |
| `Ctrl+O` | Wczytaj plik YAML |
| `Ctrl+R` | Przeładuj bieżący plik |
| `2×Esc` lub `Ctrl+Q` | Wyjście |

## Struktura projektu

```
meblarz/
├── baza/
│   └── prowadnice.yaml         # baza modeli prowadnic kulkowych
├── docs/
│   └── reguly_projektowania.md # zasady projektowania mebli
├── elementy/
│   ├── szuflada.py             # szuflada wewnętrzna bez uchwytu
│   └── komoda.py               # szafka z szufladami wewnętrznymi
├── projekty/
│   ├── szuflada.yaml           # przykład: samodzielna szuflada
│   └── komoda.yaml             # przykład: komoda z szufladami
├── tests/
│   ├── test_szuflada.py
│   └── test_komoda.py
└── viewer.py                   # aplikacja 3D
```

---

## Format YAML — szuflada wewnętrzna

```yaml
niche:
  width:  410   # szerokość wnęki [mm]
  height: 420   # wysokość wnęki [mm]
  depth: 1000   # głębokość wnęki [mm]

material:
  thickness:        18   # grubość MDF boczków/tyłu/frontu [mm]
  bottom_thickness: 18   # grubość dna skrzynki [mm]

slides:
  model: GTV-H53   # ID modelu z baza/prowadnice.yaml

front:
  top_gap:    50   # przerwa górna frontu [mm] (50 = bez uchwytu)
  inset:     1.5   # cofnięcie frontu względem lica [mm]
  side_gap:    3   # szczelina boczna [mm]
  bottom_gap:  3   # szczelina dolna [mm]
```

**Prowadnice:** `GTV-H45` (głębokość ≤ 600 mm), `GTV-H53` (głębokość > 600 mm).

---

## Format YAML — komoda z szufladami

```yaml
carcass:
  width:  800    # szerokość zewnętrzna [mm]
  height: 2070   # całkowita wysokość mebla wliczając cokoł [mm]
  depth:  1100   # głębokość zewnętrzna [mm]
  placement: freestanding
  # placement: freestanding | builtin_left | builtin_right | builtin_both
  # freestanding = oba boki widoczne → kołki
  # builtin_*    = boki przy ścianie niewidoczne → konfirmaty od tej strony

material:
  thickness:        18   # MDF – wierzch, spód, boki korpusu [mm]
  back_thickness:    0   # 0 = tył otwarty (zalecane dla szuflad)
  drawer_thickness: 18   # MDF – elementy skrzynki szuflady [mm]
  drawer_bottom:    18   # MDF – dno skrzynki szuflady [mm]

plinth:
  height:      100   # wysokość cokołu [mm]; 0 = brak cokołu
  inset_front:  15   # wcięcie cokołu od lica frontu [mm]
  inset_side:   15   # wcięcie cokołu od boków [mm]

rail:                   # poprzeczka między szufladami (z rowkiem LED)
  depth:      100       # głębokość poprzeczki [mm]
  thickness:   18       # grubość MDF [mm]
  led_groove:
    width:    12        # szerokość rowka [mm]
    depth:     4        # głębokość rowka [mm]
    face:   bottom      # rowek na spodniej ścianie poprzeczki
    offset:   20        # odległość od przedniej krawędzi [mm]

drawers:
  count: 4
  distribution: equal   # equal | custom

  # Przy distribution: custom — lista wysokości od najniższej do najwyższej.
  # Można podać mniej wartości niż count — reszta wyliczona równo.
  # heights: [380, 380, 180]

  # Tryb interpretacji podanych wysokości (dotyczy tylko distribution: custom):
  # height_mode: front      # (domyślnie) wysokość frontu szuflady
  # height_mode: niche      # wysokość wnęki (front_H = niche_H − top_gap − bot_gap)
  # height_mode: interior   # max wysokość zawartości (side_H ≥ h; front_H = ⌊3h/2⌋)
  # Aliasy numeryczne: 1 = niche, 2 = interior, 3 = front

slides:
  model: GTV-H45   # ID modelu z baza/prowadnice.yaml

front:
  inset:      1.5   # cofnięcie frontów względem lica korpusu [mm]
  side_gap:     3   # szczelina boczna każdego frontu [mm]
  bottom_gap:   3   # szczelina pod każdym frontem [mm]
  top_gap:     50   # przerwa na palce nad każdym frontem [mm]
```

### Tryby height_mode

| Tryb | Co podajesz | Przeliczenie |
|---|---|---|
| `front` (domyślny) | wysokość frontu | bez przeliczenia |
| `niche` | wysokość wnęki na szufladę | `front_H = h − top_gap − bot_gap` |
| `interior` | max wysokość rzeczy w szufladzie | `front_H = ⌊3h/2⌋` (min. front dla `side_H ≥ h`) |

### Podział wysokości (distribution: custom, częściowa lista)

Jeśli `len(heights) < count`, brakujące szuflady (od góry) wyliczane są jako równy
podział pozostałej dostępnej wysokości. Brakujące zawsze traktowane jako `front_H`.

---

## Testy

```bash
venv/bin/python -m pytest tests/ -v
```
