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
venv/bin/python viewer.py projects/kitchen_tall_unit.yaml
```

Model type is detected automatically from YAML keys (`niche` → drawer, `carcass` → dresser,
`desk_drawer_wall` → desk wall with drawer tower, `kitchen_tall_unit` → two-column kitchen tall unit).

## Kitchen tall unit

`kitchen_tall_unit.panels.top` and `.bottom` independently select `shared`
(one full-width board) or `separate` (one board per column). All four combinations
are supported. The project selects `shared` for both: two 1350 × 610 × 18 mm
boards. Omitting the settings preserves the older shared top and separate bottoms.
Each column keeps its own side boards and four adjustable legs in either mode.

`kitchen_tall_unit.fridge_ventilation` sets the rear ventilation opening at the
plinth, bottom, divider above the fridge, and top independently. Defaults are
500 × 40 mm; `guide.width`/`guide.depth` default to 3.2 × 2 mm. The cut-list
boards remain rectangular. A groove marks a contour segment only when its axis
is at most `guide.max_edge_offset` (default 50 mm) from a parallel edge.
Otherwise shallow Ø3 × 2 mm holes mark that segment about every 20 mm, starting
and ending 5 mm from its ends. Default openings have two grooved and two drilled
segments on the plinth, and one grooved and two drilled segments on each
horizontal board. The marked interior must be cut out separately after the
rectangular boards are ordered; marks alone do not make an air passage. A
separate furniture-board back closes the upper
cabinet ahead of the 40 mm rear channel (`upper_back`); its thickness follows
`material.thickness` unless overridden. `upper_back.clearance` keeps its rear
face 10 mm ahead of the ventilation opening by default. The guide geometry is
also recorded in the drilling sheet and DXF when production export is allowed.

`projects/kitchen_tall_unit.yaml` is a separate two-column appliance cabinet:
left side is a Samsung BRB38G705DWWEF refrigerator niche with a lift-up cabinet
above it; right side has three configurable overlay drawer fronts, an Electrolux
EOE7C31Z oven niche, an Electrolux EMS4253TMK microwave niche, and a two-door
upper cabinet without a vertical partition. The supplied starting dimensions are
2420 × 1350 × 610 mm with a 100 mm plinth, 714 mm left clear width and a
600 mm wide right carcass. `plinth.inset_front: 10` recesses only the plinth's
front edge; its side boards still reach the cabinet's rear plane.

Appliance boards are preview-only. The Samsung product sheet gives an appliance
envelope of 690 × 1935 × 550 mm and a 714 × 1940 × 580 mm niche. The Electrolux
oven installation niche is 560 × 590 × 550 mm and the appliance fascia is
596 × 594 mm. The microwave niche is 560 × 380 × 550 mm and its fascia is
595 × 388 mm. Its total depth is 377 mm (20 mm fascia plus 357 mm behind
the carcass front); the 550 mm niche is installation space, not body depth.
These values are held in the appliance-model library in
`parts/kitchen_tall_unit.py`: YAML selects `model`, and the vertical layout is
calculated from the selected model, board thickness and furniture-front reveals.
Appliance installation clearances and fascia offsets belong to the model library;
they cannot be overridden in the project. Each Electrolux model records its
installation manual and page. The oven overlap is derived from its fascia top
and niche height (594 − 590 = 4 mm).

The generator derives carcass joints from panel contacts, not from a list of
named plates or manually entered hole coordinates. `parts/joinery.py` is shared
geometry code; `kitchen_tall_unit.joinery` selects hidden/visible fasteners,
end-panel joints, edge distances and maximum spacing. Gaps greater than
`dowel_between_confirmats_above` (default 200 mm) between adjacent confirmats
automatically receive a midpoint dowel with paired blind bores. The default uses confirmats
on hidden faces and dowels on exposed cheeks. A plinth is a separate assembly,
attached to the legs with clips; it is not screwed through the cabinet bottom.
The eight selected Emuca Bone 2024417 legs use four 64 × 64 mm fixing centres
each. The underside of the bottom panel receives Ø2.5 × 12 mm pilot bores for
Ø4 wood screws; this pilot size is a project choice. The plinth-clip fixing
still needs a selected mounting method. Emuca specifies 40 kg per leg and a
100 kg tested module load; verify the filled tall cabinet's load before buying.
Both shared/separate top/bottom modes generate their own matching bores.
`kitchen_tall_unit.joinery.column_ties` adds aligned Ø3 through-bores in both
adjoining column cheeks. By default four evenly spaced levels run from 100 mm above
the lower panel to 100 mm below the upper panel, 500–800 mm apart, with two
bores per level at 100 mm from the front and 100 mm from the rear. The YAML
controls the offsets, spacing and diameter. Select a suitable through-fastener
and its retainer for the two-board joint.
The same rule applies to every pair of touching independent carcasses whose
outer side boards are tagged by the generator; internal dividers are excluded.

Drawer and hinge templates live in `db/drawer_systems.yaml` and `db/hinges.yaml`.
The three Axis Pro variants are D/B/A (`PB-AXISPRO-KPL600D/B/A`): purchased metal
side heights are 200/120/86 mm, while cut rear heights are 199/116/84 mm.
For clear width LW and nominal length NL, the 16 mm bottom is `(LW-75) × (NL-24)`
and the 16 mm rear is `(LW-87) × rear_height`. Here bottoms are 489 × 576 mm,
rears 477 mm wide. NL+10 is the required installation depth, not the bottom size.
The chosen GTV circular runner holes are at 37/261/389 mm for NL600; other supported
lengths select their own pattern. Front/rear connector pilots are Ø2 × 12 mm.
Runner pilots Ø3 × 12 mm are a project choice for wood screws. Metal telescoping
profiles are simplified preview geometry, excluded from cutting; their fixed
parts stay in the cabinet when a drawer opens. GTV recommends extra railing for
the 300 mm front (over 284 mm); that accessory requires its own selected template.

GTV INHC H04 hinges get Ø35 × 12 mm cups at K=3 mm (centre 20.5 mm from edge),
45 mm cup screw spacing with a 9.5 mm offset, and 32 mm plate screw spacing at
37 mm from the carcass front. Ø2.5 × 10 mm pilots are a project choice. Cup count
is currently a project height-based rule, not a certified load calculation.
Furniture fridge doors have independent cup hinges in addition to sliding
couplers. `fridge.fronts.sliding_connectors` positions preview centres at
`width_fraction_from_hinge: 0.75` and `height_fractions: [0.25, 0.75]`.
The horizontal 90 × 38 mm markers mirror automatically for right hinges.
These proportions are a user-selected illustration, not Samsung mounting data. Lift-up hinges attach to the top board; their -1 mm overlay adjustment
retains the 3 mm top reveal. Unverified gas-lift holes have been removed; the
selected lift's template and force remain to be specified.

`handles.model` selects GTV UA-00-337160-20M from the existing handle library:
160 mm fixing centres, 180 mm overall length, Ø5 through bores in this project.
Drawer handles are exactly centred (a 160.5 mm high front has its centre at
80.25 mm; do not independently round and lose centring). Door handles are vertical
on the free edge: lower-front top corner, upper-front bottom corner. The flap
handle is horizontal at its bottom edge. `door_edge_offset`, `door_end_offset`
(nearest fixing hole) and `lift_bottom_offset` default to 50 mm. These are design
choices, not mandatory manufacturer offsets. Preview handles follow the complete
front motion, including rotation and picking.

Generation always validates bore entry faces, depths and intersecting bore
envelopes (`parts/machining.py`). A collision raises an error naming the part and
both bores, with local coordinates; it never silently moves drilling. Resolve
it in YAML. Validation is conservative near bore ends; it does not yet cover
arbitrary groove intersections or full hardware/door swept-volume collisions.
If a construction rule is missing, agree it with the user and implement it as a
rule; do not patch generated parts or invent a manufacturer's drilling pattern.

Missing machining templates are structured `DrawerModel.machining_issues`.
Preview remains available and shows a status message with the missing operations.
All manufacturing writers (CSV, drilling sheet and DXF) reject such a model before
writing files; there is no override switch. The current kitchen is therefore
**not yet exportable for production**: AXIS bottom-to-metal-side fixings, flap
lifts, Samsung sliding couplers, and plinth-clip fixing still need
verified mounting templates. Filling in those library templates must resolve the
issues; removing an error flag without adding the missing machining is not a fix.

Sources: [GTV AXIS PRO, pp.6–8](https://assets.gtv.com.pl/assets/attachments/karta_techniczna/Axis_Pro_karta%20techniczna_3.pdf),
[GTV INHC H04](https://api2.gtv.com.pl/pimcore/assets/attachments/karta_techniczna/ZM-INHC_H04_07.12.2021.pdf),
[GTV handle](https://gtv.com.pl/produkt/UA-00-337160-20M/),
[handle placement principles](https://capramontandco.com/pages/capramont-co-cabinet-handle-size-placement-guide).

`right_column.microwave.side_cutout` defines a rear-edge notch in the outer
right side panel, behind the microwave. The current project marks a 280mm-high,
120mm-deep notch, centred vertically in the microwave niche. Shallow Ø3 × 2mm
pilot marks on the panel's inner face trace the three cut edges, up to four
per edge, with the end marks 5mm from its corners. The existing rear panel edge
needs no marks. The preview and DXF show the guide, but
the cut-list panel remains rectangular; remove the marked material manually.
Measure the outlet and cable route before cutting.

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
Overlay fronts share rules from `parts/front_rules.py`: 2 mm at each outside
side, 3 mm at the bottom/top of the front group, 3 mm between stacked fronts,
and 2 mm between paired doors. Overlays are derived from carcass thickness:
16 mm at the sides and 15 mm at the ends for 18 mm board.
The desk project now has five 596 × 169 mm fronts spanning Z=3 to Z=860 mm.
The kitchen has 596 mm drawer fronts and two 297 mm upper doors.
Appliance installation requirements take precedence at appliance boundaries.
Front divisions use 0.5 mm increments, distributing any remainder without
changing the total height or gaps. Handle holes remain centred.
`front.mount: overlay` enables these rules for the standalone drawer and dresser;
their existing inset examples retain their explicit recess and finger gaps.
For a standalone drawer, `front.carcass_thickness` defaults to drawer board
thickness and the niche dimensions describe the clear opening.
The desk's legacy `whole_mm` option applies to other furniture positions, not
overlay-front divisions or centred handle holes.

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

Samsung door geometry is stored in the model library from manual page 32: freezer
Z=50–671 mm, refrigerator Z=735–1882 mm relative to the appliance base.
The furniture-front gap is 3 mm centred at appliance Z=703 mm. In the kitchen
project (appliance base at floor Z=118 mm), that gap is Z=819.5–822.5 mm.
The fridge `fronts` section only specifies hinge side and panel thicknesses;
width is derived from the carcass, and reveals/gaps use the common furniture
rules in `parts/front_rules.py`, not per-appliance YAML settings.
Drawer `front_heights: [300, 250, null]` automatically sizes the top drawer front
to preserve alignment with the freezer furniture front (currently 160.5 mm).
