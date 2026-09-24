# Knowledge base — furniture design rules

> **Authoritative source: [reguly_projektowania.md](reguly_projektowania.md) (Polish)**
> This file is an English translation. In case of any discrepancy the Polish version takes precedence.

> Explicit project/YAML settings override defaults. Rules 4–24 and 53–57 describe legacy inset drawers with 18mm bottoms; rules 63–65 cover HDF and overlay variants. These project rules do not certify structural capacity or configurator compatibility.

## MATERIALS AND DIMENSIONS

1. The client provides external dimensions — the designer calculates internal ones.
2. Default structural material: 18mm laminated furniture board (EGGER H1318 ST10 Natural Wild Oak in the current project), not HDF. Cabinet backs are normally HDF 3mm; the upper refrigerator cabinet uses furniture board (rule 87).
3. Use HDF back for cabinets with doors or shelves unless the project specifies a furniture-board back. For drawer cabinets — back is open.

---

## DRAWERS

### Handleless inner drawers with ball-bearing slides

4. Handleless drawers (opened by fingers) — front top gap **50mm**.
5. Drawer front recessed **1.5mm** from the carcass face.
6. Box side height = **2/3 of front height**. For very small or very large drawers — confirm with client.
7. Box bottom — 18mm furniture board by default; see rule 63 for HDF 3mm. Exception: check slide spec (some kitchen slides require 16mm).
8. Rails between drawers only between them — no extra rail at top or bottom. Exception: kitchen furniture may have an extra top rail as worktop reinforcement.
9. The drawer box has no separate inner front — the front panel serves both aesthetic and structural roles.
10. The box starts at Y = `front_inset + board_thickness` — the rear face of the front panel defines the start of sides and bottom. Box and front touch, they do not overlap.
11. Front side gap and bottom gap: **3mm**.
12. The bottom lies under the sides (sides stand on the bottom). Bottom has full external width `box_W_ext` and full depth `box_depth`. Bottom of the box is **2mm higher** than the bottom of the front (box does not protrude below the front).
13. External box width: `box_W_ext = niche_W − 2 × slide_clearance`.
14. Box depth: `box_depth = niche_D − (front_inset + front_thickness) − rear_clearance`. *(Note: the full front thickness including inset is subtracted because the box starts behind the front rear face — rule 10.)*
15. The box rear has full external width `box_W_ext` (same as the bottom). It sits on the bottom at the rear edge of the box.
16. Box sides have depth `box_depth − board_thickness` — shortened by the rear wall thickness. Sides fit between the rear face of the front and the rear wall (they do not extend past the back).
17. Box depth = slide NL (for inner drawer: SKL = NL). Select the **largest available NL** not exceeding `max_box_depth`. The slide length determines the box depth, not the other way around.
18. Box depth can be set explicitly by specifying `slides.nl` in the drawer or dresser YAML. The given NL must exist in the slide model's `available_lengths_mm` list and must not exceed `max_box_depth`. If `slides.nl` is omitted, the program automatically selects the maximum fitting NL (rule 17).

---

## INNER DRAWER BOX JOINTS

19. Box joint overview:
    - Front (visible) ↔ sides, front ↔ bottom: **wooden dowels** (rules 34 and 45, aesthetics).
    - Bottom ↔ sides, bottom ↔ rear, rear ↔ sides: **confirmats** (hidden surfaces).
