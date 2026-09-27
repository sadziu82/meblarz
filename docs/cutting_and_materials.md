# Rozkrój, eksport i materiały

Wszystkie polecenia uruchamiaj z katalogu repozytorium, po aktywowaniu `venv`.
Wymiary w YAML i raportach podawane są w milimetrach.

## Instalacja i wybór dostawcy

```bash
source venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

`cutting.py` zastąpił `rozkroj_meble_pl.py`, a `export.py` zastąpił
`export_meblepl.py`. Oba wymagają `--vendor meble.pl`; obecnie nie obsługują
innych dostawców. Brak tej opcji lub nieznany dostawca daje kod wyjścia 2
przed wczytaniem projektu. Biblioteka materiałów znajduje się w
[db/materials.yaml](../db/materials.yaml).

## Gotowe przykłady

| Projekt | Co pokazuje |
|---|---|
| [cutting_drawer.yaml](../examples/cutting_drawer.yaml) | Dąb EGGER H1318 ST10, automatyczne obrzeża 0,8 mm, tył nieoklejany |
| [cutting_drawer_edges.yaml](../examples/cutting_drawer_edges.yaml) | Obrzeża 2 mm, dopuszczone tylne krawędzie, jawny wyjątek `rear: []` |
| [cutting_kitchen.yaml](../examples/cutting_kitchen.yaml) | Osobne płyty 18 i 16 mm, cofnięcie półek 20 mm, klapa 75° |

To kompletne pliki, a nie fragmenty do wklejenia. Przykład kuchenny ma te same
nierozstrzygnięte mocowania ślizgaczy Samsung i klipsów cokołu co projekt bazowy.

### Plan lokalny i podgląd

```bash
python cutting.py examples/cutting_drawer.yaml --vendor meble.pl --dry-run
python cutting.py examples/cutting_kitchen.yaml --vendor meble.pl --dry-run --output-dir exports/kitchen-check
DISPLAY=:98 python viewer.py examples/cutting_drawer_edges.yaml
```

`--dry-run` tworzy plan i raport; nie łączy się ze sklepem. W podglądzie `E`
przełącza turkusowe oznaczenia oklejanych krawędzi, a `Ctrl+R` odświeża YAML.
Klawisz `E` działa również przez stdin przy uruchomieniu przez SSH.

### Formularz i wycena

```bash
DISPLAY=:98 python cutting.py examples/cutting_drawer.yaml --vendor meble.pl
DISPLAY=:98 python cutting.py examples/cutting_drawer.yaml --vendor meble.pl --no-calculate
python cutting.py examples/cutting_drawer.yaml --vendor meble.pl --headless --output-dir exports/drawer-batch
```

Pierwsze polecenie wprowadza formatki, obrzeża, obsługiwane nawierty i wręgi, a potem
przelicza koszt. Drugie pozostawia wypełniony formularz bez przeliczenia; nie
traktuj go jako zapisanego rozkroju pod trwałym adresem. Trzecie działa bez GUI.
Skrypt nie dodaje zlecenia do koszyka ani nie składa zamówienia.

### Weryfikacja

Wstaw adres własnego zapisanego rozkroju:

```bash
cut_url='https://www.meble.pl/rozkroj,r12345678'
DISPLAY=:98 python cutting.py projects/drawer.yaml --vendor meble.pl --verify "$cut_url"
```

`--verify` odczytuje formularz i porównuje go z bieżącym YAML-em: materiały,
grubości, formatki, wymiary, ilości, obrzeża, słoje, nawierty i wręgi, w tym brakujące
lub nadmiarowe. Grupy materiałowe są porównywane w kolejności planu, formatki
wewnątrz grup po nazwach. Nie poprawia danych na stronie. Różnice trafiają do
`weryfikacja.md`, a odczyt do `odczyt.json`.

### Eksport plików produkcyjnych

```bash
python export.py examples/cutting_drawer.yaml --vendor meble.pl --output-dir exports/drawer-production
```

Powstają `cutting_drawer-meblepl.csv`, `cutting_drawer-wiercenia.md` i katalog
`cutting_drawer-dxf/`. Są to lokalne pliki, bez otwierania przeglądarki.
`export.py` zatrzymuje się przed zapisem, jeśli model zgłasza niekompletną obróbkę.
Dlatego eksport produkcyjny przykładu kuchennego pozostaje zablokowany.

CSV PRO100 zapisuje kierunek słojów i liczbę obrzeży, ale nie rozróżnia,
którą z dwóch równoległych krawędzi okleić przy pojedynczym obrzeżu. Przy ręcznym
imporcie sprawdź stronę, dekor i grubość obrzeża. `cutting.py` ustawia każdą
krawędź osobno w formularzu.

## Opcje CLI

| Opcja | Skrypt | Znaczenie |
|---|---|---|
| `--vendor meble.pl` | oba | Wymagany dostawca |
| `--output-dir KATALOG` | oba | Katalog wyników; `export.py`: domyślnie `exports`; `cutting.py`: `exports/NAZWA-meblepl-DATA-CZAS` |
| `--dry-run` | cutting | Wyłącznie lokalny plan i raport |
| `--verify URL` | cutting | Odczyt i porównanie zapisanego rozkroju |
| `--no-calculate` | cutting | Wypełnienie bez wyceny |
| `--close` | cutting | Zamknięcie okna po wykonaniu pracy |
| `--headless` | cutting | Bez GUI i bez pozostawiania okna; nie wymaga DISPLAY |
| `--help` | oba | Pomoc |

Nie można łączyć `--verify` z `--dry-run`.

Po zwykłym wykonaniu `cutting.py` pozostawia przeglądarkę do kontroli.
Ctrl+C pozwala dokończyć bieżącą operację i zamknąć okno; powtórne Ctrl+C nie
przerywa sprzątania. Przerwanie pracy daje kod 130; zamknięcie okna już po
zakończonej pracy zachowuje jej wynik. Błąd formularza lub różnice dają 1,
błąd argumentów/projektu daje 2, sukces daje 0.

Paski postępu aktualizują się po każdym zapisanym nawiertcie. „Na płaszczyźnie”
oznacza szeroką powierzchnię formatki, „w czole” — wąską krawędź. W logu bez
terminala każdy krok ma osobny wiersz.

## Materiały i obrzeża w YAML

Dla zwykłego generatora sekcja jest na głównym poziomie; dla kuchni pod
`kitchen_tall_unit.material`:

```yaml
material:
  thickness: 18
  boards_by_thickness:
    18: EGGER-U999-ST19
    16: KRONOSPAN-U0164-ST9
  edge_banding:
    automatic: true
    thickness: 0.8
    band_rear_edges: false
    floor_edges: false
    boards:
      'drawer_*_front': [left, right, top, bottom]
      rear: []
