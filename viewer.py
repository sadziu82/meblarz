#!/usr/bin/env python3
"""
Meblarz Viewer – oglądarka modeli mebli w PyQt6 + PyOpenGL.
Wymaga: libglx-nvidia0 (sudo apt install libglx-nvidia0)
Uruchamiać z venv projektu: ./run.sh
"""

import sys
import math
from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSlider, QLabel, QPushButton, QFileDialog, QGroupBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QSurfaceFormat

from OpenGL.GL import *
from OpenGL.GLU import *

from elementy.szuflada import DrawerModel, Board, Hole, JointHole, load_drawer


def _ray_aabb(ro, rd, bmin, bmax):
    """Ray – AABB intersection. Zwraca t (odległość) lub None."""
    tmin, tmax = -np.inf, np.inf
    for i in range(3):
        if abs(rd[i]) < 1e-9:
            if ro[i] < bmin[i] or ro[i] > bmax[i]:
                return None
        else:
            t1 = (bmin[i] - ro[i]) / rd[i]
            t2 = (bmax[i] - ro[i]) / rd[i]
            if t1 > t2:
                t1, t2 = t2, t1
            tmin = max(tmin, t1)
            tmax = min(tmax, t2)
    if tmax < tmin or tmax < 0:
        return None
    return tmin if tmin >= 0 else tmax


# ── OpenGL widget ──────────────────────────────────────────────────────────────

class GLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: DrawerModel | None = None

        self.rot_x = 25.0
        self.rot_y = -35.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_z = 0.0

        self._last_pos = None
        self._press_pos = None
        self._pan_axis: str | None = None   # 'x' | 'z', blokada osi podczas pan
        self._open = 0.0
        self._scene_size = 500.0
        self._selected: int | None = None   # indeks wybranej deski
        self._mv_mat = None                 # zapisana macierz dla pickingu
        self._proj_mat = None
        self._viewport = None

    def set_open(self, value: float):
        self._open = value
        self.update()

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_NORMALIZE)

        glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 2.0, 3.0, 0.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [0.85, 0.85, 0.80, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.30, 0.30, 0.30, 1.0])

        glClearColor(0.18, 0.18, 0.22, 1.0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, max(h, 1))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / max(h, 1), 1.0, 10000.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        dist = self._scene_size * 2.5 / self.zoom
        gluLookAt(self.pan_x, -dist, dist * 0.6 + self.pan_z,
                  self.pan_x,     0,             self.pan_z,
                  0, 0, 1)

        glRotatef(self.rot_x, 1, 0, 0)
        glRotatef(self.rot_y, 0, 0, 1)

        # Zapisz macierze po ustawieniu widoku – używane do ray pickingu
        self._mv_mat   = glGetDoublev(GL_MODELVIEW_MATRIX)
        self._proj_mat = glGetDoublev(GL_PROJECTION_MATRIX)
        self._viewport = glGetIntegerv(GL_VIEWPORT)

        if self.model:
            self._draw_model()
        else:
            self._draw_placeholder()

    def _draw_model(self):
        travel = self.model.max_travel * self._open
        sel = self._selected
        boards = self.model.boards
        sel_name = boards[sel].name if sel is not None else None

        def draw_body(board, alpha):
            r, g, b, _ = board.color
            glPushMatrix()
            glTranslatef(board.pos[0], board.pos[1] - travel, board.pos[2])
            glColor4f(r, g, b, alpha)
            self._draw_box(board.width, board.depth, board.height)
            glPopMatrix()

        def draw_slide_holes(board):
            glPushMatrix()
            glTranslatef(board.pos[0], board.pos[1] - travel, board.pos[2])
            for h in board.holes:
                glPushMatrix()
                glTranslatef(h.x - board.pos[0], h.y - board.pos[1], h.z - board.pos[2])
                self._draw_hole(h.direction, h.diameter, h.depth)
                glPopMatrix()
            glPopMatrix()

        def draw_joint_holes(board, filter_partner=None):
            """Rysuje otwory łączeniowe. filter_partner=None → wszystkie."""
            glPushMatrix()
            glTranslatef(board.pos[0], board.pos[1] - travel, board.pos[2])
            for jh in board.joint_holes:
                if filter_partner is not None and jh.partner != filter_partner:
                    continue
                glPushMatrix()
                glTranslatef(jh.x - board.pos[0], jh.y - board.pos[1], jh.z - board.pos[2])
                self._draw_joint_hole(jh.direction, jh.element, jh.hole_type)
                glPopMatrix()
            glPopMatrix()

        if sel is None:
            for b in boards:
                draw_body(b, b.color[3])
                draw_slide_holes(b)
                draw_joint_holes(b)
        else:
            # Wszystkie korpusy – najpierw tło (posortowane od tyłu)
            others = sorted(
                [i for i in range(len(boards)) if i != sel],
                key=lambda i: -(boards[i].pos[1] + boards[i].depth / 2),
            )
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDepthMask(GL_FALSE)
            for i in others:
                draw_body(boards[i], 0.15)
            # wybrany – półprzezroczysty, ale na wierzchu
            draw_body(boards[sel], 0.5)
            glDepthMask(GL_TRUE)
            glDisable(GL_BLEND)

            # Prowadnice – zawsze widoczne
            for b in boards:
                draw_slide_holes(b)

            # Otwory łączeniowe wybranej deski – wszystkie, pełna widoczność
            draw_joint_holes(boards[sel])

            # Otwory łączeniowe innych desek – tylko te pasujące do wybranego
            for i in others:
                draw_joint_holes(boards[i], filter_partner=sel_name)

        self._draw_grid()

    def _draw_box(self, w, d, h):
        v = [
            (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),
            (0, 0, h), (w, 0, h), (w, d, h), (0, d, h),
        ]
        faces = [
            ([0,1,2,3], (0, 0,-1)),
            ([4,5,6,7], (0, 0, 1)),
            ([0,1,5,4], (0,-1, 0)),
            ([3,2,6,7], (0, 1, 0)),
            ([0,3,7,4], (-1,0, 0)),
            ([1,2,6,5], ( 1,0, 0)),
        ]
        glBegin(GL_QUADS)
        for idx, n in faces:
            glNormal3f(*n)
            for i in idx:
                glVertex3f(*v[i])
        glEnd()

        edges = [
            (0,1),(1,2),(2,3),(3,0),
            (4,5),(5,6),(6,7),(7,4),
            (0,4),(1,5),(2,6),(3,7),
        ]
        glLineWidth(1.0)
        glDisable(GL_LIGHTING)
        glColor3f(0.2, 0.15, 0.1)
        glBegin(GL_LINES)
        for a, b in edges:
            glVertex3f(*v[a])
            glVertex3f(*v[b])
        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_hole(self, direction, diameter, depth):
        """Stożkowe wiercenie: średnica na powierzchni = diameter, na głębokości depth = 2mm."""
        surface_r = 1.5       # 3mm średnicy na powierzchni
        tip_r = 0.0           # pełny stożek – zwęża się do punktu
        overshoot = 0.3       # lekko wystaje ponad powierzchnię – unika z-fightingu

        glColor3f(0.9, 0.2, 0.2)

        # Obroty: gluCylinder idzie wzdłuż +Z → obracamy na kierunek wiercenia
        # direction = normalna powierzchni (na zewnątrz), wiercenie idzie w kierunku odwrotnym
        _rot = {
            '-x': ( 90,  0, 1, 0),   # powierzchnia -X, wiercenie +X
            '+x': (-90,  0, 1, 0),   # powierzchnia +X, wiercenie -X
            '-y': (-90,  1, 0, 0),   # powierzchnia -Y, wiercenie +Y
            '+y': ( 90,  1, 0, 0),   # powierzchnia +Y, wiercenie -Y
            '-z': (  0,  1, 0, 0),   # wiercenie +Z – brak rotacji
            '+z': (180,  1, 0, 0),   # wiercenie -Z
        }
        # przesunięcie podstawy stożka poza powierzchnię (wzdłuż kierunku normalnej)
        _off = {
            '-x': (-overshoot, 0, 0),
            '+x': ( overshoot, 0, 0),
            '-y': (0, -overshoot, 0),
            '+y': (0,  overshoot, 0),
            '-z': (0, 0, -overshoot),
            '+z': (0, 0,  overshoot),
        }

        angle, ax, ay, az = _rot[direction]
        ox, oy, oz = _off[direction]
        total = depth + overshoot

        glPushMatrix()
        glTranslatef(ox, oy, oz)
        if angle:
            glRotatef(angle, ax, ay, az)

        q = gluNewQuadric()
        gluQuadricNormals(q, GLU_SMOOTH)

        # Podstawa stożka – pełne kółko na powierzchni
        gluDisk(q, 0, surface_r, 16, 1)

        # Stożek: szeroki przy powierzchni, zwęża się do punktu
        gluCylinder(q, surface_r, tip_r, total, 16, 1)

        gluDeleteQuadric(q)
        glPopMatrix()

    def _draw_joint_hole(self, direction: str, element: int, hole_type: str = 'confirmat'):
        """
        Otwór łączeniowy jako walec wg zasad:
          confirmat element=1 (czerwony): pogłębienie ø11×4,5mm + przelot ø5×13,5mm
          confirmat element=2 (zielony):  gwint ø5×35mm
          dowel element=1 (czerwony): kołek ø8, w płaszczyźnie 11mm głębokości
          dowel element=2 (zielony):  kołek ø8, w czole 27mm głębokości
        """
        _rot = {
            '-x': ( 90, 0,1,0), '+x': (-90, 0,1,0),
            '-y': (-90, 1,0,0), '+y': ( 90, 1,0,0),
            '-z': (  0, 1,0,0), '+z': (180, 1,0,0),
        }
        _off = {
            '-x': (-0.3,0,0), '+x': (0.3,0,0),
            '-y': (0,-0.3,0), '+y': (0,0.3,0),
            '-z': (0,0,-0.3), '+z': (0,0,0.3),
        }
        OVR = 0.3   # wychodzi 0.3mm poza powierzchnię – unika z-fightingu

        angle, ax, ay, az = _rot[direction]
        ox, oy, oz = _off[direction]

        glPushMatrix()
        glTranslatef(ox, oy, oz)
        if angle:
            glRotatef(angle, ax, ay, az)

        q = gluNewQuadric()
        gluQuadricNormals(q, GLU_SMOOTH)

        if hole_type == 'dowel':
            # Kołek drewniany ø8mm (zasada 30-31)
            r = 4.0  # ø8mm
            d = 11.0 if element == 1 else 27.0   # płaszczyzna / czoło
            glColor3f(0.9, 0.15, 0.15) if element == 1 else glColor3f(0.1, 0.75, 0.2)
            gluQuadricOrientation(q, GLU_INSIDE)
            gluCylinder(q, r, r, d + OVR, 20, 1)
            glTranslatef(0, 0, d + OVR)
            gluQuadricOrientation(q, GLU_OUTSIDE)
            gluDisk(q, 0, r, 20, 1)

        elif element == 1:
            glColor3f(0.9, 0.15, 0.15)          # czerwony
            c_r, c_d = 5.5, 4.5                  # pogłębienie ø11mm × 4,5mm
            t_r, t_d = 2.5, 13.5                 # przelot ø5mm × 13,5mm (18-4,5)

            # Walec pogłębienia
            gluQuadricOrientation(q, GLU_INSIDE)
            gluCylinder(q, c_r, c_r, c_d + OVR, 20, 1)
            # Pierścień na dnie pogłębienia (między ø11 a ø5)
            glTranslatef(0, 0, c_d + OVR)
            gluQuadricOrientation(q, GLU_OUTSIDE)
            gluDisk(q, t_r, c_r, 20, 1)
            # Walec otworu przelotowego
            gluQuadricOrientation(q, GLU_INSIDE)
            gluCylinder(q, t_r, t_r, t_d, 20, 1)
            # Zamknięcie dna
            glTranslatef(0, 0, t_d)
            gluQuadricOrientation(q, GLU_OUTSIDE)
            gluDisk(q, 0, t_r, 20, 1)

        else:
            glColor3f(0.1, 0.75, 0.2)            # zielony
            t_r, t_d = 2.5, 35.0                 # gwint ø5mm × 35mm

            gluQuadricOrientation(q, GLU_INSIDE)
            gluCylinder(q, t_r, t_r, t_d + OVR, 20, 1)
            glTranslatef(0, 0, t_d + OVR)
            gluQuadricOrientation(q, GLU_OUTSIDE)
            gluDisk(q, 0, t_r, 20, 1)

        gluDeleteQuadric(q)
        glPopMatrix()

    def _draw_grid(self):
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glLineWidth(0.5)

        s = self._scene_size * 0.8
        step = 100  # 10 cm
        r = range(-int(s) // step * step, int(s) + step, step)

        glBegin(GL_LINES)
        for i in r:
            glColor4f(0.35, 0.40, 0.55, 0.25)  # XY – niebieski
            glVertex3f(i, -s, 0); glVertex3f(i,  s, 0)
            glVertex3f(-s, i,  0); glVertex3f(s, i,  0)

            glColor4f(0.30, 0.48, 0.36, 0.25)  # XZ – zielony
            glVertex3f(i, 0, -s); glVertex3f(i, 0,  s)
            glVertex3f(-s, 0, i); glVertex3f(s,  0, i)

            glColor4f(0.50, 0.32, 0.32, 0.25)  # YZ – czerwony
            glVertex3f(0, i, -s); glVertex3f(0, i,  s)
            glVertex3f(0, -s, i); glVertex3f(0,  s, i)
        glEnd()

        # osie przez środek – wyraźniejsze
        glLineWidth(1.2)
        glBegin(GL_LINES)
        glColor4f(0.75, 0.20, 0.20, 0.7); glVertex3f(-s, 0, 0); glVertex3f(s, 0, 0)
        glColor4f(0.20, 0.75, 0.20, 0.7); glVertex3f(0, -s, 0); glVertex3f(0, s, 0)
        glColor4f(0.25, 0.45, 0.90, 0.7); glVertex3f(0, 0, -s); glVertex3f(0, 0, s)
        glEnd()

        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    def _draw_placeholder(self):
        glDisable(GL_LIGHTING)
        glColor3f(0.5, 0.5, 0.5)
        glBegin(GL_LINE_LOOP)
        for i in range(36):
            a = math.radians(i * 10)
            glVertex3f(math.cos(a)*100, math.sin(a)*100, 0)
        glEnd()
        glEnable(GL_LIGHTING)

    def mousePressEvent(self, e):
        self._last_pos = e.position()
        self._press_pos = e.position()
        self._pan_axis = None   # reset blokady osi przy każdym nowym kliknięciu

    def mouseMoveEvent(self, e):
        if self._last_pos is None:
            return
        dx = e.position().x() - self._last_pos.x()
        dy = e.position().y() - self._last_pos.y()
        self._last_pos = e.position()

        if e.buttons() & Qt.MouseButton.RightButton:
            # Przy pierwszym ruchu >5px zablokuj oś na resztę gestu
            if self._pan_axis is None and self._press_pos is not None:
                dp = e.position() - self._press_pos
                if (dp.x()**2 + dp.y()**2) > 25:
                    self._pan_axis = 'x' if abs(dp.x()) >= abs(dp.y()) else 'z'
            if self._pan_axis == 'x':
                self.pan_x -= dx * 0.5
            elif self._pan_axis == 'z':
                self.pan_z += dy * 0.5
        else:
            self.rot_y += dx * 0.4
            self.rot_x += dy * 0.4
        self.update()

    def mouseReleaseEvent(self, e):
        if (e.button() == Qt.MouseButton.LeftButton
                and self._press_pos is not None):
            dp = e.position() - self._press_pos
            if dp.x()**2 + dp.y()**2 < 25:   # <5px – klik, nie drag
                self._pick(int(e.position().x()), int(e.position().y()))
        self._last_pos = None
        self._press_pos = None

    def _pick(self, px, py):
        if self._mv_mat is None or not self.model:
            return
        py_gl = self.height() - py - 1
        near = gluUnProject(px, py_gl, 0.0, self._mv_mat, self._proj_mat, self._viewport)
        far  = gluUnProject(px, py_gl, 1.0, self._mv_mat, self._proj_mat, self._viewport)
        ro = np.array(near, dtype=float)
        rd = np.array(far,  dtype=float) - ro
        n = np.linalg.norm(rd)
        if n < 1e-9:
            return
        rd /= n

        travel = self.model.max_travel * self._open
        best_t, best_i = np.inf, None
        for i, b in enumerate(self.model.boards):
            bmin = np.array([b.pos[0],         b.pos[1] - travel,          b.pos[2]])
            bmax = np.array([b.pos[0]+b.width,  b.pos[1] - travel+b.depth, b.pos[2]+b.height])
            t = _ray_aabb(ro, rd, bmin, bmax)
            if t is not None and t < best_t:
                best_t, best_i = t, i

        self._selected = None if best_i == self._selected else best_i
        self.update()

    def wheelEvent(self, e):
        delta = e.angleDelta().y()
        self.zoom *= 1.0 + delta / 1200.0
        self.zoom = max(0.05, min(self.zoom, 20.0))
        self.update()

    def load_model(self, model: DrawerModel):
        self.model = model
        if model.boards:
            xs = [b.pos[0] for b in model.boards] + [b.pos[0] + b.width  for b in model.boards]
            ys = [b.pos[1] for b in model.boards] + [b.pos[1] + b.depth  for b in model.boards]
            zs = [b.pos[2] for b in model.boards] + [b.pos[2] + b.height for b in model.boards]
            self._scene_size = max(max(xs) - min(xs),
                                   max(ys) - min(ys),
                                   max(zs) - min(zs),
                                   300)
        self.update()


# ── Panel boczny ──────────────────────────────────────────────────────────────

class SidePanel(QWidget):
    def __init__(self, gl: GLWidget, parent=None):
        super().__init__(parent)
        self.gl = gl
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        grp_file = QGroupBox("Model")
        vl = QVBoxLayout(grp_file)
        btn_open = QPushButton("Otwórz YAML…")
        btn_open.clicked.connect(self._open_file)
        vl.addWidget(btn_open)
        self._lbl_file = QLabel("(brak)")
        self._lbl_file.setWordWrap(True)
        vl.addWidget(self._lbl_file)
        layout.addWidget(grp_file)

        grp_anim = QGroupBox("Szuflada")
        vl2 = QVBoxLayout(grp_anim)
        vl2.addWidget(QLabel("Otwarcie:"))
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(0)
        self._slider.valueChanged.connect(self._on_slider)
        vl2.addWidget(self._slider)
        self._lbl_pct = QLabel("0 %")
        vl2.addWidget(self._lbl_pct)
        btn_anim = QPushButton("Animuj otwarcie")
        btn_anim.setCheckable(True)
        btn_anim.toggled.connect(self._on_anim)
        self._btn_anim = btn_anim
        vl2.addWidget(btn_anim)
        layout.addWidget(grp_anim)

        grp_cam = QGroupBox("Kamera")
        vl3 = QVBoxLayout(grp_cam)
        btn_reset = QPushButton("Resetuj widok")
        btn_reset.clicked.connect(self._reset_cam)
        vl3.addWidget(btn_reset)
        layout.addWidget(grp_cam)

        layout.addStretch()

        self._timer = QTimer()
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._anim_tick)
        self._anim_dir = 1

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Otwórz model mebla", "", "YAML (*.yaml *.yml)"
        )
        if path:
            try:
                model = load_drawer(path)
                self.gl.load_model(model)
                self._lbl_file.setText(Path(path).name)
                self._slider.setValue(0)
            except Exception as e:
                self._lbl_file.setText(f"Błąd: {e}")

    def _on_slider(self, v):
        self._lbl_pct.setText(f"{v} %")
        self.gl.set_open(v / 100.0)

    def _on_anim(self, checked):
        if checked:
            self._timer.start()
        else:
            self._timer.stop()

    def _anim_tick(self):
        v = self._slider.value() + self._anim_dir
        if v >= 100: v = 100; self._anim_dir = -1
        elif v <= 0: v = 0;   self._anim_dir = 1
        self._slider.setValue(v)

    def _reset_cam(self):
        self.gl.rot_x = 25.0; self.gl.rot_y = -35.0
        self.gl.zoom = 1.0; self.gl.pan_x = 0.0; self.gl.pan_z = 0.0
        self.gl.update()


# ── Okno główne ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, yaml_path: str | None = None):
        super().__init__()
        self.setWindowTitle("Meblarz – Oglądarka mebli")
        self.resize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        hlay = QHBoxLayout(central)
        hlay.setContentsMargins(4, 4, 4, 4)

        self.gl = GLWidget()
        self.panel = SidePanel(self.gl)
        self.panel.setFixedWidth(230)

        hlay.addWidget(self.gl, stretch=1)
        hlay.addWidget(self.panel)

        if yaml_path:
            try:
                model = load_drawer(yaml_path)
                self.gl.load_model(model)
                self.panel._lbl_file.setText(Path(yaml_path).name)
            except Exception as e:
                print(f"Błąd ładowania modelu: {e}")


def main():
    # Musi być PRZED QApplication – wymusza desktop OpenGL zamiast ES2 przez RHI
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
    fmt.setVersion(2, 1)
    fmt.setDepthBufferSize(24)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    yaml_path = sys.argv[1] if len(sys.argv) > 1 else None
    if yaml_path is None:
        default = Path(__file__).parent / 'projekty' / 'szuflada.yaml'
        if default.exists():
            yaml_path = str(default)

    win = MainWindow(yaml_path)
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
