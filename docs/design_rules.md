# Knowledge base — furniture design rules

> **Authoritative source: [reguly_projektowania.md](reguly_projektowania.md) (Polish)**
> This file is an English translation. In case of any discrepancy the Polish version takes precedence.

## MATERIALS AND DIMENSIONS

1. The client provides external dimensions — the designer calculates internal ones.
2. Default material: MDF 18mm. Cabinet backs (where used): HDF 3mm.
3. Use HDF back for cabinets with doors or shelves. For drawer cabinets — back is open.

---

## DRAWERS

### Handleless inner drawers with ball-bearing slides

4. Handleless drawers (opened by fingers) — front top gap **50mm**.
5. Drawer front recessed **1.5mm** from the carcass face.
6. Box side height = **2/3 of front height**. For very small or very large drawers — confirm with client.
7. Box bottom — MDF 18mm by default. Exception: check slide spec (some kitchen slides require 16mm).
8. Rails between drawers only between them — no extra rail at top or bottom. Exception: kitchen furniture may have an extra top rail as worktop reinforcement.
9. The drawer box has no separate inner front — the front panel serves both aesthetic and structural roles.
10. The box starts at Y = `front_inset + mdf` — the rear face of the front panel defines the start of sides and bottom. Box and front touch, they do not overlap.
11. Front side gap and bottom gap: **3mm**.
12. The bottom lies under the sides (sides stand on the bottom). Bottom has full external width `box_W_ext` and full depth `box_depth`. Bottom of the box is **2mm higher** than the bottom of the front (box does not protrude below the front).
13. External box width: `box_W_ext = niche_W − 2 × slide_clearance`.
14. Box depth: `box_depth = niche_D − (front_inset + front_thickness) − rear_clearance`. *(Note: the full front thickness including inset is subtracted because the box starts behind the front rear face — rule 10.)*
15. The box rear has full external width `box_W_ext` (same as the bottom). It sits on the bottom at the rear edge of the box.
16. Box sides have depth `box_depth − mdf` — shortened by the rear wall thickness. Sides fit between the rear face of the front and the rear wall (they do not extend past the back).
17. Box depth = slide NL (for inner drawer: SKL = NL). Select the **largest available NL** not exceeding `max_box_depth`. The slide length determines the box depth, not the other way around.
18. Box depth can be set explicitly by specifying `slides.nl` in the drawer or dresser YAML. The given NL must exist in the slide model's `available_lengths_mm` list and must not exceed `max_box_depth`. If `slides.nl` is omitted, the program automatically selects the maximum fitting NL (rule 17).

---

## INNER DRAWER BOX JOINTS

19. Box joint overview:
    - Front (visible) ↔ sides, front ↔ bottom: **wooden dowels** (rule 29, aesthetics).
    - Bottom ↔ sides, bottom ↔ rear, rear ↔ sides: **confirmats** (hidden surfaces).
20. **Bottom ↔ Left side / Right side**: confirmats drilled from below the bottom (+Z direction) through the bottom into the side base. Y positions: 1/4 and 3/4 of side depth (`box_depth − mdf`). X position: centre of side thickness.
21. **Rear ↔ Left side / Right side**: confirmats drilled from the rear face of the rear wall (−Y direction) through the rear into the back edge of the side. Z positions: 1/4 and 3/4 of side height (`side_H`). X position: centre of side thickness.
22. **Bottom ↔ Rear**: confirmats drilled from below the bottom (+Z) through the bottom into the rear wall base. X positions: 1/4 and 3/4 of external width (`box_W_ext`). Y position: centre of rear wall depth.
23. **Front ↔ Left side / Right side**: ø8mm dowels. Holes in the rear face of the front (in-plane, depth 11mm) and in the side front end (depth 27mm). Z positions: 1/4 and 3/4 of side height (`side_H`) from the side base. X position: centre of side thickness.
24. **Front ↔ Bottom**: **always two dowels** ø8mm for this drawer type. Holes in the rear face of the front (in-plane, depth 11mm) and in the bottom front end (depth 27mm). X positions: 1/4 and 3/4 of external bottom width (`box_W_ext`). Z position: centre of bottom thickness.

---

## SLIDES

25. Always ask for the slide model/spec — thickness and mounting vary. Do not assume.
26. Standard side ball-bearing: ~12.5mm per side. Deep/heavy drawers may require thicker slides.
27. For niches deeper than **600mm** use heavy-duty slides (e.g. GTV H53: 19.5mm clearance, 100kg load, NL 300–1100mm). Standard slides (H45 and similar) are not rated for those depths.
28. Slide models are stored in `db/slides.yaml`. In the drawer YAML specify `slides.model: <ID>` (e.g. `GTV-H53`) — the program selects NL and mounting dimensions automatically. Optionally `slides.nl: <NL>` forces a specific length (rule 18).
29. Rear clearance (slide must not protrude beyond carcass): default **20mm**.
30. Slide mounting height: slide bottom at **50mm from the box bottom**. From the slide model (dimension H) calculate the exact mounting hole axis height — both on the drawer box and on the carcass side.
31. Slide mounting holes: dimensions and spacing per the slide product datasheet — use data from `db/slides.yaml`.
32. Mounting hole layout on the carcass must match the drawer type (standard, push-to-open, soft-close, etc.) — check the slide documentation for positions relative to drawer front and rear.

---

## JOINTS — GENERAL RULES

33. Every joint must have **at least two fastening points** (two confirmats or two dowels).
34. Fastener selection:
    - **Hidden** surfaces → confirmats.
    - **Visible** surfaces → wooden dowels.
    - **Visible surfaces requiring reinforcement** → ask client (dowels + internal screws, brackets, lamello, etc.).

