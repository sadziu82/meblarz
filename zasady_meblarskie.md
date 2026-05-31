# Baza wiedzy - zasady projektowania mebli

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
17. Głębokość skrzynki = NL prowadnicy (dla szuflady wewnętrznej: SKL = NL). Wybierać największe dostępne NL nieprzekraczające `max_box_depth`. Długość prowadnicy wyznacza głębokość skrzynki, nie odwrotnie.

---

## POŁĄCZENIA SKRZYNKI SZUFLADY WEWNĘTRZNEJ

18. Połączenia skrzynki — przegląd typów:
    - Front (widoczny) ↔ boki, front ↔ dno: **kołki drewniane** (zasada 26, estetyka).
    - Dno ↔ boki, dno ↔ tył, tył ↔ boki: **konfirmaty** (powierzchnie niewidoczne).
19. **Dno ↔ Bok lewy / Bok prawy**: konfirmaty wiercone od spodu dna w kierunku +Z przez dno i w podstawę boku. Pozycje Y: wg zasady 1/4 i 3/4 głębokości boku (`box_depth − mdf`). Pozycja X: środek grubości boku.
20. **Tył ↔ Bok lewy / Bok prawy**: konfirmaty wiercone od tylnej ściany tyłu w kierunku −Y przez tył w tylną krawędź boku. Pozycje Z: wg zasady 1/4 i 3/4 wysokości boku (`side_H`). Pozycja X: środek grubości boku.
21. **Dno ↔ Tył**: konfirmaty wiercone od spodu dna w kierunku +Z przez dno w podstawę tylnej ścianki. Pozycje X: wg zasady 1/4 i 3/4 szerokości zewnętrznej (`box_W_ext`). Pozycja Y: środek głębokości tylnej ścianki.
22. **Front ↔ Bok lewy / Bok prawy**: kołki ø8mm. Otwory w tylnej ścianie frontu (w płaszczyźnie, głębokość 11mm) i w czole boku (głębokość 27mm). Pozycje Z: 1/4 i 3/4 wysokości boku (`side_H`), liczone od podstawy boku. Pozycja X: środek grubości boku.
23. **Front ↔ Dno**: **zawsze dwa kołki** ø8mm przy tym typie szuflady. Otwory w tylnej ścianie frontu (w płaszczyźnie, głębokość 11mm) i w czole dna — przednia krawędź (głębokość 27mm). Pozycje X: 1/4 i 3/4 szerokości zewnętrznej dna (`box_W_ext`). Pozycja Z: środek grubości dna.

---

## PROWADNICE

24. Zawsze pytać o model/specyfikację prowadnic — grubość i montaż są różne. Nie zakładać z góry.
25. Standardowe boczne kulkowe: ~12,5mm z każdej strony. Przy głębokich/ciężkich szufladach mogą być grubsze.
26. Dla wnęk głębszych niż **600mm** stosować prowadnice wzmocnione (np. GTV H53: luz 19,5mm, nośność 100kg, NL 300–1100mm). Standardowe prowadnice (H45 i podobne) nie są przystosowane do takich głębokości.
27. Modele prowadnic przechowywane są w `prowadnice.yaml`. W pliku YAML szuflady podawać `slides.model: <ID>` (np. `GTV-H53`) — program automatycznie dobierze NL i wymiary montażowe.
28. Luz tylny szuflady (prowadnica nie wystaje poza korpus): domyślnie **20mm**.
29. Wysokość montażu prowadnicy: spód prowadnicy na **50mm od spodu dna szuflady**. Na podstawie modelu prowadnicy (wymiar H) wyliczyć dokładną wysokość osi otworów montażowych — zarówno na skrzynce szuflady, jak i na boku korpusu.
30. Otwory montażowe prowadnic: wymiary i rozstaw wg karty produktowej modelu prowadnicy — używać danych z `prowadnice.yaml`.
31. Rozmieszczenie otworów montażowych na korpusie dopasować do typu szuflady (standard, push-to-open, soft-close itp.) — sprawdzać w dokumentacji prowadnicy, gdzie producent podaje pozycje względem frontu i tyłu szuflady.

