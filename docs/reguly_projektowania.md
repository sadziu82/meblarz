# Baza wiedzy — zasady projektowania mebli

> Ustalenia konkretnego projektu/YAML mają pierwszeństwo przed wartościami domyślnymi. Reguły 4–24 i 53–57 opisują starszą szufladę wpuszczaną z dnem 18mm; warianty nakładane i HDF opisano w regułach 63–65. Są to reguły projektu, nie certyfikacja nośności ani gwarancja wykonania w konfiguratorze.

## MATERIAŁY I WYMIARY

1. Klient podaje wymiary zewnętrzne — projektant wylicza wewnętrzne.
2. Domyślny materiał konstrukcyjny: płyta meblowa laminowana 18mm (w aktualnym projekcie EGGER H1318 ST10 Dąb dziki naturalny), nie HDF. Tył szafek (gdzie stosowany): HDF 3mm.
3. Tył HDF stosować przy szafkach z drzwiami lub półkami. Przy szafkach z szufladami — tył otwarty.

---

## SZUFLADY

### Szuflady wewnętrzne bez uchwytów z prowadnicami kulkowymi

4. Szuflady bez uchwytów (otwierane palcami) — przerwa górna frontu **50mm**.
5. Front szuflady cofnięty o **1,5mm** względem lica korpusu.
6. Wysokość boków skrzynki szuflady = **2/3 wysokości frontu**. Przy małych i bardzo dużych szufladach — potwierdzać z klientem.
7. Dno skrzynki szuflady — domyślnie płyta meblowa 18mm; wariant HDF 3mm opisuje zasada 63. Wyjątek: sprawdzać specyfikację prowadnic (niektóre kuchenne wymagają 16mm).
8. Listwy między szufladami tylko między nimi — bez dodatkowej listwy na górze i na dole. Wyjątek: meble kuchenne mogą mieć dodatkową listwę górną jako wzmocnienie pod blat.
9. Skrzynka szuflady bez osobnego przodu — front pełni rolę estetyczną i konstrukcyjną.
10. Skrzynka szuflady zaczyna się w Y od `front_inset + board_thickness` — tylna ściana frontu wyznacza punkt startu boków i dna. Skrzynka i front stykają się, nie nachodzą.
11. Szczelina boczna i dolna frontu szuflady: **3mm**.
12. Dno szuflady leży na spodzie boków (boki stoją na dnie). Dno ma pełną szerokość zewnętrzną `box_W_ext` i pełną głębokość `box_depth`. Spód dna skrzynki jest **2mm wyżej** niż spód frontu (dno nie wystaje poniżej frontu).
13. Zewnętrzna szerokość skrzynki: `box_W_ext = szerokość_wnęki − 2 × luz_prowadnicy`.
14. Głębokość skrzynki: `box_depth = głębokość_wnęki − (front_inset + grubość_frontu) − luz_tylny`. *(Uwaga: odejmujemy pełną grubość frontu wraz z cofnięciem, bo skrzynka zaczyna się za tylną ścianą frontu — zasada 10.)*
15. Tył skrzynki szuflady ma pełną szerokość zewnętrzną `box_W_ext` (taką samą jak dno). Leży na dnie przy tylnej krawędzi skrzynki.
16. Boki skrzynki mają głębokość `box_depth − board_thickness` — skrócone o grubość tylnej ścianki. Boki mieszczą się między tylną ścianą frontu a tylną ścianką (nie wychodzą poza tył).
17. Głębokość skrzynki = NL prowadnicy (dla szuflady wewnętrznej: SKL = NL). Wybierać **największe dostępne NL** nieprzekraczające `max_box_depth`. Długość prowadnicy wyznacza głębokość skrzynki, nie odwrotnie.
18. Głębokość skrzynki można wymusić jawnie, podając `slides.nl` w YAML-u szuflady lub komody. Podane NL musi istnieć na liście `available_lengths_mm` danego modelu i mieścić się w `max_box_depth`. Jeśli `slides.nl` nie jest podane, program automatycznie dobiera maksymalne dostępne NL (zasada 17).