---

## JOINTS — CONFIRMATS

35. Confirmats — always countersink for the head:
    - Through hole: **ø5mm** or **ø4mm**
    - Head countersink: **ø11mm × 4.5mm deep**
    - Threaded hole in the second element: **ø5mm** or **ø4mm**, min. 35mm deep
36. Threaded hole depth = confirmat length − first element thickness, minimum **35mm**. For a 50mm confirmat in MDF 18mm = 32mm → round up to 35mm.
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

45. Visible elements (fronts, external sides) — **never** have visible holes from the outside. Holes only from the inner/hidden side.
46. Drawer front: dowel holes only from the box side (rear of front), drilled in-plane.

---

## OPENSCAD

47. **ASCII only** in variable and module names. Polish characters only in comments (`//`).
48. Aesthetic elements (fronts) must be **separate modules** — do not nest them inside the box module.
49. Before writing code draw a cross-section — identify which element is the base, which stand on it, which wrap around it.
50. For holes joining two elements at different Z heights — calculate position in **global coordinates** (add offset between elements).
51. Cylinder rotation directions (default direction is `+Z`):
    - drilling in `+Y`: `rotate([-90,0,0])`
    - drilling in `-Y`: `rotate([90,0,0])`
    - drilling in `-Z`: `rotate([180,0,0])`
    - drilling in `+Z`: no rotation
52. Holes are drilled from the surface inward — the cylinder starts at the surface + **0.1mm** overshoot (for correct `difference()` operation).
53. Two confirmat hole modules:
    - `conf_hole()` — **first element**: ø11mm countersink + ø5mm through hole
    - `conf_hole_thread()` — **second element**: ø5mm threaded hole only, depth 35mm
54. Exploded view — each element offset in its natural assembly direction (front in -Y, sides in ±X, rear in +Y, bottom in -Z). Parameter `explode = 0/1` to toggle.

---

## CARCASS

### Structure and dimensions

55. The client provides external furniture dimensions. **`carcass.height` is the total height from floor to top, including the plinth.** Top and bottom panels have full external width (`width`). Sides fit between them. Internal dimensions: `int_W = width − 2×thickness`, `int_H = (height − plinth.height) − 2×thickness`, `int_D = depth`.
56. Back of a drawer cabinet — **open** (rule 3). Do not use HDF back with drawers.
57. Cabinet type `placement` determines side visibility: `freestanding` — both sides visible; `builtin_left/right` — one side against a wall (hidden); `builtin_both` — both sides hidden.

### Carcass joints

58. **Top ↔ sides** and **bottom ↔ sides** — drilling direction depends on joint type:
    - **Dowels** (visible side): top — in-plane hole from the **bottom face** (inside cabinet); bottom — in-plane hole from the **top face** (inside cabinet). Matching end holes in the sides.
    - **Confirmats** (hidden side): top — head on the **top face** (hidden by worktop/enclosure), drilled top-down through top into side end; bottom — head on the **bottom face** (under cabinet), drilled bottom-up through bottom into side end.
59. **Rail ↔ sides** — drilling direction depends on side visibility:
    - **Dowels** (visible side): element 1 from the **inner** face of the side (hidden inside cabinet), in-plane; element 2 — rail end.
    - **Confirmats** (hidden side): element 1 from the **outer** face of the side (against the wall, hidden), drilled through side into rail end; element 2 — rail end.
60. Lower kitchen cabinet (no top, with load-bearing rails) — separate type, separate rules.

### Height distribution — drawers with rails

61. Number of rails between drawers = `count − 1`. Each rail has width `int_W` and depth per spec (default 100mm).
62. Element sequence bottom to top (per drawer): `bottom_gap` (3mm) → drawer front → `top_gap` (50mm, finger clearance) → rail (18mm) → … → last drawer front → `top_gap` → underside of top. A rail does **not** follow the top-most drawer.
63. Front height with equal distribution (`distribution: equal`): `front_H = (int_H − (count−1)×rail_thickness − count×(top_gap + bottom_gap)) / count`. Round down; add any remainder to the **lowest** drawer.
64. With custom distribution (`distribution: custom`) — the `heights` list is given **from lowest to highest** drawer. Fewer values than `count` may be given — missing drawers (highest ones) are calculated as an equal split of the remaining height. Missing values are always interpreted as `front_H`.
65. Parameter `height_mode` (only with `distribution: custom`) specifies what the given heights represent:
    - `front` (default) — front height.
    - `niche` — niche height: `front_H = h − top_gap − bottom_gap`.
    - `interior` — max contents height (= `side_H`): `front_H = ⌊3h/2⌋` (minimum front_H yielding `side_H ≥ h`).
    - Numeric aliases: `1` = `niche`, `2` = `interior`, `3` = `front`.

### LED rail groove

66. LED strip groove milled on the **bottom face** of the rail, 20mm from the front edge, 12×4mm. The groove illuminates the open drawer below.
67. The rail does not reach full carcass depth — open space remains behind it. Default depth: 100mm.

### Plinth

68. The plinth is a separate element mounted under the carcass bottom. `carcass.height` is the total furniture height **including the plinth** — carcass height without plinth = `height − plinth.height`. Parameters: `height` (default 100mm), `inset_front` (inset from front face, default 15mm), `inset_side` (inset from sides, default 15mm). `height: 0` means no plinth.
69. The plinth consists of a front board and two side boards (open back). Front board width: `width − 2×inset_side`. Side board depth: `depth − inset_front − thickness`. *(Side boards start behind the rear face of the front board.)* Joints: confirmats from the outer (bottom) face of the plinth — the plinth underside is not visible in normal use.