```

Ten fragment pokazuje składnię wyjątków; nazwy muszą pasować do formatek
wybranego generatora. Brak dopasowania jest błędem. Wyjątek zastępuje cały
wynik automatu dla formatki; późniejszy pasujący wzorzec ma pierwszeństwo.

- `boards_by_thickness` jawnie wskazuje płytę dla każdej użytej grubości.
  Brak wyboru jest błędem; dekor nie jest zgadywany.
- `board: EGGER-H1318-ST10` jest skrótem tylko dla `material.thickness`
  (domyślnie 18 mm). Mapa `boards_by_thickness` ma pierwszeństwo.
- `edge_banding.thickness` oznacza grubość **obrzeża**, nie płyty. Wymiary
  formatki są końcowe: wpisujesz 400 mm, a meble.pl uwzględnia obrzeże przy cięciu.
  Skrypt obsługuje obrzeża 0,8 i 2 mm oraz jedną grubość na formatkę.
- `automatic` domyślnie wynosi `true`. Automat okleja odsłonięte krawędzie,
  uwzględnia styki płyt i ruchome elementy; fronty okleja dookoła.
- `band_rear_edges` zastępuje dawną nazwę `oklejaj_tyl`; domyślnie `false`.
  Wartość `true` dopuszcza odsłonięte tylne krawędzie.
- `floor_edges: false` pomija krawędzie przy podłodze. HDF do 6 mm oraz
  wizualizacje okuć są pomijane przez automat.
- `boards` ustala ręczne wyjątki, również przy `automatic: false`.
  Nazwy: `left/right` = −X/+X, `front/rear` = −Y/+Y, `bottom/top` = −Z/+Z.
  Nie wolno wskazywać szerokiej powierzchni zamiast wąskiej krawędzi.

Możliwy jest też opis materiału bez wpisu w bibliotece:

```yaml
material:
  boards_by_thickness:
    16:
      name: Kronospan U0164 ST9 Antracyt
      meble_pl:
        decor: U0164
        structure: ST9
        manufacturer: Kronospan
        product_codes:
          16: P16ST41MEB11.U0164.ST9.KRO
      texture: assets/materials/kronospan-u0164-st9.jpg
      texture_size_mm: [260, 260]