---

## POŁĄCZENIA SKRZYNKI SZUFLADY WEWNĘTRZNEJ

19. Połączenia skrzynki — przegląd typów:
    - Front (widoczny) ↔ boki, front ↔ dno: **kołki drewniane** (zasady 34 i 45, estetyka).
    - Dno ↔ boki, dno ↔ tył, tył ↔ boki: **konfirmaty** (powierzchnie niewidoczne).
20. **Dno ↔ Bok lewy / Bok prawy**: konfirmaty wiercone od spodu dna w kierunku +Z przez dno i w podstawę boku. Pozycje Y: wg zasady 1/4 i 3/4 głębokości boku (`box_depth − board_thickness`). Pozycja X: środek grubości boku.
21. **Tył ↔ Bok lewy / Bok prawy**: konfirmaty wiercone od tylnej ściany tyłu w kierunku −Y przez tył w tylną krawędź boku. Pozycje Z: wg zasady 1/4 i 3/4 wysokości boku (`side_H`). Pozycja X: środek grubości boku.
22. **Dno ↔ Tył**: konfirmaty wiercone od spodu dna w kierunku +Z przez dno w podstawę tylnej ścianki. Pozycje X: wg zasady 1/4 i 3/4 szerokości zewnętrznej (`box_W_ext`). Pozycja Y: środek głębokości tylnej ścianki.
23. **Front ↔ Bok lewy / Bok prawy**: kołki ø8mm. Otwory w tylnej ścianie frontu (w płaszczyźnie, głębokość 11mm) i w czole boku (głębokość 27mm). Pozycje Z: 1/4 i 3/4 wysokości boku (`side_H`), liczone od podstawy boku. Pozycja X: środek grubości boku.
24. **Front ↔ Dno**: **zawsze dwa kołki** ø8mm przy tym typie szuflady. Otwory w tylnej ścianie frontu (w płaszczyźnie, głębokość 11mm) i w czole dna — przednia krawędź (głębokość 27mm). Pozycje X: 1/4 i 3/4 szerokości zewnętrznej dna (`box_W_ext`). Pozycja Z: środek grubości dna.

---

## PROWADNICE

25. Korzystać z wybranego modelu i jego specyfikacji prowadnic. Pytać o model tylko wtedy, gdy nie został ustalony; grubość i montaż zależą od modelu.
26. Standardowe boczne kulkowe: ~12,5mm z każdej strony. Przy głębokich/ciężkich szufladach mogą być grubsze.
27. Dla wnęk głębszych niż **600mm** stosować prowadnice wzmocnione (np. GTV H53: luz 19,5mm, nośność 100kg, NL 300–1100mm). To domyślna preferencja projektu; dopuszczalne NL i obciążenie zawsze wynikają z konkretnej karty, nie z samej nazwy H45/H53.
28. Modele prowadnic przechowywane są w `db/slides.yaml`. W pliku YAML szuflady podawać `slides.model: <ID>` (np. `GTV-H53`) — program automatycznie dobierze NL i wymiary montażowe. Opcjonalnie `slides.nl: <NL>` wymusza konkretną długość (zasada 18).
29. Luz tylny szuflady (prowadnica nie wystaje poza korpus): domyślnie **20mm**.
30. Wysokość montażu prowadnicy: spód prowadnicy na **50mm od spodu dna szuflady**. Na podstawie modelu prowadnicy (wymiar H) wyliczyć dokładną wysokość osi otworów montażowych — zarówno na skrzynce szuflady, jak i na boku korpusu.
31. Otwory montażowe prowadnic: wymiary i rozstaw wg karty produktowej modelu prowadnicy — używać danych z `db/slides.yaml`.
32. Rozmieszczenie otworów montażowych na korpusie dopasować do typu szuflady (standard, push-to-open, soft-close itp.) — sprawdzać w dokumentacji prowadnicy, gdzie producent podaje pozycje względem frontu i tyłu szuflady.