---

## ŁĄCZENIA - ZASADY OGÓLNE

32. Każde połączenie musi mieć **co najmniej dwa punkty** mocowania (dwa konfirmaty lub dwa kołki).
33. Dobór metody łączenia:
    - Powierzchnie **niewidoczne** → konfirmaty.
    - Powierzchnie **widoczne** → kołki drewniane.
    - Powierzchnie **widoczne z potrzebą wzmocnienia** → pytać klienta (kołki + wkręty od wewnątrz, kątowniki, lamel itp.).

---

## ŁĄCZENIA - KONFIRMATY

34. Konfirmaty — zawsze pogłębienie na głowicę:
    - Otwór przelotowy: **ø5mm** lub **ø4mm**
    - Pogłębienie na głowicę: **ø11mm × 4,5mm głębokości**
    - Otwór gwintowany w drugim elemencie: **ø5mm** lub **ø4mm**, min. 35mm głębokości
35. Głębokość otworu gwintowanego = długość konfirmatu − grubość pierwszego elementu, minimum **35mm**. Dla konfirmatu 50mm i MDF 18mm = 32mm → zaokrąglamy do 35mm.
36. Rozmieszczenie konfirmatów — w **1/4 i 3/4** długości łączonej krawędzi, max 100mm od końca. Jeśli odstęp między konfirmatami > 300mm — dodać kolejne w równych odstępach.

---

## ŁĄCZENIA - KOŁKI DREWNIANE

37. Kołki drewniane: **ø8mm × 35mm** jako standard.
38. Głębokość otworów na kołki:
    - W **płaszczyźnie** elementu: **11mm**
    - W **czole** elementu: **27mm**
39. Rozmieszczenie kołków — tak samo jak konfirmaty: **1/4 i 3/4** wspólnego wymiaru łączonych elementów, max 100mm od końca.
40. Przy otworach łączących dwa elementy — pozycja 1/4 i 3/4 liczona z **wspólnego wymiaru** (krótszy z dwóch).

---

## ESTETYKA

41. Elementy widoczne (fronty, boki zewnętrzne) — **nigdy** nie mają widocznych wierceń od strony zewnętrznej. Otwory tylko od strony wewnętrznej/niewidocznej.
42. Front szuflady: otwory na kołki wyłącznie od strony skrzynki (tył frontu), wiercone w płaszczyźnie.

---

## OPENSCAD

43. Tylko **ASCII** w nazwach zmiennych i modułów. Polskie znaki tylko w komentarzach (`//`).
44. Elementy estetyczne (fronty) modelować jako **osobne moduły** — nie zagnieżdżać w module skrzynki.
45. Przed pisaniem kodu narysować przekrój — określić który element jest bazowy, które stoją na nim, które obejmują.
46. Przy otworach łączących dwa elementy na różnych wysokościach Z — liczyć pozycję we **współrzędnych globalnych** (dodać offset między elementami).
47. Kierunki rotacji cylindrów (domyślnie idą w `+Z`):
    - wiercenie w `+Y`: `rotate([-90,0,0])`
    - wiercenie w `-Y`: `rotate([90,0,0])`
    - wiercenie w `-Z`: `rotate([180,0,0])`
    - wiercenie w `+Z`: brak rotacji
48. Otwory wiercone od powierzchni w głąb — cylinder startuje na powierzchni + **0.1mm** naddatku (żeby difference działał poprawnie).
49. Dwa moduły dla otworów konfirmatów:
    - `conf_hole()` — **pierwszy element**: pogłębienie ø11mm + otwór przelotowy ø5mm
    - `conf_hole_thread()` — **drugi element**: tylko otwór gwintowany ø5mm, głębokość 35mm
50. Exploded view — każdy element odsunięty w naturalnym kierunku montażu (front w -Y, boki w ±X, tył w +Y, dno w -Z). Parametr `explode = 0/1` do przełączania.