20. **Bottom ↔ Left side / Right side**: confirmats drilled from below the bottom (+Z direction) through the bottom into the side base. Y positions: 1/4 and 3/4 of side depth (`box_depth − board_thickness`). X position: centre of side thickness.
21. **Rear ↔ Left side / Right side**: confirmats drilled from the rear face of the rear wall (−Y direction) through the rear into the back edge of the side. Z positions: 1/4 and 3/4 of side height (`side_H`). X position: centre of side thickness.
22. **Bottom ↔ Rear**: confirmats drilled from below the bottom (+Z) through the bottom into the rear wall base. X positions: 1/4 and 3/4 of external width (`box_W_ext`). Y position: centre of rear wall depth.
23. **Front ↔ Left side / Right side**: ø8mm dowels. Holes in the rear face of the front (in-plane, depth 11mm) and in the side front end (depth 27mm). Z positions: 1/4 and 3/4 of side height (`side_H`) from the side base. X position: centre of side thickness.
24. **Front ↔ Bottom**: **always two dowels** ø8mm for this drawer type. Holes in the rear face of the front (in-plane, depth 11mm) and in the bottom front end (depth 27mm). X positions: 1/4 and 3/4 of external bottom width (`box_W_ext`). Z position: centre of bottom thickness.

---

## SLIDES

25. Use the selected slide model and its specifications. Ask for the model only if it has not been chosen; thickness and mounting vary.
26. Standard side ball-bearing: ~12.5mm per side. Deep/heavy drawers may require thicker slides.
27. For deep niches using ordinary side ball-bearing slides, consider heavy-duty slides (e.g. GTV H53: 19.5mm clearance, 100kg load, NL 300–1100mm). Do not apply this preference to a selected metal-side drawer system such as AXIS PRO; its model sheet governs the allowed NL, load and minimum carcass depth.
28. Slide models are stored in `db/slides.yaml`. In the drawer YAML specify `slides.model: <ID>` (e.g. `GTV-H53`) — the program selects NL and mounting dimensions automatically. Optionally `slides.nl: <NL>` forces a specific length (rule 18).
29. Rear clearance (slide must not protrude beyond carcass): default **20mm**.
30. Slide mounting height: slide bottom at **50mm from the box bottom**. From the slide model (dimension H) calculate the exact mounting hole axis height — both on the drawer box and on the carcass side.
31. Slide mounting holes: dimensions and spacing per the slide product datasheet — use data from `db/slides.yaml`.
32. Mounting hole layout on the carcass must match the drawer type (standard, push-to-open, soft-close, etc.) — check the slide documentation for positions relative to drawer front and rear.

---

## JOINTS — GENERAL RULES

33. Standard joints require **at least two fastening points**, including mixed fasteners. A single additional upper-module screw supplements two dowels (rule 74). The current generator uses one point on edges shorter than 40mm; this geometric exception does not certify load capacity.
34. Fastener selection:
    - **Hidden** surfaces → confirmats.
    - **Visible** surfaces → wooden dowels.
    - **Visible surfaces requiring reinforcement** → ask client (dowels + internal screws, brackets, lamello, etc.).

---

## JOINTS — CONFIRMATS

35. Confirmats require a head countersink; the following current-model assumptions must match the purchased screw and tooling:
    - Through hole: **ø5mm** or **ø4mm**
    - Head countersink: **ø11mm × 4.5mm deep**
    - Threaded hole in the second element: **ø5mm** or **ø4mm**, min. 35mm deep
36. Threaded hole depth = confirmat length − first element thickness, minimum **35mm**. For a 50mm confirmat in 18mm board = 32mm → round up to 35mm.
37. Confirmat placement — at **1/4 and 3/4** of the joined edge length, max 100mm from either end. If spacing between confirmats > 300mm — add intermediate ones at equal intervals.

---

## JOINTS — WOODEN DOWELS

38. Wooden dowels: **ø8mm × 35mm** as standard.
39. Dowel hole depths:
    - In the **face** of an element: **11mm**
    - In the **end** of an element: **27mm**
40. Dowel placement — same as confirmats: **1/4 and 3/4** of the shared dimension of the joined elements, max 100mm from either end.
41. For holes joining two elements — the 1/4 and 3/4 positions are measured along the **shared dimension** (the shorter of the two).

---

## LOCAL BOARD COORDINATE SYSTEM