---

## ŁĄCZENIA — ZASADY OGÓLNE

33. Standardowe połączenie ma **co najmniej dwa punkty** mocowania. Dopuszczalne są połączenia mieszane; dodatkowy pojedynczy konfirmat nadbudówki uzupełnia dwa kołki (zasada 74). Krótkie krawędzie poniżej 40mm mają w obecnym generatorze jeden punkt — to wyjątek geometryczny, nie potwierdzenie nośności.
34. Dobór metody łączenia:
    - Powierzchnie **niewidoczne** → konfirmaty.
    - Powierzchnie **widoczne** → kołki drewniane.
    - Powierzchnie **widoczne z potrzebą wzmocnienia** → pytać klienta (kołki + wkręty od wewnątrz, kątowniki, lamel itp.).

---

## ŁĄCZENIA — KONFIRMATY

35. Konfirmaty — pogłębienie na głowicę; poniższe wymiary są założeniami obecnego modelu i wymagają zgodności z zakupionym konfirmatem oraz narzędziem:
    - Otwór przelotowy: **ø5mm** lub **ø4mm**
    - Pogłębienie na głowicę: **ø11mm × 4,5mm głębokości**
    - Otwór gwintowany w drugim elemencie: **ø5mm** lub **ø4mm**, min. 35mm głębokości
36. Głębokość otworu gwintowanego = długość konfirmatu − grubość pierwszego elementu, minimum **35mm**. Dla konfirmatu 50mm i płyty 18mm = 32mm → zaokrąglamy do 35mm.
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

45. Na widocznych powierzchniach nie umieszczać odkrytych otworów konstrukcyjnych. Otwory przelotowe pod uchwyty są wyjątkiem — zasłania je okucie. Kołki wiercić od strony wewnętrznej/niewidocznej.
46. Front szuflady: otwory na kołki wyłącznie od strony skrzynki (tył frontu), wiercone w płaszczyźnie.

---

## KORPUS SZAFKI

### Konstrukcja i wymiary

47. Klient podaje wymiary zewnętrzne mebla. **`carcass.height` to całkowita wysokość od podłogi do wierzchu, wliczając cokoł.** Wierzch i spód mają pełną szerokość zewnętrzną (`width`). Boki mieszczą się między nimi. Wymiary wewnętrzne: `int_W = width − 2×thickness`, `int_H = (height − plinth.height) − 2×thickness`, `int_D = depth`.
48. Tył szafki z szufladami — **otwarty** (zasada 3). Nie stosować pleców HDF za szufladami; nie dotyczy to den HDF.
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

58. Rowek LED na spodzie poprzeczki oświetla szufladę poniżej. W starszym generatorze komody występuje 12×4mm; aktualny projekt biurka ma 10×4mm i 20mm prześwitu od przedniej krawędzi. Wymiary i sposób mierzenia odsunięcia określa zasada 68.
59. Poprzeczka nie sięga pełnej głębokości korpusu — za nią pozostaje wolna przestrzeń. Głębokość domyślna: 100mm.

### Cokoł

60. Cokoł jest osobnym elementem montowanym pod spodem korpusu. `carcass.height` to całkowita wysokość mebla **wliczając cokoł** — wysokość korpusu bez cokołu = `height − plinth.height`. Parametry: `height` (domyślnie 100mm), `inset_front` (wcięcie od lica frontu, domyślnie 15mm), `inset_side` (wcięcie od boków, domyślnie 15mm). Wartość `height: 0` oznacza brak cokołu.
61. Cokoł składa się z deski przedniej i dwóch desek bocznych (tył otwarty). Szerokość deski przedniej: `width − 2×inset_side`. Głębokość desek bocznych: `depth − inset_front − thickness`. *(Deski boczne zaczynają się za tylną ścianą deski przedniej.)* Połączenia: konfirmaty od zewnętrznej (dolnej) ściany cokołu — powierzchnia cokołu jest niewidoczna przy normalnym użytkowaniu.


