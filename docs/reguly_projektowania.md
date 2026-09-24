# Baza wiedzy — zasady projektowania mebli

> Ustalenia konkretnego projektu/YAML mają pierwszeństwo przed wartościami domyślnymi. Reguły 4–24 i 53–57 opisują starszą szufladę wpuszczaną z dnem 18mm; warianty nakładane i HDF opisano w regułach 63–65. Są to reguły projektu, nie certyfikacja nośności ani gwarancja wykonania w konfiguratorze.

## MATERIAŁY I WYMIARY

1. Klient podaje wymiary zewnętrzne — projektant wylicza wewnętrzne.
2. Domyślny materiał konstrukcyjny: płyta meblowa laminowana 18mm (w aktualnym projekcie EGGER H1318 ST10 Dąb dziki naturalny), nie HDF. Tył szafek zwykle z HDF 3mm; górna szafka nad lodówką ma plecy z płyty meblowej (zasada 87).
3. Tył HDF stosować przy szafkach z drzwiami lub półkami, chyba że projekt określa plecy z płyty meblowej. Przy szafkach z szufladami — tył otwarty.

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
27. Przy głębokich wnękach ze zwykłymi bocznymi prowadnicami kulkowymi rozważyć prowadnice wzmocnione (np. GTV H53: luz 19,5mm, nośność 100kg, NL 300–1100mm). Tej preferencji nie stosować do wybranego systemu szuflad z metalowymi bokami, np. AXIS PRO; o dopuszczalnym NL, obciążeniu i minimalnej głębokości korpusu decyduje karta konkretnego modelu.
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

