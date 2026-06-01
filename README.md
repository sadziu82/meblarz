# Meblarz

Parametric furniture design and 3D visualisation tool.

## Requirements

```bash
# Debian/Ubuntu — NVIDIA OpenGL driver
sudo apt install libglx-nvidia0

# Python environment
python3 -m venv venv
venv/bin/pip install PyQt6 PyOpenGL PyOpenGL_accelerate numpy PyYAML
```

## Running

```bash
venv/bin/python viewer.py projects/drawer.yaml
venv/bin/python viewer.py projects/dresser.yaml
```

Model type is detected automatically from YAML keys (`niche` → drawer, `carcass` → dresser).

## Controls

| Shortcut | Action |
|---|---|
| **Left drag** | Rotate camera |
| **Right drag** | Pan (axis lock) |
| **Scroll wheel** | Zoom |
| **Left click** | Select board |
| **Ctrl + left click** | Open / close movable element |
| `Shift` + arrows | Rotate camera |
| Arrows | Pan |
| `Ctrl` + `↑` / `↓` | Zoom in / out |
| `Home` | Reset view |
| `P` | Perspective / ortho |
| `N` | Dimensions of selected (next N: +holes) |
| `H` | Help (shortcut list) |
| `+` / `-` | Open / close all drawers |
| `Ctrl+O` | Open YAML file |
| `Ctrl+R` | Reload current file |
| `2×Esc` or `Ctrl+Q` | Quit |

## Project structure

```
meblarz/
├── db/
│   └── slides.yaml             # ball-bearing slide model database
├── docs/
│   ├── reguly_projektowania.md # design rules (Polish — authoritative)
│   └── design_rules.md         # design rules (English translation)
├── parts/
│   ├── drawer.py               # inner drawer without handle
│   └── dresser.py              # chest of drawers
├── projects/
│   ├── drawer.yaml             # example: standalone drawer
│   └── dresser.yaml            # example: dresser with drawers
├── tests/
│   ├── test_drawer.py
│   └── test_dresser.py
├── config.yaml                 # viewer configuration
└── viewer.py                   # 3D viewer application
```

---

## YAML format — inner drawer

```yaml
niche:
  width:  410   # niche width [mm]
  height: 420   # niche height [mm]
  depth: 1000   # niche depth [mm]

material:
  thickness:        18   # MDF thickness — sides / rear / front [mm]
  bottom_thickness: 18   # box bottom thickness [mm]

slides:
  model: GTV-H53   # model ID from db/slides.yaml

front:
  top_gap:    50   # front top gap [mm] (50 = handleless)
  inset:     1.5   # front inset from carcass face [mm]
  side_gap:    3   # side gap [mm]
  bottom_gap:  3   # bottom gap [mm]
```

**Slides:** `GTV-H45` (depth ≤ 600 mm), `GTV-H53` (depth > 600 mm).

---

## YAML format — dresser with drawers

```yaml
carcass:
  width:  800    # external width [mm]
  height: 2070   # total furniture height including plinth [mm]
  depth:  1100   # external depth [mm]
  placement: freestanding
  # placement: freestanding | builtin_left | builtin_right | builtin_both
  # freestanding = both sides visible → dowels
  # builtin_*    = sides against wall hidden → confirmats on that side

material:
  thickness:        18   # MDF — top, bottom, carcass sides [mm]
  back_thickness:    0   # 0 = open back (recommended for drawers)
  drawer_thickness: 18   # MDF — drawer box parts [mm]
  drawer_bottom:    18   # MDF — drawer box bottom [mm]

plinth:
  height:      100   # plinth height [mm]; 0 = no plinth
  inset_front:  15   # plinth inset from front face [mm]
  inset_side:   15   # plinth inset from sides [mm]

rail:                   # horizontal rail between drawers (with LED groove)
  depth:      100       # rail depth [mm]
  thickness:   18       # MDF thickness [mm]
  led_groove:
    width:    12        # groove width [mm]
    depth:     4        # groove depth [mm]
    face:   bottom      # groove on the bottom face of the rail
    offset:   20        # distance from front edge [mm]

drawers:
  count: 4
  distribution: equal   # equal | custom

  # With distribution: custom — heights list from lowest to highest.
  # Fewer values than count allowed — remainder split equally.
  # heights: [380, 380, 180]

  # How to interpret the given heights (only with distribution: custom):
  # height_mode: front      # (default) front height
  # height_mode: niche      # niche height (front_H = niche_H − top_gap − bot_gap)
  # height_mode: interior   # max contents height (side_H ≥ h; front_H = ⌊3h/2⌋)
  # Numeric aliases: 1 = niche, 2 = interior, 3 = front

slides:
  model: GTV-H45   # model ID from db/slides.yaml

front:
  inset:      1.5   # front inset from carcass face [mm]
  side_gap:     3   # side gap per front [mm]
  bottom_gap:   3   # bottom gap per front [mm]
  top_gap:     50   # finger clearance above each front [mm]
```

### height_mode summary

| Mode | Input | Conversion |
|---|---|---|
| `front` (default) | front height | none |
| `niche` | niche height per drawer | `front_H = h − top_gap − bot_gap` |
| `interior` | max contents height | `front_H = ⌊3h/2⌋` (min front for `side_H ≥ h`) |

### Height distribution (distribution: custom, partial list)

If `len(heights) < count`, the missing drawers (from the top) are calculated as an equal
split of the remaining available height. Missing values are always treated as `front_H`.

---

## Tests

```bash
venv/bin/python -m pytest tests/ -v
```