42. Hole positions are always given in the **local coordinate system** of the board, regardless of its orientation in the furniture:
    - **x** — horizontal axis (along board width)
    - **y** — vertical axis (along board height)
    - **thickness** — always the board thickness; does not affect the in-plane hole position and is not given as a separate coordinate
43. Holes in the **end** (dowels, confirmat thread entering from the end) always lie at the centre of the board thickness. Position given only as (x, y).
44. In-plane hole — position as (x, y) from the bottom-left corner of the visible face.

---

## AESTHETICS

45. Do not expose structural holes on visible faces. Through holes for handles are an exception, concealed by hardware. Drill dowels from the inner/hidden face.
46. Drawer front: dowel holes only from the box side (rear of front), drilled in-plane.

---

## CARCASS

### Structure and dimensions

47. The client provides external furniture dimensions. **`carcass.height` is the total height from floor to top, including the plinth.** Top and bottom panels have full external width (`width`). Sides fit between them. Internal dimensions: `int_W = width − 2×thickness`, `int_H = (height − plinth.height) − 2×thickness`, `int_D = depth`.
48. Back of a drawer cabinet — **open** (rule 3). Do not use HDF backs behind drawers; HDF drawer bottoms are a separate part.
49. Cabinet type `placement` determines side visibility: `freestanding` — both sides visible; `builtin_left/right` — one side against a wall (hidden); `builtin_both` — both sides hidden.

### Carcass joints

50. **Top ↔ sides** and **bottom ↔ sides** — drilling direction depends on joint type:
    - **Dowels** (visible side): top — in-plane hole from the **bottom face** (inside cabinet); bottom — in-plane hole from the **top face** (inside cabinet). Matching end holes in the sides.
    - **Confirmats** (hidden side): top — head on the **top face** (hidden by worktop/enclosure), drilled top-down through top into side end; bottom — head on the **bottom face** (under cabinet), drilled bottom-up through bottom into side end.
51. **Rail ↔ sides** — drilling direction depends on side visibility:
    - **Dowels** (visible side): element 1 from the **inner** face of the side (hidden inside cabinet), in-plane; element 2 — rail end.
    - **Confirmats** (hidden side): element 1 from the **outer** face of the side (against the wall, hidden), drilled through side into rail end; element 2 — rail end.
52. Lower kitchen cabinet (no top, with load-bearing rails) — separate type, separate rules.

### Height distribution — drawers with rails

53. Number of rails between drawers = `count − 1`. Each rail has width `int_W` and depth per spec (default 100mm).
54. Element sequence bottom to top (per drawer): `bottom_gap` (3mm) → drawer front → `top_gap` (50mm, finger clearance) → rail (18mm) → … → last drawer front → `top_gap` → underside of top. A rail does **not** follow the top-most drawer.
55. Front height with equal distribution (`distribution: equal`): `front_H = (int_H − (count−1)×rail_thickness − count×(top_gap + bottom_gap)) / count`. Round down; add any remainder to the **lowest** drawer.
56. With custom distribution (`distribution: custom`) — the `heights` list is given **from lowest to highest** drawer. Fewer values than `count` may be given — missing drawers (highest ones) are calculated as an equal split of the remaining height. Missing values are always interpreted as `front_H`.
57. Parameter `height_mode` (only with `distribution: custom`) specifies what the given heights represent:
    - `front` (default) — front height.
    - `niche` — niche height: `front_H = h − top_gap − bottom_gap`.
    - `interior` — max contents height (= `side_H`): `front_H = ⌊3h/2⌋` (minimum front_H yielding `side_H ≥ h`).
    - Numeric aliases: `1` = `niche`, `2` = `interior`, `3` = `front`.

### LED rail groove

58. The underside LED groove lights the drawer below. The legacy dresser uses 12×4mm; the current desk uses 10×4mm with 20mm clear distance from the front. See rule 68 for dimensions and offset conventions.
59. The rail does not reach full carcass depth — open space remains behind it. Default depth: 100mm.

