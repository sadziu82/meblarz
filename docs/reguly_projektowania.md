# Baza wiedzy — zasady projektowania mebli

## MATERIAŁY I WYMIARY

1. Klient podaje wymiary zewnętrzne — projektant wylicza wewnętrzne.
2. Domyślny materiał: MDF 18mm. Tył szafek (gdzie stosowany): HDF 3mm.
3. Tył HDF stosować przy szafkach z drzwiami lub półkami. Przy szafkach z szufladami — tył otwarty.

---

## SZUFLADY

### Szuflady wewnętrzne bez uchwytów z prowadnicami kulkowymi

4. Szuflady bez uchwytów (otwierane palcami) — przerwa górna frontu **50mm**.
5. Front szuflady cofnięty o **1,5mm** względem lica korpusu.
6. Wysokość boków skrzynki szuflady = **2/3 wysokości frontu**. Przy małych i bardzo dużych szufladach — potwierdzać z klientem.
7. Dno skrzynki szuflady — domyślnie MDF 18mm. Wyjątek: sprawdzać specyfikację prowadnic (niektóre kuchenne wymagają 16mm).
8. Listwy między szufladami tylko między nimi — bez dodatkowej listwy na górze i na dole. Wyjątek: meble kuchenne mogą mieć dodatkową listwę górną jako wzmocnienie pod blat.
9. Skrzynka szuflady bez osobnego przodu — front pełni rolę estetyczną i konstrukcyjną.
10. Skrzynka szuflady zaczyna się w Y od `front_inset + mdf` — tylna ściana frontu wyznacza punkt startu boków i dna. Skrzynka i front stykają się, nie nachodzą.
11. Szczelina boczna i dolna frontu szuflady: **3mm**.
12. Dno szuflady leży na spodzie boków (boki stoją na dnie). Dno ma pełną szerokość zewnętrzną `box_W_ext` i pełną głębokość `box_depth`. Spód dna skrzynki jest **2mm wyżej** niż spód frontu (dno nie wystaje poniżej frontu).
13. Zewnętrzna szerokość skrzynki: `box_W_ext = szerokość_wnęki − 2 × luz_prowadnicy`.
14. Głębokość skrzynki: `box_depth = głębokość_wnęki − (front_inset + grubość_frontu) − luz_tylny`. *(Uwaga: odejmujemy pełną grubość frontu wraz z cofnięciem, bo skrzynka zaczyna się za tylną ścianą frontu — zasada 10.)*
15. Tył skrzynki szuflady ma pełną szerokość zewnętrzną `box_W_ext` (taką samą jak dno). Leży na dnie przy tylnej krawędzi skrzynki.
16. Boki skrzynki mają głębokość `box_depth − mdf` — skrócone o grubość tylnej ścianki. Boki mieszczą się między tylną ścianą frontu a tylną ścianką (nie wychodzą poza tył).
17. Głębokość skrzynki = NL prowadnicy (dla szuflady wewnętrznej: SKL = NL). Wybierać **największe dostępne NL** nieprzekraczające `max_box_depth`. Długość prowadnicy wyznacza głębokość skrzynki, nie odwrotnie.
18. Głębokość skrzynki można wymusić jawnie, podając `slides.nl` w YAML-u szuflady lub komody. Podane NL musi istnieć na liście `available_lengths_mm` danego modelu i mieścić się w `max_box_depth`. Jeśli `slides.nl` nie jest podane, program automatycznie dobiera maksymalne dostępne NL (zasada 17).

---

## POŁĄCZENIA SKRZYNKI SZUFLADY WEWNĘTRZNEJ

19. Połączenia skrzynki — przegląd typów:
    - Front (widoczny) ↔ boki, front ↔ dno: **kołki drewniane** (zasada 29, estetyka).
    - Dno ↔ boki, dno ↔ tył, tył ↔ boki: **konfirmaty** (powierzchnie niewidoczne).