```

Ścieżka tekstury jest względem repozytorium, a jej skala służy podglądowi.
`product_codes` jest opcjonalną mapą potwierdzonych kodów według grubości.
Dla znanego kodu wybór i weryfikacja wymagają dokładnej zgodności SKU zamiast
nazwy opisowej. To obsługuje alias „0164 ST9 ... (u963)” w formularzu Kronospan.
Bez kodu sprawdzane są dekor, struktura i producent w nazwie.

## Orientacja i precyzja

Formatki poziome używają osi X/Y, fronty i plecy X/Z, boki Y/Z. Słoje biegną
wzdłuż szerokości płyt poziomych, frontów i pleców, a na bokach pionowo.
Kierunek nie zależy od tego, który wymiar jest dłuższy. Nawierty, strony A/B
oraz obrzeża są mapowane do tych samych osi. Na samym obrzeżu słoje zawsze
biegną wzdłuż krawędzi, również po łuku zaokrąglenia.

Gdy sklep oznacza materiał jako bezkierunkowy (`plyta_sloje=0`), skrypt i
weryfikacja nie wymagają nieistniejącego wyboru słojów. Tak zachowuje się
Kronospan U0164 ST9 16 mm; nie jest to ogólne pomijanie brakujących pól.

Produkcja używa rozdzielczości 0,1 mm: 80,25 zaokrągla się do 80,3 mm.
Obliczenia pośrednie zachowują precyzję, a współrzędne otworów są zaokrąglane
w lokalnym układzie płyty. Rozdzielczość nie oznacza tolerancji wykonania.

## Półki i podnośniki klapy

`shelf_front_setback: 10` na głównym poziomie YAML określa domyślne cofnięcie
półek wewnętrznych od czoła korpusu. Skraca półkę od przodu, zachowując jej tył.
Lokalne `front_setback`, potem jawna `depth`, mają pierwszeństwo przed wartością
domyślną. Przykładowo `kitchen_tall_unit.right_column.upper_cabinet.front_setback`
zmienia półki nad mikrofalą. Ustawienie 0 daje półkę zlicowaną; reguła nie dotyczy
płyt konstrukcyjnych i podpór AGD.

```yaml
shelf_front_setback: 20
kitchen_tall_unit:
  gas_lifts:
    model: GTV-PD-GNEO12-80-60
    opening_angle: 75