62. Wymiary formatek, pozycje elementów i współrzędne wierceń można podawać z rozdzielczością **0,5mm**. Nie wymuszać pełnych milimetrów ani przesuwać otworów z osi symetrii tylko dla uzyskania liczby całkowitej. Obliczenia pośrednie zachowują pełną precyzję; zaokrąglenie wymiarów produkcyjnych do 0,5mm wymaga sprawdzenia sum, szczelin i zgodności współpracujących otworów. Zachować parametry technologiczne i katalogowe, np. frez 3,2mm, pogłębienie 4,5mm czy luz prowadnic. `whole_mm` pozostaje opcją starszych projektów, nie zasadą ogólną. Rozdzielczość zapisu nie oznacza tolerancji wykonania ±0,5mm. Nazwy zmiennych grubości nie oznaczają gatunku materiału.

    Weryfikacja meble.pl (21.09.2026): [archiwalny BIZNES meble.pl, luty 2014](https://wydawnictwo.meble.pl/gfx/e-wydanie/biznes-meble-pl-2-2014/files/assets/common/downloads/publication.pdf) opisuje rozkrój centrum.meble.pl z dokładnością 0,1mm. Na aktualnych stronach [rozkroju](https://www.meble.pl/rozkroj) i [CNC](https://www.meble.pl/ciecie-cnc) nie znaleziono liczbowego potwierdzenia aktualnej tolerancji ani kroku wprowadzania współrzędnych wierceń. Archiwalna informacja nie jest potwierdzeniem obecnych parametrów usługi.
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

## SŁUPEK KUCHENNY I AGD

78. AGD w zabudowie modelować oddzielnie jako obrys podglądowy (`fabrication: false`) oraz jako parametry wnęki. Nie traktować gabarytu urządzenia, szerokości frontu ani wymiaru wnęki jako tej samej wartości. Przed cięciem stosować rysunek instalacyjny konkretnego wariantu urządzenia.
79. Słupek kuchenny w tym projekcie składa się z dwóch kolumn na cokole 100mm. Lewa wnęka lodówki ma oddzielną szafkę górną z frontem unoszonym do góry. Prawa kolumna zawiera kolejno: trzy szuflady, piekarnik, mikrofalę i dwudrzwiową szafkę górną bez pionowej przegrody. YAML wybiera model AGD; wymiary wnęki, frontu i pionowy układ wynikają z biblioteki danego modelu, grubości płyty oraz zadanych szczelin. Cokół używa istniejącego parametru `plinth.inset_front`: front jest obecnie cofnięty o 10mm, a boczne płyty nadal dochodzą do tylnej płaszczyzny korpusu.
80. Samsung BRB38G705DWWEF: karta produktu podaje 690 × 1935 × 550mm jako gabaryt urządzenia i zalecaną wnękę 714 × 1940 × 580mm. Wnęka nie zastępuje wymagań wentylacyjnych, punktów mocowania ani instrukcji producenta.
81. Electrolux EOE7C31Z: wnęka 590 × 560 × 550mm; urządzenie 594 × 596 × 569mm. Piekarnik pobiera 3490W i wymaga instalacji zgodnej z instrukcją producenta; dokumentacja mebla nie jest projektem elektrycznym.
82. Mikrofala EMS4253TMK: dla obecnego układu przyjęto wnękę 380 × 560 × 550mm. Sprawdzić tabliczkę i rysunek instalacyjny przed produkcją. `right_column.microwave.side_cutout` określa wycięcie przy tylnej krawędzi zewnętrznego prawego boku, za urządzeniem: obecnie 280mm wysokości i 120mm wzdłuż głębokości, pośrodku wysokości wnęki. Trzy cięte odcinki obrysu zaznaczają od strony wnętrza ślepe nawierty Ø3 × 2mm, maksymalnie cztery na odcinek; pierwszy i ostatni 5mm od narożników. Na istniejącej tylnej krawędzi płyty nawierty nie są potrzebne. Obrys w DXF nie jest ścieżką frezu; formatka pozostaje prostokątna, a materiał usuwa się ręcznie. Wycięcie nie może kolidować z urządzeniem ani innymi otworami. Przed cięciem zmierzyć gniazdo, wtyczkę i trasę przewodu.
82a. Układ przyjęty z użytkownikiem: górna płaszczyzna podpory piekarnika jest bazą Z. Front szuflady kończy się 3mm poniżej bazy; front piekarnika zaczyna się 5mm powyżej i kończy 594mm powyżej (widoczna wysokość 589mm). Szczelina wynosi 8mm. Wymagania montażowe są zapisane w bibliotece modeli wraz z odnośnikami do instrukcji i numerami stron. Projekt wybiera model; nie nadpisuje geometrii fasady, luzu pod podporą ani nachodzenia. Wnęka 590mm ustala spód przegrody na Z+590mm, a nachodzenie 4mm wynika z 594−590. Z płytą 18mm i dolnym naddatkiem mikrofali 4,5mm odstęp między urządzeniami wynosi 9,5mm. Wnęka ma wymagane 590mm, a korpus urządzenia 589mm; generator odrzuca nachodzenie zmniejszające wnękę poniżej wymaganego minimum. Mikrofala ma naddatki 3,5mm na górze i 4,5mm na dole oraz wymaga tylnego komina 45mm.
83. AXIS PRO to system z bokami metalowymi. db/drawer_systems.yaml, karta GTV s.6–8: dno16 mm, LW−75 × NL−24; tył16 mm, LW−87 × 84/116/167/199 mm dla A/B/C/D. Boki kupowane:86/120/168/200 mm, długość NL−7. NL+10 oznacza minimalną głębokość zabudowy; ten projekt kuchenny używa NL600 w korpusie o głębokości 610mm. Nawierty prowadnic i mocowań frontu/tyłu wyliczać z wariantu, NL i poziomu montażu, nigdy ze schematu zwykłej prowadnicy kulkowej. Ø2 × 12 mocowań podaje GTV; Ø3 × 12 pod prowadnice jest wyborem projektowym dla wkrętów. Profile metalowe w podglądzie są uproszczone. Przy frontach powyżej284 mm GTV zaleca dodatkowy reling; jego nawierty wymagają osobnego szablonu.
84. GTV ZM-INHC09H04-BE H0: puszka Ø35 × 12; K=3 dla nałożenia16 mm, oś20,5 mm od krawędzi. Wkręty puszki: rozstaw45 mm, przesunięcie9,5 mm ku krawędzi; prowadnik: rozstaw32 mm, odsunięcie37 mm od czoła korpusu. Nawiert Ø2,5 × 10 to wybór projektowy. Zawiasy klapy montować do górnej płyty, nie boków; regulacja−1 mm zapewnia nałożenie15 mm. Dane pobierać z db/hinges.yaml i sprawdzać grubość/nałożenie. Liczba zawiasów według wysokości jest regułą projektu, nie obliczeniem nośności.
85. Samsung Slide Hinge spina dwoje niezależnie zawieszonych drzwi. Fronty meblowe wymagają własnych zawiasów — to korekta wcześniejszego błędnego zapisu o zastąpieniu zawiasów przez ślizgi. Pozycje łączników pozostają znacznikami do czasu wprowadzenia szablonu zestawu Samsung. Sprawdzić gabaryt rzeczywistych zawiasów w luzie obok lodówki. Zalecana wnęka714×1940×580 mm, fronty18 mm, limity masy chłodziarka/zamrażarka23/15,5 kg.
86. Klapa wymaga zawiasów i odpowiednio dobranych podnośników. Nie generować otworów podnośników z orientacyjnych współrzędnych: wcześniejsze prowizoryczne nawierty usunięto. Dobrać siłę do masy frontu i wprowadzić szablon konkretnego podnośnika przed generowaniem obróbki.
87. Kanał wentylacyjny lodówki ma cztery parametryzowane poziomy (`fridge_ventilation.openings`, domyślnie 500 × 40mm): przód cokołu, płytę dolną, przegrodę nad lodówką i płytę górną. Formatki do rozkroju pozostają prostokątne. Obrys przyszłego ręcznego wycięcia trasować wręgiem 3,2 × 2mm tylko tam, gdzie oś wręgu leży nie dalej niż 50mm od równoległej krawędzi. Odcinki poza tym zasięgiem zaznaczyć płytkimi nawiertami Ø3 × 2mm, około co 20mm, z pierwszym i ostatnim 5mm od końców odcinka. Domyślnie cokół ma dwa wręgi i dwa rzędy nawiertów, a każda płyta pozioma jeden wręg i dwa rzędy nawiertów. Parametry są w `fridge_ventilation.guide`. Znaczniki nie tworzą otworu — materiał wyciąć później. Górna szafka ma plecy z płyty meblowej; ich grubość wynika z `material.thickness`, a `upper_back.clearance` pozostawia 10mm do otworu wentylacyjnego. Przebieg kanału i kratkę potwierdzić z instrukcją lodówki przed wykonaniem.
    Źródło limitu 50mm: [Centrum Meble.pl — wręgowanie](https://centrum.meble.pl/uslugi/wregowanie). [Inna strona sklepu](https://www.meble.pl/plyty-informacje) podaje 40mm; przed zamówieniem sprawdzić limit w aktywnym formularzu. W YAML-u limit jest parametrem.

88. Fronty nakładane: 2mm luzu od zewnętrznego obrysu korpusu po lewej i prawej; 3mm od skrajnej dolnej i górnej krawędzi grupy; 3mm łącznie między frontami w pionie; 2mm łącznie między podwójnymi drzwiami. Dla płyty 18mm nachodzenie wynosi 16mm na boki i 15mm na poziome płyty skrajne. Wymiary i pozycje wyliczać wspólnie (parts/front_rules.py), podziały w kroku 0,5mm, z zachowaniem sumy wysokości. Przy AGD obowiązują wymagania modelu urządzenia. Zasada dotyczy frontów nakładanych; fronty wpuszczane mają osobne parametry. Zastępuje wcześniejsze przykłady 3mm luzu bocznego oraz 3mm między drzwiami podwójnymi.

89. Połączenia i obróbkę generować automatycznie przy każdym wczytaniu YAML-a. Styki płyt rozpoznawać z geometrii, typ łącznika z polityki joinery. Nie uzupełniać ręcznie nawiertów pojedynczego projektu. Szablony okuć należą do bibliotek modeli. Nieustalone zachowanie omówić z użytkownikiem przed dodaniem reguły.
90. Kolizja nawiertów jest błędem z nazwą płyty i współrzędnymi otworów. Nie przesuwać samodzielnie okuć ani połączeń w celu ukrycia kolizji. Ustalona wcześniej reguła półek naprzeciw siebie (konfirmat i przesunięty kołek) pozostaje jawną regułą konstrukcyjną. Walidacja obejmuje nawierty, nie pełne kolizje frezów i ruchu okuć.
91. Uchwyty kuchenne: model z biblioteki; szuflady centralnie, drzwiczki pionowo przy wolnej krawędzi (górne od dołu, zamrażarka od góry), klapa poziomo na dole. Odsunięcia50 mm są parametrami projektu, nie normą; odległość od końca frontu dotyczy najbliższego otworu. Dokładne centrowanie frontu o wymiarze z połówką mm może dać współrzędną z ćwiartką mm.

92. Brak potwierdzonego szablonu obróbki blokuje cały eksport produkcyjny (CSV, dokumentację wierceń, DXF), ale pozwala na podgląd. Każdą brakującą operację i dotknięte nią elementy zapisać w DrawerModel.machining_issues i pokazać użytkownikowi. Bez przełącznika omijania blokady. Uzupełnić model/szablon, nie usuwać samej informacji o braku.

93. Wzdłuż jednego połączenia, gdy sąsiednie konfirmaty dzieli więcej niż 200 mm, dodać pośrodku kołek (na siatce 0,5 mm) i pasujące ślepe nawierty w obu płytach. Konfirmaty pozostają. Przy dokładnie 200 mm nie dodawać kołka. YAML: joinery.dowel_between_confirmats_above, domyślnie 200. Obowiązuje zwykła walidacja kolizji, bez przesuwania otworów.

94. Każdą parę stykających się boków dwóch odrębnych korpusów łączyć współosiowymi otworami Ø3 na wylot przez obie płyty (`joinery.column_ties`). Generator rozpoznaje pary po tożsamości korpusów i geometrii styku; przegród wewnątrz jednego korpusu nie wiercić tą regułą. Pierwszy poziom 100mm nad górą dolnej płyty, ostatni 100mm poniżej spodu górnej; poziomy pośrednie dobrać możliwie blisko 650mm, w zakresie 500–800mm, zaokrąglając do 0,5mm. Na każdym poziomie dwa otwory, 100mm od przodu i 100mm od tyłu wspólnej powierzchni. Odległości i średnica są parametrami YAML. Kolizja nawiertów lub niemożliwy rozstaw oznaczają błąd konfiguracji; śrubę przelotową i sposób jej zamocowania dobrać przed montażem urządzeń.
95. Nóżki kuchenne wybiera się przez `legs.model`. Obecny zestaw Emuca Bone 2024417 ma regulację 98–140mm, płytkę 78 × 83mm i cztery osie mocowania w rozstawie 64 × 64mm (katalog Emuca s.727). Dla każdej nóżki wygenerować cztery ślepe nawierty na spodzie odpowiedniej dolnej płyty, także przy osobnych dnach kolumn. Pilotaż Ø2,5 × 12mm pod wkręty do drewna Ø4 jest wyborem projektowym, nie wymiarem wiercenia zadanym przez producenta; w płycie 18mm pozostaje nad nim 6mm materiału. Katalog podaje 40kg na nóżkę i 100kg przetestowanego obciążenia modułu; przed użyciem zestawu pod wypełnionym wysokim słupkiem trzeba policzyć ciężar. Zestaw zawiera klipsy cokołowe, lecz sposób ich mocowania do drewnianego cokołu pozostaje nieustalony i nadal blokuje eksport produkcyjny.