20. **Dno ↔ Bok lewy / Bok prawy**: konfirmaty wiercone od spodu dna w kierunku +Z przez dno i w podstawę boku. Pozycje Y: wg zasady 1/4 i 3/4 głębokości boku (`box_depth − mdf`). Pozycja X: środek grubości boku.
21. **Tył ↔ Bok lewy / Bok prawy**: konfirmaty wiercone od tylnej ściany tyłu w kierunku −Y przez tył w tylną krawędź boku. Pozycje Z: wg zasady 1/4 i 3/4 wysokości boku (`side_H`). Pozycja X: środek grubości boku.
22. **Dno ↔ Tył**: konfirmaty wiercone od spodu dna w kierunku +Z przez dno w podstawę tylnej ścianki. Pozycje X: wg zasady 1/4 i 3/4 szerokości zewnętrznej (`box_W_ext`). Pozycja Y: środek głębokości tylnej ścianki.
23. **Front ↔ Bok lewy / Bok prawy**: kołki ø8mm. Otwory w tylnej ścianie frontu (w płaszczyźnie, głębokość 11mm) i w czole boku (głębokość 27mm). Pozycje Z: 1/4 i 3/4 wysokości boku (`side_H`), liczone od podstawy boku. Pozycja X: środek grubości boku.
24. **Front ↔ Dno**: **zawsze dwa kołki** ø8mm przy tym typie szuflady. Otwory w tylnej ścianie frontu (w płaszczyźnie, głębokość 11mm) i w czole dna — przednia krawędź (głębokość 27mm). Pozycje X: 1/4 i 3/4 szerokości zewnętrznej dna (`box_W_ext`). Pozycja Z: środek grubości dna.

---

## PROWADNICE

25. Zawsze pytać o model/specyfikację prowadnic — grubość i montaż są różne. Nie zakładać z góry.
26. Standardowe boczne kulkowe: ~12,5mm z każdej strony. Przy głębokich/ciężkich szufladach mogą być grubsze.
27. Dla wnęk głębszych niż **600mm** stosować prowadnice wzmocnione (np. GTV H53: luz 19,5mm, nośność 100kg, NL 300–1100mm). Standardowe prowadnice (H45 i podobne) nie są przystosowane do takich głębokości.
28. Modele prowadnic przechowywane są w `db/slides.yaml`. W pliku YAML szuflady podawać `slides.model: <ID>` (np. `GTV-H53`) — program automatycznie dobierze NL i wymiary montażowe. Opcjonalnie `slides.nl: <NL>` wymusza konkretną długość (zasada 18).
29. Luz tylny szuflady (prowadnica nie wystaje poza korpus): domyślnie **20mm**.
30. Wysokość montażu prowadnicy: spód prowadnicy na **50mm od spodu dna szuflady**. Na podstawie modelu prowadnicy (wymiar H) wyliczyć dokładną wysokość osi otworów montażowych — zarówno na skrzynce szuflady, jak i na boku korpusu.
31. Otwory montażowe prowadnic: wymiary i rozstaw wg karty produktowej modelu prowadnicy — używać danych z `db/slides.yaml`.
32. Rozmieszczenie otworów montażowych na korpusie dopasować do typu szuflady (standard, push-to-open, soft-close itp.) — sprawdzać w dokumentacji prowadnicy, gdzie producent podaje pozycje względem frontu i tyłu szuflady.

---

## ŁĄCZENIA — ZASADY OGÓLNE

33. Każde połączenie musi mieć **co najmniej dwa punkty** mocowania (dwa konfirmaty lub dwa kołki).
34. Dobór metody łączenia:
    - Powierzchnie **niewidoczne** → konfirmaty.
    - Powierzchnie **widoczne** → kołki drewniane.
    - Powierzchnie **widoczne z potrzebą wzmocnienia** → pytać klienta (kołki + wkręty od wewnątrz, kątowniki, lamel itp.).

---

## ŁĄCZENIA — KONFIRMATY