### Plinth

60. The plinth is a separate element mounted under the carcass bottom. `carcass.height` is the total furniture height **including the plinth** — carcass height without plinth = `height − plinth.height`. Parameters: `height` (default 100mm), `inset_front` (inset from front face, default 15mm), `inset_side` (inset from sides, default 15mm). `height: 0` means no plinth.
61. The plinth consists of a front board and two side boards (open back). Front board width: `width − 2×inset_side`. Side board depth: `depth − inset_front − thickness`. *(Side boards start behind the rear face of the front board.)* Joints: confirmats from the outer (bottom) face of the plinth — the plinth underside is not visible in normal use.


## HDF, MACHINING AND THE CURRENT DESK PROJECT

62. Board dimensions, part positions and drilling coordinates may use **0.5mm resolution**. Do not force integer millimetres or shift holes away from their symmetry axis merely to obtain integers. Preserve full precision in intermediate calculations; when rounding manufacturing dimensions to 0.5mm, check totals, reveals and mating-hole alignment. Preserve machining and catalogue precision, such as 3.2mm grooves, 4.5mm countersinks and slide clearances. `whole_mm` remains a legacy project option, not the general rule. Numerical resolution does not imply a ±0.5mm manufacturing tolerance. Thickness variable names do not specify material.

    Meble.pl verification (2026-09-21): [BIZNES meble.pl, February 2014](https://wydawnictwo.meble.pl/gfx/e-wydanie/biznes-meble-pl-2-2014/files/assets/common/downloads/publication.pdf) describes centrum.meble.pl cutting accuracy of 0.1mm. The current [cutting](https://www.meble.pl/rozkroj) and [CNC](https://www.meble.pl/ciecie-cnc) pages checked did not provide numeric confirmation of current tolerances or drilling-coordinate input increments. Historical information does not establish current service specifications.
63. Select `drawers.bottom.type: hdf_3` or `board_18`; `mdf_3` is a legacy alias only. HDF 3mm sits under sides/rear, fixed with small screws from below. Current assumptions: 3×16mm screws, Ø3 through holes in HDF and Ø2×13mm pilots in sides/rear. Confirm screw selection; do not use Ø8 dowels or confirmats to fasten this thin bottom.
64. The HDF bottom enters a groove in the rear face of the front: currently 3mm deep and 3mm high. Check actual material thickness/tool availability before manufacture. Bottom depth is 303mm for NL=300mm. The 3.2mm back rebate is a separate operation and does not automatically change the bottom groove.
65. Calculate overlay fronts separately from inset fronts. Current project: five 594×164mm fronts, 3mm gaps, bottom overlap 2mm, top overlap 3mm. Equal heights result from adjusting the bottom edge. Handle holes are centred and through; Ø3mm is the user's assumption, 256mm centres come from the selected handle.
66. Use white HDF 3mm backs, leaving the drawer section open. Back recess thickness is 3.2mm; overlap into supports is 12mm at outer edges and 6mm on shared edges. Across an 18mm board, two backs leave 6mm between them. Metadata `rabbet.depth` is 3.2mm, `width` is 6/12mm overlap; do not confuse this geometry with configurator tool naming.
67. Each machining face/edge must have **one continuous rectangular rebate**, not disconnected bay segments. Unify cross-sections before merging. The bridge upper rear edge uses 6mm overlap throughout, making the upper desk backs 760mm tall. Other edges or opposite faces may have separate rebates.
68. Current LED grooves: underside, 10×4mm. Clear front distance is 20mm for drawers and 50mm for shelves; `offset` denotes the centreline (25/55mm). Desktop uses its own offset of 30mm. Keyboard tray has no LED groove. Include lighting under the drawer section top and the upper-module top.
69. LED endpoints: shelves between sides and low shelf run full width; bridge starts at the left edge and stops 15mm before the right; upper top stops 18mm before the right. Desktop starts at the left edge and clears its right rounded outline by 20mm. `end_margin_left/right` override `end_margin`. A continuous machined groove can cross dividers; strips/profiles need not be continuous.
70. Add a surface cable channel, 3.2×3mm, from the rear to the LED groove on the same face. `wire_groove.side` selects left/right; `edge_offset` measures clear side distance. Desktop uses 10mm, bridge and upper top 0mm. Stopped grooves default to a channel at their endpoint. Do not use long internal drilling or legacy starter bores in this project. Cable sizing includes insulation and LED electrical requirements.
71. User-reported meble.pl configurator options: widths 3.2/4.3/10.2mm, depths 2–13mm in 1mm increments, offsets 0–50mm. Current LED width 10mm and bottom groove height 3mm require CNC confirmation or an explicit design change. DXF export does not certify standard-service availability.
72. Choose joints by **head visibility and tool access**. `joinery.hidden_faces` lists screw-head faces; other joints remain dowelled. `keep_dowels` preserves selected pairs. Confirmat through holes/countersinks start at the first board's outer face; pilots start at the second board's mating face.
73. Opposing shelves on a shared divider use confirmats on one side and dowels on the other, without intersecting bores. `mixed_shared_sides` handles opposed shelf joints at the same height, shifting dowels at least 20mm along the depth. Assemble the screwed shelf first, then the dowelled shelf covering the heads. This is not a general collision detector.
74. Upper module: locating dowels below, confirmats above. Two internal dividers additionally accept underside confirmats through the bridge, 30mm from the rear and hidden behind its support (`overhead.rear_confirmats`), each supplementing two dowels. Lower sides block underside access beneath outer sides, so those retain dowels. Desktop uses two confirmats per side; on the right the drawer-section shelf conceals the heads and uses offset dowels.
75. Store slide and handle specifications in libraries; NL is not travel. Current drawer slides: GTV soft-close ball-bearing 300mm; keyboard slides: 400mm starting 70mm behind the tray front. Tray 1000×500mm, recessed 30mm, with 100mm clear space below the desktop. Do not transfer mounting patterns/load ratings between models without specifications.
76. Production documentation identifies material, machining face, groove dimensions/extents and hole type/diameter/depth/through status. Preview hardware and trial monitor mounting are excluded from cutting. CSV still leaves edging and grain direction unspecified; complete these before pricing. Budget estimates distinguish verified material prices from service allowances and are not supplier quotations.

77. Without selected control models, use preview location markers only (`lighting_controls.preview`). Fixed drawer switches sit at the rear above the runners; intended logic is closed = off, open = on. Other strips have provisional hand-gesture sensor locations. Orange/blue 6mm markers are not device envelopes or validated mounting locations; they generate no drilling, are excluded from cutting and do not simulate LED operation. Select models, mounting, actuator travel, voltage/current and lighting groups before machining.

## KITCHEN TALL UNIT AND APPLIANCES

78. Model built-in appliances separately as preview envelopes (`fabrication: false`) and niche parameters. Appliance envelope, front width and niche dimensions are distinct. Use the installation drawing for the exact appliance variant before cutting.
79. This project uses two columns on a 100mm plinth: refrigerator plus lift-up upper cabinet on the left; three drawers, oven, microwave and a two-door upper cabinet without a vertical partition on the right. YAML selects appliance models; their niche and fascia dimensions drive the vertical layout together with board thickness and configured reveals. The plinth uses the existing `plinth.inset_front` parameter: its front is currently recessed 10mm, while its side panels still reach the cabinet's rear plane.
80. Samsung BRB38G705DWWEF product data gives a 690 × 1935 × 550mm appliance envelope and a 714 × 1940 × 580mm recommended niche. The niche does not replace manufacturer ventilation, fixing or installation requirements.
81. Electrolux EOE7C31Z niche: 590 × 560 × 550mm; appliance: 594 × 596 × 569mm. Its 3490W electrical requirement must be handled under the manufacturer's installation instructions; furniture documentation is not an electrical design.
82. EMS4253TMK microwave defaults to a 380 × 560 × 550mm niche. Verify the identification plate and installation drawing before production. `right_column.microwave.side_cutout` specifies a rear-edge notch in the outer right panel, behind the appliance: currently 280mm high and 120mm along the cabinet depth, centred vertically in the niche. Mark its three cut edges from the inner face with at most four blind Ø3 × 2mm bores per edge, first and last 5mm from each corner. The existing rear panel edge needs no bores. The DXF guide is not a toolpath; the panel remains rectangular in the cut list and must be cut manually. Reject a cutout that overlaps the appliance or another bore. Measure the socket and cable route before cutting.
82a. User-specified layout: use the oven support TOP as Z datum. Drawer front ends at Z-3, oven fascia extends from Z+5 to Z+594 (visible height 589mm), giving an 8mm reveal. Installation requirements belong to the model library, with manual URLs and page numbers. Projects select the model rather than overriding fascia geometry, support clearance or overlap. The 590mm niche sets the divider underside at Z+590; the 4mm overlap follows from 594−590. With an 18mm divider and 4.5mm lower microwave overhang, the inter-appliance reveal is 9.5mm. The opening is the required 590mm and the appliance body is 589mm; overlaps leaving less than the required niche height are rejected. Microwave overhangs are 3.5mm above and 4.5mm below; its manual requires a 45mm rear chimney.
83. AXIS PRO is a metal-side drawer system. Use db/drawer_systems.yaml (GTV sheet pp.6–8): bottom 16 mm, LW−75 by NL−24; rear 16 mm, LW−87 by 84/116/167/199 mm for A/B/C/D. Purchased sides are 86/120/168/200 mm, length NL−7. NL+10 is minimum installation depth; this kitchen project uses NL600 in a 610mm-deep carcass. Derive runner, front and rear connector drilling from the selected variant/length and drawer installation datum; never use ordinary ball-bearing templates. Ø2 × 12 connector pilots are specified by GTV, Ø3 × 12 runner pilots are a project screw choice. Nominal metal envelopes remain simplified. Extra railing is recommended for fronts over 284 mm; only generate its bores from its selected template.
84. GTV ZM-INHC09H04-BE H0: cup Ø35 × 12, K=3 for nominal 16 mm overlay, centre 20.5 from edge. Cup screws: spacing45, offset9.5 towards edge; mounting plate: spacing32, setback37. Pilot Ø2.5 × 10 is a project choice. Lift-up hinges use the top panel, not side panels, with -1 mm adjustment for 15 mm overlay. Use db/hinges.yaml and validate thickness/overlay against the selected hinge. Height-based hinge count is a project rule, not a load certification.
85. Samsung Slide Hinge connectors couple two independently hinged doors. Furniture fronts still need their own hinges; this corrects the former statement that sliders replace cup hinges. Coupler positions remain preview markers until the Samsung kit template is provided. Check actual hinge-envelope clearance beside the appliance. Recommended niche714×1940×580; 18 mm fronts; refrigerator/freezer panel mass limits23/15.5 kg.
86. A lift-up flap requires hinges and suitably selected lifts. Do not fabricate gas-lift drilling from guessed positions: previous provisional holes are removed. Select force from the actual panel mass and obtain the exact mounting template before enabling machining.
87. The refrigerator ventilation route is configurable with `fridge_ventilation.openings` (default 500 × 40mm) at the plinth front, bottom, divider above the fridge, and top. Cut-list boards remain rectangular. Mark a later manual cut with 3.2 × 2mm rebates only where the rebate axis is at most 50mm from a parallel edge. Replace unreachable segments with shallow Ø3 × 2mm drill markers about every 20mm, the first and last 5mm from the segment ends. By default the plinth has two rebates and two rows of markers; each horizontal board has one rebate and two marker rows. These settings are in `fridge_ventilation.guide`. Markers do not open the airflow path; remove the marked material later. The upper cabinet has a furniture-board back following `material.thickness` and `upper_back.clearance` leaves 10mm to the vent opening. Verify airflow and grille against the refrigerator instructions before construction.
    The [Meble.pl service page](https://centrum.meble.pl/uslugi/wregowanie) states a 50mm edge-distance limit, while [another store page](https://www.meble.pl/plyty-informacje) says 40mm. Check the live order form; the limit is configurable in YAML.

88. Overlay fronts: 2mm outside side reveals, 3mm at the bottom/top of a front group, 3mm total between vertically stacked fronts, and 2mm total between paired doors. With 18mm board, overlays are 16mm on sides and 15mm on end panels. Calculate dimensions and positions together using parts/front_rules.py; distribute heights in 0.5mm increments while preserving the total. Appliance model requirements take precedence at appliance boundaries. Inset fronts retain separate parameters. This supersedes previous examples of 3mm side reveals and 3mm paired-door gaps.

89. Generate joints and machining automatically on every YAML load. Infer structural contacts from geometry; choose fasteners from joinery policy. No per-project manual hole patching. Purchased fitting templates belong in model libraries. Discuss unspecified behaviour with the user before adding a rule.
90. Reject drilling collisions with part names and bore coordinates; never move fittings or joints to hide them. The established opposed-shelf rule (screw on one face, offset dowel on the other) remains an explicit construction rule. Validation covers bores; it does not certify groove or hardware-motion collisions.
91. Kitchen handles: selected library model, drawer centres, vertical free-edge door handles (upper doors at bottom, lower freezer at top), horizontal bottom flap handle. Default offsets50 mm are configurable design choices; the closest fixing hole defines the end offset. Exact centring may yield a quarter-mm coordinate on a half-mm front.

92. Missing machining templates block all production exports (CSV, drilling sheet, DXF), while preview remains available. Record every missing operation and affected boards in DrawerModel.machining_issues; display this list to the user. No export override. Resolve the actual missing model/template, not merely the issue flag.

93. Along each connection, if neighbouring confirmats are more than 200 mm apart, add one locating dowel midway between them (rounded to the 0.5 mm grid), with matching blind bores in both panels. Keep the confirmats. Exactly 200 mm requires no extra dowel. YAML: joinery.dowel_between_confirmats_above (default 200). Run ordinary collision validation; do not move conflicting bores.

94. Join every pair of touching side cheeks from distinct cabinets with aligned Ø3 through-bores in both boards (`joinery.column_ties`). The generator detects pairs by cabinet identity and contact geometry; internal partitions of one cabinet are excluded. Place the first level 100mm above the lower panel top and the last 100mm below the upper panel underside. Distribute intermediate levels as close to 650mm apart as possible within 500–800mm, rounding to 0.5mm. Each level has two bores, 100mm from the front and 100mm from the rear of the shared area. YAML controls offsets and diameter. Reject collisions and impossible spacing; select a through-fastener and its retainer before installing appliances.
95. Select kitchen feet through `legs.model`. The current Emuca Bone 2024417 set adjusts from 98 to 140mm and has a 78 × 83mm plate with four fixing centres at 64 × 64mm (Emuca catalogue p.727). Generate four blind bores on the underside of the containing bottom panel for each foot, including separate-bottom layouts. Ø2.5 × 12mm pilots for Ø4 wood screws are a project choice, not a manufacturer drilling prescription; 18mm board retains 6mm above them. The catalogue gives 40kg per foot and 100kg tested per module; a load check is required before using this set for a filled tall cabinet. The kit includes plinth clips, but their fixing to the wooden plinth still lacks a confirmed method and remains a production-export blocker.
