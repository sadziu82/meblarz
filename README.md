# Meblarz

Parametric furniture design and 3D visualisation tool.

Design rules: [Polish (authoritative)](docs/reguly_projektowania.md),
[English](docs/design_rules.md). The current desk project uses 18 mm laminated
furniture board (EGGER H1318 ST10), HDF 3 mm backs and HDF 3 mm drawer bottoms.

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
venv/bin/python viewer.py projects/desk_drawer_wall.yaml
```

Model type is detected automatically from YAML keys (`niche` → drawer, `carcass` → dresser,
`desk_drawer_wall` → desk wall with drawer tower).

For `desk_drawer_wall`, the desktop, left side and overhead shelves share the
tower's rear plane; a deeper desktop extends towards the user. The left side
runs in two sections separated by a full-width bridge. `desk.width` measures
from its outer edge to the tower; horizontal boards fit inside this opening.
`desk.low_shelf.supports: 1` places a support at the centre, and `2` places their
axes at one third and two thirds of the shelf width. Touching shelf ends are
joined to the desk/tower sides according to the visibility rules. Its `height` is the clearance from the desktop to the shelf's
underside. Partial shelves use `span: partial`, `width` and `side: left|right`.
`overhead.bridge.bottom` sets the underside height of one common board across
the desk and tower. The lower sides end there; the upper module stands on it.
`drawer_tower.upper_shelves` configures the shelves above the drawers but below
this bridge. `overhead.shelf_groups` configures shelves inside the upper module;
wider groups are split at its divider. The example uses open shelving; optional cabinets remain available
through `overhead.cabinets.count`.

`desk.keyboard_tray.position: center` centres the tray between the desk sides.
For `position: offset`, `offset_left` measures from the inner left side to the
tray's left edge. `offset_front` measures from the desktop's front edge.
Two fixed board hangers attach below the desktop, with slide clearance on both
sides of the tray. Select their slides with `slides.model` and optional `slides.nl`;
`travel` cannot exceed that length. `drop` measures from the desktop's upper
surface to the tray's upper surface. Mounting holes and dowel joints are exported.

The measured desk example uses `desk.width_mode: desktop` for the actual desktop
width (1350 mm), and `desk.underside_height` for the floor-to-underside dimension
(845 mm). `overhead.bridge.top` is its finished top height (1640 mm);
`overhead.height` adds the upper module height above it (760 mm).
`overhead.bridge.support: {enabled: true, height: 200, rear_offset: 50}` adds
a vertical stiffening panel beneath the bridge, spanning the desk opening.
The rear offset is measured to the panel's rear face. Its top and end dowel
connections are included in the machining documentation and DXF.
`drawers.align_top_to_desk` aligns the shelf above the drawers with the desktop.
The keyboard tray is 1000 × 500 mm, centred, with `offset_front: 30` measured
back from the desktop's front edge when closed. `clear_height: 100` measures
from the tray top to the desktop underside and takes precedence over `drop`.
Its side boards use black GTV Versalite Plus 400 mm soft-close runners
(`PK-L-H45-400-B-20`), with 400 mm travel and 13 mm side clearance (within the
manufacturer's 12.7–13.0 mm range). At full travel the tray projects 370 mm beyond
the desk front. The 400 mm deep mounting sides and runners start 70 mm behind the tray front
(`slides.offset_front`); `hanger_depth` controls side depth. The database stores separate
fixed and moving mounting patterns from the manufacturer's drawing. Ø3 × 10 mm
wood pilot bores are a project assumption, to match the chosen screws/material.
The manufacturer sheet does not confirm use with a 1000 mm wide tray; this
qualification is included in the export. The Emuca 4193409 alternative has
409 mm length and 285 mm travel, top mounting brackets and a recommended tray
width of 450–600 mm, so it has not been substituted into the side-mount geometry.
`front.mount: overlay` places drawer fronts ahead of the carcass, with `gap`
between fronts and around the outside, and `carcass_gap` behind them.
`desk.stiffeners.above_top` and `desk.stiffeners.floor` add vertical panels
across the desk opening, with `enabled`, `height` and `rear_offset` settings.
The example uses a 130 mm high panel resting on the desktop directly behind
the low shelf (32 mm above it), flush with the furniture rear; the 100 mm high floor panel has a 100 mm rear
offset. The low shelf and its supports move forward by the upper panel thickness
(18 mm), keeping the shelf depth unchanged. End dowels and panel-to-desktop dowels
are included in the machining documentation. `under_top` remains available for
a panel below the desktop; hanger depth is shortened if needed, and an overlap
with the tray or insufficient length for its slides is rejected.

`desk.monitor_setup.enabled` adds a trial ART L-02N stand and two iiyama
XUB2797QSNP-B1 monitors on the low shelf. The stand uses schematic geometry and
an assumed through-mount adapter, not the rear clamp. Position, VESA height,
screen gap and trial hole diameter are adjustable in YAML. The 10 mm hole is
unconfirmed and shown only in the preview; machining exports omit it and all
equipment parts. Disable the section to remove the entire trial setup.
`inward_angle: 5` turns each screen inward by 5 degrees. `left_clearance: 10`
aligns the screens 10 mm from the inner left side independently of the pole;
`offset_x: 0` centres the pole on the shelf,
while `monitor_gap: 10` leaves 10 mm between the rotated enclosures. Both gaps
include the enclosure depth when computing the rotated outline. Display and
VESA plate rotation is shown in the viewer and respected by mouse picking.
`max_vesa_span: 735` models two 367.5 mm arms with equal lengths and different
fold angles; the right elbow folds towards the rear. Each arm is represented
by two equal links (the link split is schematic). `forward_reach: 70` keeps
both VESA mounts within reach while retaining the screen gaps and 50 mm height
above the shelf. Impossible arm reach is rejected.
Monitor envelopes are rounded up to 614 × 364 × 48 mm from the
[manufacturer drawing](https://iiyama.com/f/218728c626978b1d8a33b6befe596294_xub2797qsn-p-dim.pdf).
The [ART listing](https://www.x-kom.pl/p/315118-uchwyt-do-monitora-art-l-02n.html)
does not specify the through-mount drilling diameter; confirm the adapter before fabrication.
`upper_shelves.front_setback` and `secondary.front_setback` measure from the
carcass front, independent of the back thickness. `overhead.desk_back.enabled`
adds a separate white HDF back to each upper bay above the desk; its `rabbet`
settings use the same width, depth and horizontal-edge options as the tower.
The example uses 3 mm backs in 3.2 mm recesses, overlapping supporting edges
by 6 mm where two backs share a panel and 12 mm at external edges. Shelves
are shortened to clear the backs. Setbacks measure from the
carcass front, independent of the back thickness. Secondary shelves divide the
remaining clear height in the configured `fraction` (3/5 in the example).
`overhead.desk_columns: two_equal_tower_and_remainder` produces two desk bays
with the same clear width as the tower bay, plus a narrow bay on the left.
`middle_shelf: true` divides all four upper bays into equal clear heights.
`overhead.middle_shelf_front_setback: 20` sets these shelves back 20 mm from
the carcass front, with their depths adjusted for the back panel in each bay.
White 3 mm backs can sit in `drawer_tower.back.rabbet: {width: 12, shared_width: 6, depth: 3.2, horizontal: true}`.
`rabbet.width: 12` sets the external overlap and `shared_width: 6` the overlap
on shared edges; `depth: 3.2` accommodates the 3 mm HDF thickness.
Two backs leave 6 mm between them across a shared 18 mm panel. Shared edges
are detected from the adjoining back panels, including the common bridge.
`drawer_tower.back.behind_drawers: false` leaves the drawer section open at the rear;
the lower back starts in the shelf above the drawers. Rebates follow the actual
back outline in the viewer, machining sheet and DXF. Omitted `horizontal` defaults
to false; omitted `behind_drawers` defaults to true for older projects.
`front.bottom_overlay` and `front.top_overlay` override the vertical edge reveals:
positive values cover the bottom panel from above and the top panel from below.
The example uses 2 mm at the bottom and 3 mm at the top, so the fronts span Z=16 to Z=848 mm.
For its five overlay fronts, 3 mm gaps give a width of
`600 - 2*3 = 594 mm` and a total front height of `848 - 16 - 4*3 = 820 mm`.
All five fronts are 164 mm high, preserving the 3 mm gaps. With `whole_mm: true`,
computed shelf and
support positions are rounded to millimetres, and keyboard hangers are extended
to the next whole millimetre. Handle holes on an odd-height front move at most
0.5 mm from the exact centre to have whole-millimetre vertical drilling coordinates.
Purchased hardware dimensions and mounting clearances retain their database precision.
The side overlay is `18 - 3 = 15 mm`. These are finished dimensions including edging;
the visible 3 mm gap is independent of the 2 mm front-to-carcass distance.

## Lighting controls (concept preview)

`lighting_controls.preview: true` shows orange location markers for five fixed
rear drawer switches above the slides, and blue markers for hand-gesture sensors
at the ends of other LED runs. `drawers` and `shelves` each accept `enabled` and
`side: left|right`; `drawers.above_slide` controls marker clearance above the runner.
The drawer closes against a switch mounted on the fixed carcass/bracket; intended
logic is closed = off, open = on. Shelf sensors are provisionally toggle controls.
The 6 mm markers are not device envelopes, brackets or validated mounting locations.
They remain stationary, are excluded from cutting/DXF, and generate no holes.
There is no lighting-state simulation. Choose actual models, voltage/current,
actuator travel, brackets and wiring before producing mounting holes. Shelf sensor
quantity and grouping remain configurable design choices, not a purchase list.

## Connections in the measured project

The measured project selects screw-head faces with `joinery.hidden_faces`
(board name → face list, e.g. `upper_top: [+z]`). Paired dowel joints on those
faces become confirmats drilled from the opposite, outer face; partner pilot
holes retain their entry face. Other joints remain dowelled. The upper-module
feet on `module_bridge` retain locating dowels, with confirmats at the upper top.
`overhead.rear_confirmats` adds one underside confirmat under each internal
desk divider, hidden behind the bridge support (`rear_offset: 30` mm).
Outer sides retain dowels because lower-module sides block access from below.
With `mixed_shared_sides: true`, opposed shelf joints on a shared vertical
divider use confirmats on one side and dowels on the other. Screw heads are
covered by the opposing shelf; its dowels move 20 mm along the depth to avoid
the screw bores. Assemble the screwed shelf before fitting the dowelled shelf.
`keep_dowels` maps board names to partners whose connections remain dowelled.

## Export for Meble.pl

Hardware libraries live in `db/slides.yaml` and `db/handles.yaml`. Select a handle
with `front.handle.model`, retaining `vertical: center` and `hole_depth: through`.
Available handles: `GOODHOME-ATOMIA-293-BLACK` (256 mm hole centres),
`GTV-UA-337-160-BLACK` (160 mm) and `GTV-UA-337-320-ALUMINIUM` (320 mm).
Per-project machining values override library defaults; Ø5 is a chosen clearance
bore, not a manufacturer-specified drilling diameter. Hardware sizes retain their
catalogue precision, including projections of 20.5 and 26.5 mm.
The desk project overrides the Atomia handle holes to Ø3 mm through the 18 mm
front, as assumed by the user; their 256 mm spacing and centred placement remain unchanged.

`drawer_tower.drawers.bottom.type` selects `hdf_3` (the current project) or
`board_18`. Legacy `mdf_3` is accepted as an alias for `hdf_3`; new projects
and exports use HDF. The 3 mm HDF bottom is screwed underneath both sides and the rear,
and extends 3 mm into a 3 mm high groove in the front. Its depth is therefore
303 mm for a 300 mm drawer. The project assumes 3 × 16 mm wood screws with
Ø3 through holes in the bottom and Ø2 × 13 mm pilot holes in the box; these
replace the bottom confirmats and front-to-bottom dowels. The 18 mm variant
retains the original thick-board joints. Drilling sheets and DXFs include the
selected joints and front groove. The viewer marks grooves with red cuboids.
LED grooves in the measured project are 10 mm wide and 4 mm deep. Drawer
lighting uses four rails and the underside of the drawer section top, with
20 mm clear front and end margins. Lit shelves use a 50 mm front margin;
tower shelves (including shallow secondary shelves) and the four upper-bay
shelves and the low shelf above the desktop have full-width grooves. The common
bridge groove reaches the left edge and stops 15 mm before the right edge. `offset`
measures to the groove centre, so these front clearances use 25 and 55 mm.
The keyboard tray has no LED groove. The desktop groove reaches the left edge and retains its right rounded-corner
clearance. `end_margin_left` and `end_margin_right` override `end_margin` per side. Meble.pl offers custom CNC grooves from DXF/DWG;
its [service page](https://www.meble.pl/ciecie-cnc) does not list standard
10 × 4 mm groove options, so the machining drawing is subject to their quotation.

Each `led_groove` accepts `wire_groove: {enabled: true, side: left}` for a
surface cable channel from the rear edge to the LED groove. Defaults are
`width: 3.2` and `depth: 3` mm; `side` may be `left` or `right`.
Optional `edge_offset` measures the clear distance from that side to the channel.
The desktop uses 10 mm; the bridge and upper top channels reach the left edge.
The channel uses the same face as the LED groove. It follows the side edge;
for a stopped LED groove it is inset to meet its endpoint without exposing
the side. Viewer marks it red, and machining sheets and DXF include its full
rectangle (`GROOVE_LED_WIRE_W3.2_D3`). The project uses these channels instead
of blind starter bores. The keyboard tray has no LED groove or cable channel.
The upper top uses `overhead.top_led_groove` with the same options, creating
one continuous LED run across the bays and one cable channel. Back rebates
on each machining edge are likewise merged into a continuous rectangle.
The bridge upper rear rebate uses a uniform 6 mm overlap; upper desk backs
are 760 mm tall to match it.
Legacy `wire_entry` remains available for explicitly requested starter bores.

The desk example now has a 310 mm deep tower and matching left side. Its
`GTV-PK-L-H45-300-B` ball-bearing soft-close runners use a 300 mm deep drawer box, leaving 12 mm at the rear
with the current overlay front placement. Side clearance is 13 mm, inside the
manufacturer's 12.7–13.0 mm range. Actual extension is 296 mm.
Fixed and moving slide holes use separate patterns.
`SEVROLL-04897` remains an alternative (300 mm length, 268 ±2 mm travel).
`GTV-PB-G10HX300-H` is catalogued as an undermount runner, for drawer sides up to
16 mm thick. Its pin mounting geometry is not supported by the current side-mounted
drawer generator; selecting it gives an explicit error instead of invalid drilling.
Source URLs are stored with each product in the libraries.

```bash
venv/bin/python export_meblepl.py projects/dresser.yaml
```

The command creates two files in `exports/`:

- `<model>-meblepl.csv` — a PRO100-compatible cut list for **Wczytaj listę formatek z CSV** in Meble.pl. The export leaves edging and grain direction unset, so select them on the site.
- `<model>-wiercenia.md` — dimensions and every drilling position for each board. Meble.pl's CSV import contains only cut-list data; its online drilling options are limited to built-in templates. Use this file when arranging custom drilling with their CNC service.
- `<model>-dxf/` — one AutoCAD R12 DXF per drilled board face. Each file contains the board outline and drilling circles on layers that state the diameter and depth; it can be sent to CNC for custom drilling.

## Controls

| Shortcut | Action |
|---|---|
| **Left drag** | Rotate camera |
| **Right drag** | Pan (axis lock) |
| **Scroll wheel** | Zoom |
| **Left click** | Select board |
| **Ctrl + left click** or **double left click** | Open / close movable element |
| `Shift` + arrows | Rotate camera |
| Arrows | Pan |
| `Ctrl` + `↑` / `↓` | Zoom in / out |
| `A` / `D` | Rotate left / right |
| `W` / `S` | Rotate up / down |
| `Home` | Reset view |
| `P` | Perspective / ortho |
| `N` | Dimensions of selected (next N: +holes) |
| `H` | Help (shortcut list) |
| `+` / `-` | Open / close all drawers |
| `Ctrl+O` | Open YAML file |
| `Ctrl+R` | Reload current file |
| `2×Esc` or `Ctrl+Q` | Quit |

When started from an interactive SSH terminal, the viewer also accepts these
keyboard controls from standard input. This lets you control the VNC view even
when the VNC client uses `-viewonly`; the terminal is restored on exit.

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
  thickness:        18   # Board thickness — sides / rear / front [mm]
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
  thickness:        18   # Furniture board — top, bottom, carcass sides [mm]
  back_thickness:    0   # 0 = open back (recommended for drawers)
  drawer_thickness: 18   # Furniture board — drawer box parts [mm]
  drawer_bottom:    18   # Furniture board — drawer box bottom [mm]

plinth:
  height:      100   # plinth height [mm]; 0 = no plinth
  inset_front:  15   # plinth inset from front face [mm]
  inset_side:   15   # plinth inset from sides [mm]

rail:                   # horizontal rail between drawers (with LED groove)
  depth:      100       # rail depth [mm]
  thickness:   18       # Board thickness [mm]
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