35. Konfirmaty — zawsze pogłębienie na głowicę:
    - Otwór przelotowy: **ø5mm** lub **ø4mm**
    - Pogłębienie na głowicę: **ø11mm × 4,5mm głębokości**
    - Otwór gwintowany w drugim elemencie: **ø5mm** lub **ø4mm**, min. 35mm głębokości
36. Głębokość otworu gwintowanego = długość konfirmatu − grubość pierwszego elementu, minimum **35mm**. Dla konfirmatu 50mm i MDF 18mm = 32mm → zaokrąglamy do 35mm.
37. Rozmieszczenie konfirmatów — w **1/4 i 3/4** długości łączonej krawędzi, max 100mm od końca. Jeśli odstęp między konfirmatami > 300mm — dodać kolejne w równych odstępach.

---

## ŁĄCZENIA — KOŁKI DREWNIANE

38. Kołki drewniane: **ø8mm × 35mm** jako standard.
39. Głębokość otworów na kołki:
    - W **płaszczyźnie** elementu: **11mm**
    - W **czole** elementu: **27mm**
40. Rozmieszczenie kołków — tak samo jak konfirmaty: **1/4 i 3/4** wspólnego wymiaru łączonych elementów, max 100mm od końca.
41. Przy otworach łączących dwa elementy — pozycja 1/4 i 3/4 liczona z **wspólnego wymiaru** (krótszy z dwóch).

---

## LOKALNY UKŁAD WSPÓŁRZĘDNYCH PŁYTY

42. Pozycje otworów zawsze podawane w **lokalnym układzie współrzędnych** płyty, niezależnie od orientacji elementu w meblu:
    - **x** — oś pozioma (wzdłuż szerokości płyty)
    - **y** — oś pionowa (wzdłuż wysokości płyty)
    - **głębokość** — zawsze grubość płyty; nie wpływa na położenie otworu w płaszczyźnie i nie jest podawana jako osobna współrzędna pozycji
43. Otwory **w czole** (kołki, gwint konfirmatu wchodzący od czoła) leżą zawsze na środku grubości płyty. Pozycja podawana wyłącznie jako (x, y).
44. Otwór w płaszczyźnie — pozycja jako (x, y) od lewego dolnego narożnika widocznej twarzy płyty.

---

## ESTETYKA

45. Elementy widoczne (fronty, boki zewnętrzne) — **nigdy** nie mają widocznych wierceń od strony zewnętrznej. Otwory tylko od strony wewnętrznej/niewidocznej.
46. Front szuflady: otwory na kołki wyłącznie od strony skrzynki (tył frontu), wiercone w płaszczyźnie.

---

## KORPUS SZAFKI

### Konstrukcja i wymiary

47. Klient podaje wymiary zewnętrzne mebla. **`carcass.height` to całkowita wysokość od podłogi do wierzchu, wliczając cokoł.** Wierzch i spód mają pełną szerokość zewnętrzną (`width`). Boki mieszczą się między nimi. Wymiary wewnętrzne: `int_W = width − 2×thickness`, `int_H = (height − plinth.height) − 2×thickness`, `int_D = depth`.
48. Tył szafki z szufladami — **otwarty** (zasada 3). Nie stosować HDF przy szufladach.
49. Typ szafki `placement` określa widoczność boków: `freestanding` — oba boki widoczne; `builtin_left/right` — jeden bok przy ścianie (niewidoczny); `builtin_both` — oba niewidoczne.

### Połączenia korpusu

50. Połączenia **wierzch ↔ boki** i **spód ↔ boki** — kierunek wiercenia zależy od typu połączenia:
    - **Kołki** (bok widoczny): wierzch — otwór w płaszczyźnie od **spodniej ściany** (wewnątrz szafki); spód — otwór w płaszczyźnie od **górnej ściany** (wewnątrz szafki). Otwory w czołach boków naprzeciw.
    - **Konfirmaty** (bok niewidoczny): wierzch — głowica na **górnej ścianie** (przykryta blatem/zabudową), wiercenie z góry w dół przez wierzch w czoło boku; spód — głowica na **dolnej ścianie** (pod szafką), wiercenie z dołu w górę przez spód w czoło boku.