## HDF, OBRÓBKA I AKTUALNY PROJEKT BIURKA

62. Wymiary formatek i ustalane przez projektanta pozycje podawać w pełnych milimetrach (`whole_mm`). Nie zaokrąglać wymiarów technologicznych i katalogowych: frezu 3,2mm, pogłębienia 4,5mm czy luzu prowadnic. Nazwy zmiennych grubości nie oznaczają gatunku materiału.
63. Dno szuflady wybierać jawnie: `drawers.bottom.type: hdf_3` albo `board_18`. `mdf_3` to wyłącznie dawny alias zgodności. HDF 3mm leży pod bokami i tyłem; mocować go małymi wkrętami od spodu. W projekcie: wkręty 3×16mm, otwory dna Ø3 na wylot i pilotaż Ø2×13mm w bokach/tyle. To założenie do dobrania wkrętów, nie wymaganie producenta. Dna HDF nie mocować za pomocą kołków Ø8 ani konfirmatów.
64. Dno HDF wchodzi we frez tylnej powierzchni frontu: 3mm głębokości i 3mm wysokości w aktualnym modelu; sprawdzić rzeczywistą grubość materiału i dostępność narzędzia przed produkcją. Dno ma przez to 303mm przy skrzynce NL=300mm. Frez 3,2mm pod plecy jest inną obróbką; nie zmienia automatycznie frezu dna.
65. Fronty nakładane liczyć osobno od wpuszczanych. W projekcie pięć frontów 594×164mm, przerwy 3mm, zakład dolny 2mm i górny 3mm. Równe wysokości uzyskano zmianą dolnej krawędzi, a nie nierównym frontem. Otwory uchwytów centralnie w pionie i poziomie, przelotowe; Ø3mm jest uzgodnionym założeniem użytkownika, rozstaw 256mm pochodzi z wybranego uchwytu.
66. Plecy: biały HDF 3mm, bez pleców za szufladami. Wręg ma 3,2mm w kierunku grubości pleców; wsunięcie w krawędź podpory 12mm na brzegu zewnętrznym, 6mm na brzegu wspólnym. Dwa plecy przy płycie 18mm pozostawiają 6mm odstępu. W metadanych `rabbet.depth` oznacza 3,2mm, a `width` wsunięcie 6/12mm — nie zamieniać nazw z opisem narzędzia w konfiguratorze.
67. Na danej powierzchni przy tej samej krawędzi wręg musi być **jednym ciągłym prostokątnym odcinkiem**: nie rozdzielać go na fragmenty nad poszczególnymi komorami. Ujednolicić przekrój przed połączeniem; na górnym tylnym brzegu płyty łączącej jest 6mm wsunięcia na całej długości. Plecy nad biurkiem mają przez to 760mm wysokości. Inna krawędź lub przeciwna powierzchnia może mieć własny wręg.
68. Frezy LED w projekcie: 10×4mm od spodu. Przy szufladach bliższa krawędź frezu jest 20mm od czoła; przy półkach 50mm. Parametr `offset` wskazuje oś frezu, więc wynosi odpowiednio 25 i 55mm. Blat ma własny `offset: 30`. Pod półką klawiatury nie ma frezu LED. Podświetlenie obejmuje także płytę nad ostatnią szufladą i górną płytę nadbudówki.
69. Zakończenia LED: półki między bokami i mała półka — na całą szerokość; płyta łącząca — od lewej krawędzi do 15mm przed prawą; górna płyta — od lewej do 18mm przed prawą. Blat — od lewej krawędzi z 20mm zapasu przy prawym zaokrągleniu. `end_margin_left/right` nadpisują wspólne `end_margin`. Jeden ciągły frez może przechodzić nad przegrodami; taśma i profil nie muszą być jednym elementem.
70. Do frezu LED dodawać powierzchniowy rowek przewodu 3,2×3mm od tyłu, na tej samej powierzchni. `wire_groove.side` wybiera lewo/prawo; `edge_offset` to odległość bliższej krawędzi rowka od boku. W blacie 10mm, na płycie łączącej i górnej 0mm. Przy zatrzymanym frezie domyślny rowek dochodzi do jego końca. Nie stosować w tym projekcie długiego wiercenia wewnątrz płyty ani dawnych nawiertów startowych. Dobór przekroju przewodu uwzględnia izolację i zasilanie LED.
71. Konfigurator meble.pl według danych podanych przez użytkownika: szerokości wręgów 3,2/4,3/10,2mm, głębokości 2–13mm co 1mm, odsunięcie 0–50mm. Obecne frezy LED 10mm oraz dna 3mm wymagają potwierdzenia wykonania CNC lub jawnej zmiany projektu; nie traktować eksportu DXF jako potwierdzenia dostępności standardowej usługi.
72. Typ połączenia dobierać według **widoczności łba i dostępu narzędzia**. `joinery.hidden_faces` wskazuje powierzchnie łbów konfirmatów; pozostałe połączenia pozostają kołkowe. `keep_dowels` zachowuje wskazane pary na kołkach. Przy konfirmacie otwór przelotowy i pogłębienie zaczynają się na zewnętrznej powierzchni pierwszej płyty, pilotaż na powierzchni styku drugiej.
73. Przy półkach po dwóch stronach wspólnej przegrody stosować z jednej strony konfirmaty, a z drugiej kołki, które nie przecinają ich otworów. `mixed_shared_sides` obsługuje przeciwległe połączenia półek na tej samej wysokości; pozycje kołków przesuwa co najmniej o 20mm w głąb. Najpierw skręcić pierwszą półkę, potem osadzić drugą zasłaniającą łby. To nie jest ogólny wykrywacz wszystkich kolizji modelu.
74. Nadbudówka: kołki ustalające od dołu, konfirmaty od góry. Pod dwiema wewnętrznymi przegrodami dopuszczone są dodatkowe konfirmaty od spodu płyty łączącej, 30mm od tyłu, ukryte za wspornikiem (`overhead.rear_confirmats`). Każdy uzupełnia dwa kołki. Pod bocznymi płytami dolny korpus zasłania dostęp, więc pozostają kołki. Blat jest mocowany dwoma konfirmatami do każdego boku; po prawej łby zakrywa półka nad szufladami na przesuniętych kołkach.
75. Dane prowadnic i uchwytów przechowywać w bibliotekach; nie utożsamiać NL z wysuwem. W projekcie szuflady: GTV kulkowe z domykiem 300mm; klawiatura: 400mm, początek prowadnic 70mm za czołem półki. Prześwit pod blatem 100mm, półka 1000×500mm cofnięta 30mm. Nie przenosić otworów lub dopuszczalnego obciążenia między modelami bez specyfikacji.
76. Dokumentacja produkcyjna musi podawać materiał, stronę obróbki, wymiary i zakres frezu oraz rodzaj/średnicę/głębokość/przelotowość nawiertu. Sprzęt podglądowy i próbne mocowanie monitora nie wchodzą do rozkroju. CSV nie określa jeszcze obrzeży ani kierunku słojów — uzupełnić je przed wyceną. Kosztorys orientacyjny odróżnia ceny materiałów od rezerw na usługi; nie jest ofertą wykonawcy.

77. Sterowanie LED bez wybranych modeli oznaczać tylko znacznikami podglądu (`lighting_controls.preview`). Krańcówki szuflad są nieruchome, z tyłu nad prowadnicą; docelowo zamknięcie wyłącza, otwarcie włącza światło. Inne paski mają orientacyjne miejsca czujników gestu dłoni. Pomarańczowe/niebieskie znaczniki 6mm nie są gabarytami urządzeń ani potwierdzeniem miejsca montażu; nie generują nawiertów, nie trafiają do rozkroju i nie symulują działania LED. Modele, mocowania, skok krańcówki, napięcie/prąd oraz grupowanie oświetlenia ustalić przed wykonaniem obróbek.
