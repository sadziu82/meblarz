# Knowledge base — furniture design rules

> **Authoritative source: [reguly_projektowania.md](reguly_projektowania.md) (Polish)**
> This file is an English translation. In case of any discrepancy the Polish version takes precedence.

> Explicit project/YAML settings override defaults. Rules 4–24 and 53–57 describe legacy inset drawers with 18mm bottoms; rules 63–65 cover HDF and overlay variants. These project rules do not certify structural capacity or configurator compatibility.

## MATERIALS AND DIMENSIONS

1. The client provides external dimensions — the designer calculates internal ones.
2. Default structural material: 18mm laminated furniture board (EGGER H1318 ST10 Natural Wild Oak in the current project), not HDF. Cabinet backs (where used): HDF 3mm.
3. Use HDF back for cabinets with doors or shelves. For drawer cabinets — back is open.

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
27. For niches deeper than **600mm** use heavy-duty slides (e.g. GTV H53: 19.5mm clearance, 100kg load, NL 300–1100mm). This is a project default; allowable NL and load must come from the specific datasheet, not the H45/H53 family name alone.
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

62. Use whole millimetres for board sizes and designer-controlled positions (`whole_mm`). Preserve machining and catalogue precision, such as 3.2mm grooves, 4.5mm countersinks and slide clearances. Thickness variable names do not specify material.
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