51. Połączenia **poprzeczki ↔ boki** — kierunek wiercenia zależy od widoczności boku:
    - **Kołki** (bok widoczny): element 1 od **wewnętrznej** ściany boku (ukryta wewnątrz szafki), otwór w płaszczyźnie; element 2 — czoło poprzeczki.
    - **Konfirmaty** (bok niewidoczny): element 1 od **zewnętrznej** ściany boku (przy ścianie budynku, niewidoczna), wiercenie przez bok w czoło poprzeczki; element 2 — czoło poprzeczki.
52. Szafka kuchenna dolna (bez wierzchu, z poprzeczkami nośnymi) — osobny typ, osobne zasady.

### Podział wysokości — szuflady z poprzeczkami

53. Liczba poprzeczek między szufladami = `count − 1`. Każda poprzeczka ma szerokość `int_W` i głębokość wg specyfikacji (domyślnie 100mm).
54. Sekwencja elementów od spodu do góry (dla każdej szuflady): `bottom_gap` (3mm) → front szuflady → `top_gap` (50mm, przerwa na palce) → poprzeczka (18mm) → … → front ostatniej szuflady → `top_gap` → spód wierzchu. Poprzeczka **nie** występuje po ostatniej (najwyższej) szufladzie.
55. Wysokość frontu przy równym podziale (`distribution: equal`): `front_H = (int_H − (count−1)×rail_thickness − count×(top_gap + bottom_gap)) / count`. Wynik zaokrąglić w dół; nadmiarowe mm dodać do **najniższej** szuflady.
56. Przy podziale niestandardowym (`distribution: custom`) — lista `heights` podana **od najniższej do najwyższej** szuflady. Można podać mniej wartości niż `count` — brakujące szuflady (najwyższe) wyliczane są jako równy podział pozostałej wysokości. Brakujące zawsze interpretowane jako `front_H`.
57. Parametr `height_mode` (tylko przy `distribution: custom`) określa co oznaczają podane wysokości:
    - `front` (domyślnie) — wysokość frontu szuflady.
    - `niche` — wysokość wnęki: `front_H = h − top_gap − bottom_gap`.
    - `interior` — maksymalna wysokość zawartości (= `side_H`): `front_H = ⌊3h/2⌋` (minimalne front_H dające `side_H ≥ h`).
    - Aliasy numeryczne: `1` = `niche`, `2` = `interior`, `3` = `front`.

### Poprzeczka z rowkiem LED

58. Rowek na taśmę LED frezowany na **spodniej ścianie** poprzeczki, 20mm od przedniej krawędzi, wymiary 12×4mm. Rowek oświetla otwartą szufladę poniżej.
59. Poprzeczka nie sięga pełnej głębokości korpusu — za nią pozostaje wolna przestrzeń. Głębokość domyślna: 100mm.

### Cokoł

60. Cokoł jest osobnym elementem montowanym pod spodem korpusu. `carcass.height` to całkowita wysokość mebla **wliczając cokoł** — wysokość korpusu bez cokołu = `height − plinth.height`. Parametry: `height` (domyślnie 100mm), `inset_front` (wcięcie od lica frontu, domyślnie 15mm), `inset_side` (wcięcie od boków, domyślnie 15mm). Wartość `height: 0` oznacza brak cokołu.
61. Cokoł składa się z deski przedniej i dwóch desek bocznych (tył otwarty). Szerokość deski przedniej: `width − 2×inset_side`. Głębokość desek bocznych: `depth − inset_front − thickness`. *(Deski boczne zaczynają się za tylną ścianą deski przedniej.)* Połączenia: konfirmaty od zewnętrznej (dolnej) ściany cokołu — powierzchnia cokołu jest niewidoczna przy normalnym użytkowaniu.
