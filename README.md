# Meblarz

Narzędzie do parametrycznego projektowania mebli i wizualizacji 3D.

## Wymagania

```bash
# Debian/Ubuntu – sterownik OpenGL NVIDIA
sudo apt install libglx-nvidia0

# Środowisko Python
python3 -m venv venv
venv/bin/pip install PyQt6 PyOpenGL PyOpenGL_accelerate numpy PyYAML
```

## Uruchamianie

```bash
venv/bin/python viewer.py projekty/szuflada.yaml
```

## Sterowanie

| Skrót | Akcja |
|---|---|
| **Lewy przycisk myszy** | Obracanie kamery |
| **Prawy przycisk myszy** | Przesuwanie (pan, blokada osi) |
| **Kółko myszy** | Zoom |
| **Lewy klik** | Zaznaczenie elementu |
| `Shift` + strzałki | Obracanie kamery |
| Strzałki | Przesuwanie (pan) |
| `Ctrl` + `↑` / `↓` | Zoom in / out |
| `Home` | Reset widoku |
| `+` / `-` | Otwieranie / zamykanie szuflady |
| `Ctrl+O` | Wczytaj plik YAML |
| `Ctrl+R` | Przeładuj bieżący plik |
| `2×Esc` lub `Ctrl+Q` | Wyjście |

Kliknięcie w element: zaznaczony element (alpha 0.5), reszta przezroczysta (0.15),
otwory łączeniowe zaznaczonego elementu i pasujące otwory partnerów widoczne w pełni.

## Struktura projektu

```
meblarz/
├── baza/                   # bazy danych komponentów
│   └── prowadnice.yaml     # modele prowadnic kulkowych
├── docs/
│   └── reguly_projektowania.md
├── elementy/               # moduły Python – parametryczne elementy mebli
│   └── szuflada.py         # szuflada wewnętrzna bez uchwytu
├── projekty/               # pliki YAML projektów
│   └── szuflada.yaml       # przykładowa szuflada
└── viewer.py               # aplikacja 3D
```

## Dodawanie nowych elementów

1. Utwórz `elementy/<nazwa>.py` z funkcją `load_<nazwa>(path)` zwracającą `DrawerModel`
2. Utwórz `projekty/<projekt>.yaml` z wymiarami wnęki i referencją do prowadnicy
3. `venv/bin/python viewer.py projekty/<projekt>.yaml`