```

Fragment należy połączyć z pozostałą konfiguracją kuchni. `opening_angle`
obsługuje 75 i 90 stopni. Wybór zmienia położenia mocowań i nawiertów według
wariantu z `db/gas_lifts.yaml`, a także pozycję otwartej klapy w podglądzie.
Geometria metalowych mocowań AXIS PRO i podnośników jest wizualizacją;
nie tworzy dodatkowych formatek rozkroju.

## Raporty i obróbka poza formularzem

`plan.json` zawiera plan, a `raport.md` materiały, operacje, brakujące dane
oraz czynności montażowe. Zwykłe wypełnienie zapisuje również `plyta-N.csv`,
`verified-fields.json`, `wynik.txt` i `podglad.png`. Błędy zapisują `blad.txt`
i, jeśli strona pozostaje dostępna, `blad.html` oraz `blad.png`.

Dla rozkroju uzgodniono:

| Rodzaj | Wprowadzane do formularza |
|---|---|
| Konfirmat przez płaszczyznę | Ø5 mm na wylot |
| Konfirmat w czole | Ø4 × 35 mm jako pilot |
| Pogłębienie pod łeb | Pomijane, do wykonania samodzielnie |
| Zwykła prowadnica kulkowa (`slide`) | Zaznaczenie Ø3 × 3 mm |
| Mocowanie dna AXIS PRO | Podczas montażu przez otwory w metalowych bokach |

Reguła zaznaczeń `slide` nie zastępuje szablonów AXIS PRO. Inne niedostępne
średnice, głębokości, frezy i wręgi trafiają do listy osobnych operacji;
skrypt nie wybiera sam podobnego wariantu. Zaokrąglone formatki nie są obecnie
obsługiwane przez automat rozkroju. Wycena obejmuje tylko obróbkę w formularzu.

„Braki danych” oznaczają niepotwierdzone szablony, a nie liczbę otworów. W
kuchni są to ślizgacze drzwi lodówki i klipsy cokołu. Wypełnienie szkicu pozostaje
możliwe, lecz eksport produkcyjny blokuje się do ich rozstrzygnięcia.
„Operacje osobno” to znana obróbka niewprowadzana automatycznie do sklepu.
„Czynności montażowe” obejmują uzgodnione prace ręczne i nie blokują eksportu.

Po błędzie sprawdź raport i zachowane okno. Nie ma automatycznego wznowienia
od ostatniego otworu; ponowne zwykłe uruchomienie zaczyna nowy formularz.
Przed zamówieniem sprawdź wynik, także osobne prace wskazane w raporcie.

### Prywatność plików lokalnych

W `plan.json` pole `source` zapisuje ścieżkę względem repozytorium albo samą
nazwę pliku dla projektów spoza repozytorium, bez ścieżki katalogu użytkownika.
Katalog `exports/` nie jest wersjonowany: zawiera prywatne adresy rozkrojów,
kopie formularzy, zrzuty ekranu i profil przeglądarki (w tym dane sesji).
Nie publikuj go w całości. Starsze plany mogą zawierać pełne lokalne ścieżki.
Nagrania ekranu i pliki `.env` również są pomijane przez Git.

Mocowania podnośników gazowych w szkicu meble.pl są oznaczane nawiertami
Ø3 × 3 mm. Model i dokumentacja obróbki zachowują docelowe Ø2,5 × 10 mm;
dokończenie wiercenia jest czynnością ręczną zapisaną w raporcie. Początkowe
3 mm otworu pozostaje szersze (Ø3 mm). To uzgodniony znacznik, nie zmiana
szablonu producenta ani pełny otwór montażowy.

### Wręgowanie w formularzu

`cutting.py` automatycznie odczytuje wręgi z geometrii wygenerowanej z YAML-a.
Nie trzeba przepisywać listy obróbek do konfiguracji dostawcy. Obsługuje rowki
LED/przewodów, wręgi pod plecy, rowki dna i trasowanie wentylacji, o ile ich
geometria odpowiada możliwościom formularza:

- szerokości 3,2 / 4,2 / 10,2 mm (sprawdzone w formularzu 27.09.2026);
- głębokość 2–13 mm co 1 mm, mniejsza niż grubość płyty;
- odstęp **bliższej krawędzi wręgu** od krawędzi płyty 0–50 mm co 1 mm;
- co najmniej 75 mm płyty za wręgiem do przeciwnej krawędzi (granica
  wyznaczona próbami w aktywnym formularzu);
- przebieg przez całą długość albo zatrzymany z jednej/dwóch stron;
- dla wręgu nieprzelotowego długość przynajmniej 99 mm zgodnie z walidacją
  końców X1/X2 formularza;
- najwyżej jeden wręg na danej powierzchni przy tej samej krawędzi.

„Przelotowy” oznacza tutaj dojście rowka do końców formatki, a nie przebicie
jej grubości. X1/X2 są odległościami od końców: lewo/prawo dla rowka poziomego,
góra/dół dla pionowego. Strona A/B odpowiada tym samym osiom co nawierty.
Wręg na tylnej krawędzi boku jest przeliczany na obróbkę jego szerokiej
powierzchni: np. wsunięcie pleców 12 mm i grubość 3,2 mm daje rowek
szerokości 3,2 mm, głębokości 12 mm, bez odsunięcia od tylnej krawędzi.

Nieobsługiwane parametry pozostają w raporcie osobno z przyczyną i geometrią
odcinka. Skrypt nie zamienia sam frezu 10 mm na 10,2 mm ani 3 mm na 3,2 mm.
Dwa odcinki przy tej samej krawędzi wymagają zmiany projektu. Formularz może
nałożyć dodatkowe ograniczenia w zależności od innych obróbek; odrzucenie
wartości przerywa pracę, zamiast zapisywać zmienione wymiary.

W projekcie kuchennym włączono uzgodnione zaokrąglanie **odstępów znaczników
wentylacji**, zachowując szerokość frezu i jego końce:

```yaml
kitchen_tall_unit:
  fridge_ventilation:
    guide:
      width: 3.2
      depth: 2
      integer_edge_offsets: true
```

Domyślnie `integer_edge_offsets` jest wyłączone. Zmiana działa w geometrii
modelu, więc podgląd, DXF i plan rozkroju korzystają z tych samych odcinków.
Wręgi i nawierty trasujące nie usuwają środka otworu wentylacyjnego — nadal
wymaga on ręcznego wycięcia. Raport oddziela zlecane wręgi od prac ręcznych.

`--verify URL` porównuje stronę, krawędź, szerokość, głębokość, odstęp,
tryb i oba końce każdego wręgu; wykrywa także braki i nadmiarowe odcinki.
Podczas wpisywania widoczny jest osobny pasek postępu „Wręgowanie”.

W obecnej kuchni automat zleca trzy wręgi trasujące: w płycie dolnej, górnej
i przegrodzie nad lodówką. Dwa wręgi w cokole wysokości 100 mm zostają
w raporcie jako prace osobne: przy odstępie 28 mm i szerokości 3,2 mm
pozostaje 68,8 mm, mniej niż wymagane 75 mm. Nie zmieniamy samodzielnie
wysokości cokołu ani położenia otworu wentylacyjnego.
