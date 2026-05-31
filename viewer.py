#!/usr/bin/env python3
"""
Meblarz Viewer – oglądarka modeli mebli.

Użycie:
    venv/bin/python viewer.py <plik.yaml>

Skróty klawiaturowe:
    Ctrl+O          wczytaj nowy plik
    Ctrl+R          przeładuj bieżący plik
    Home            resetuj widok
    Strzałki        przesuwanie (pan)
    Shift+Strzałki  obracanie
    Ctrl+↑/↓        zoom in / out
    2×Esc / Ctrl+Q  wyjście
"""

import sys
import math
import time
from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QSurfaceFormat, QKeySequence, QShortcut

from OpenGL.GL import *
from OpenGL.GLU import *

from elementy.szuflada import DrawerModel, Board, Hole, JointHole, load_drawer


def _ray_aabb(ro, rd, bmin, bmax):
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


# ── Stałe sterowania ──────────────────────────────────────────────────────────

PAN_STEP  = 15.0   # mm
ROT_STEP  = 4.0    # stopnie
ZOOM_STEP = 0.12   # mnożnik


# ── OpenGL widget ─────────────────────────────────────────────────────────────

class GLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: DrawerModel | None = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.rot_x = 25.0
        self.rot_y = -35.0
        self.zoom  = 1.0
        self.pan_x = 0.0
        self.pan_z = 0.0

        self._last_pos  = None
        self._press_pos = None
        self._pan_axis: str | None = None
        self._open      = 0.0
        self._scene_size = 500.0
        self._selected: int | None = None
        self._mv_mat   = None
        self._proj_mat = None
        self._viewport = None

    # ── API ───────────────────────────────────────────────────────────────────

    def set_open(self, v: float):
        self._open = v
        self.update()

    def reset_view(self):
        self.rot_x = 25.0; self.rot_y = -35.0
        self.zoom  = 1.0;  self.pan_x = 0.0; self.pan_z = 0.0
        self.update()

    def load_model(self, model: DrawerModel):
        self.model = model
        self._selected = None
        if model.boards:
            xs = [b.pos[0] for b in model.boards] + [b.pos[0]+b.width  for b in model.boards]
            ys = [b.pos[1] for b in model.boards] + [b.pos[1]+b.depth  for b in model.boards]
            zs = [b.pos[2] for b in model.boards] + [b.pos[2]+b.height for b in model.boards]
            self._scene_size = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs), 300)
        self.update()

    # ── OpenGL ────────────────────────────────────────────────────────────────

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING); glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glShadeModel(GL_SMOOTH); glEnable(GL_NORMALIZE)
        glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 2.0, 3.0, 0.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [0.85, 0.85, 0.80, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.30, 0.30, 0.30, 1.0])
        glClearColor(0.18, 0.18, 0.22, 1.0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, max(h, 1))
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
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
        self._mv_mat   = glGetDoublev(GL_MODELVIEW_MATRIX)
        self._proj_mat = glGetDoublev(GL_PROJECTION_MATRIX)
        self._viewport = glGetIntegerv(GL_VIEWPORT)
        if self.model:
            self._draw_model()
        else:
            self._draw_placeholder()

    # ── Rysowanie modelu ──────────────────────────────────────────────────────

    def _draw_model(self):
        travel   = self.model.max_travel * self._open
        sel      = self._selected
        boards   = self.model.boards
        sel_name = boards[sel].name if sel is not None else None

        def draw_body(b, alpha):
            r, g, bv, _ = b.color
            glPushMatrix()
            glTranslatef(b.pos[0], b.pos[1] - travel, b.pos[2])
            glColor4f(r, g, bv, alpha)
            self._draw_box(b.width, b.depth, b.height)
            glPopMatrix()

        def draw_slide_holes(b):
            glPushMatrix()
            glTranslatef(b.pos[0], b.pos[1] - travel, b.pos[2])
            for h in b.holes:
                glPushMatrix()
                glTranslatef(h.x - b.pos[0], h.y - b.pos[1], h.z - b.pos[2])
                self._draw_hole(h.direction, h.diameter, h.depth)
                glPopMatrix()
            glPopMatrix()

        def draw_joint_holes(b, filter_partner=None):
            glPushMatrix()
            glTranslatef(b.pos[0], b.pos[1] - travel, b.pos[2])
            for jh in b.joint_holes:
                if filter_partner is not None and jh.partner != filter_partner:
                    continue
                glPushMatrix()
                glTranslatef(jh.x - b.pos[0], jh.y - b.pos[1], jh.z - b.pos[2])
                self._draw_joint_hole(jh.direction, jh.element, jh.hole_type)
                glPopMatrix()
            glPopMatrix()

        if sel is None:
            for b in boards:
                draw_body(b, b.color[3])
                draw_slide_holes(b)
                draw_joint_holes(b)
        else:
            others = sorted(
                [i for i in range(len(boards)) if i != sel],
                key=lambda i: -(boards[i].pos[1] + boards[i].depth / 2),
            )
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDepthMask(GL_FALSE)
            for i in others:
                draw_body(boards[i], 0.15)
            draw_body(boards[sel], 0.5)
            glDepthMask(GL_TRUE)
            glDisable(GL_BLEND)
            for b in boards:
                draw_slide_holes(b)
            draw_joint_holes(boards[sel])
            for i in others:
                draw_joint_holes(boards[i], filter_partner=sel_name)

        self._draw_grid()

    def _draw_box(self, w, d, h):
        v = [(0,0,0),(w,0,0),(w,d,0),(0,d,0),(0,0,h),(w,0,h),(w,d,h),(0,d,h)]
        faces = [
            ([0,1,2,3],(0,0,-1)),([4,5,6,7],(0,0,1)),
            ([0,1,5,4],(0,-1,0)),([3,2,6,7],(0,1,0)),
            ([0,3,7,4],(-1,0,0)),([1,2,6,5],(1,0,0)),
        ]
        glBegin(GL_QUADS)
        for idx, n in faces:
            glNormal3f(*n)
            for i in idx:
                glVertex3f(*v[i])
        glEnd()
        edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
        glLineWidth(1.0); glDisable(GL_LIGHTING)
        glColor3f(0.2, 0.15, 0.1)
        glBegin(GL_LINES)
        for a, b in edges:
            glVertex3f(*v[a]); glVertex3f(*v[b])
        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_hole(self, direction, diameter, depth):
        surface_r = 1.5; tip_r = 0.0; overshoot = 0.3
        _rot = {'-x':(90,0,1,0),'+x':(-90,0,1,0),'-y':(-90,1,0,0),'+y':(90,1,0,0),'-z':(0,1,0,0),'+z':(180,1,0,0)}
        _off = {'-x':(-overshoot,0,0),'+x':(overshoot,0,0),'-y':(0,-overshoot,0),'+y':(0,overshoot,0),'-z':(0,0,-overshoot),'+z':(0,0,overshoot)}
        angle,ax,ay,az = _rot[direction]; ox,oy,oz = _off[direction]
        glColor3f(0.9, 0.2, 0.2)
        glPushMatrix()
        glTranslatef(ox,oy,oz)
        if angle: glRotatef(angle,ax,ay,az)
        q = gluNewQuadric(); gluQuadricNormals(q, GLU_SMOOTH)
        gluDisk(q, 0, surface_r, 16, 1)
        gluCylinder(q, surface_r, tip_r, depth+overshoot, 16, 1)
        gluDeleteQuadric(q)
        glPopMatrix()

    def _draw_joint_hole(self, direction, element, hole_type='confirmat'):
        _rot = {'-x':(90,0,1,0),'+x':(-90,0,1,0),'-y':(-90,1,0,0),'+y':(90,1,0,0),'-z':(0,1,0,0),'+z':(180,1,0,0)}
        _off = {'-x':(-0.3,0,0),'+x':(0.3,0,0),'-y':(0,-0.3,0),'+y':(0,0.3,0),'-z':(0,0,-0.3),'+z':(0,0,0.3)}
        OVR = 0.3
        angle,ax,ay,az = _rot[direction]; ox,oy,oz = _off[direction]
        glPushMatrix()
        glTranslatef(ox,oy,oz)
        if angle: glRotatef(angle,ax,ay,az)
        q = gluNewQuadric(); gluQuadricNormals(q, GLU_SMOOTH)
        if hole_type == 'dowel':
            r = 4.0; d = 11.0 if element == 1 else 27.0
            glColor3f(0.9,0.15,0.15) if element==1 else glColor3f(0.1,0.75,0.2)
            gluQuadricOrientation(q, GLU_INSIDE)
            gluCylinder(q, r, r, d+OVR, 20, 1)
            glTranslatef(0,0,d+OVR)
            gluQuadricOrientation(q, GLU_OUTSIDE)
            gluDisk(q, 0, r, 20, 1)
        elif element == 1:
            glColor3f(0.9,0.15,0.15)
            c_r,c_d,t_r,t_d = 5.5,4.5,2.5,13.5
            gluQuadricOrientation(q, GLU_INSIDE)
            gluCylinder(q, c_r, c_r, c_d+OVR, 20, 1)
            glTranslatef(0,0,c_d+OVR)
            gluQuadricOrientation(q, GLU_OUTSIDE); gluDisk(q, t_r, c_r, 20, 1)
            gluQuadricOrientation(q, GLU_INSIDE)
            gluCylinder(q, t_r, t_r, t_d, 20, 1)
            glTranslatef(0,0,t_d)
            gluQuadricOrientation(q, GLU_OUTSIDE); gluDisk(q, 0, t_r, 20, 1)
        else:
            glColor3f(0.1,0.75,0.2)
            t_r,t_d = 2.5,35.0
            gluQuadricOrientation(q, GLU_INSIDE)
            gluCylinder(q, t_r, t_r, t_d+OVR, 20, 1)
            glTranslatef(0,0,t_d+OVR)
            gluQuadricOrientation(q, GLU_OUTSIDE); gluDisk(q, 0, t_r, 20, 1)
        gluDeleteQuadric(q)
        glPopMatrix()

    def _draw_grid(self):
        glDisable(GL_LIGHTING); glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA); glLineWidth(0.5)
        s = self._scene_size * 0.8; step = 100
        r = range(-int(s)//step*step, int(s)+step, step)
        glBegin(GL_LINES)
        for i in r:
            glColor4f(0.35,0.40,0.55,0.25); glVertex3f(i,-s,0); glVertex3f(i,s,0); glVertex3f(-s,i,0); glVertex3f(s,i,0)
            glColor4f(0.30,0.48,0.36,0.25); glVertex3f(i,0,-s); glVertex3f(i,0,s); glVertex3f(-s,0,i); glVertex3f(s,0,i)
            glColor4f(0.50,0.32,0.32,0.25); glVertex3f(0,i,-s); glVertex3f(0,i,s); glVertex3f(0,-s,i); glVertex3f(0,s,i)
        glEnd()
        glLineWidth(1.2); glBegin(GL_LINES)
        glColor4f(0.75,0.20,0.20,0.7); glVertex3f(-s,0,0); glVertex3f(s,0,0)
        glColor4f(0.20,0.75,0.20,0.7); glVertex3f(0,-s,0); glVertex3f(0,s,0)
        glColor4f(0.25,0.45,0.90,0.7); glVertex3f(0,0,-s); glVertex3f(0,0,s)
        glEnd()
        glLineWidth(1.0); glDisable(GL_BLEND); glEnable(GL_LIGHTING)

    def _draw_placeholder(self):
        glDisable(GL_LIGHTING); glColor3f(0.5,0.5,0.5)
        glBegin(GL_LINE_LOOP)
        for i in range(36):
            a = math.radians(i*10); glVertex3f(math.cos(a)*100, math.sin(a)*100, 0)
        glEnd(); glEnable(GL_LIGHTING)

    # ── Mysz ──────────────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        self._last_pos = e.position(); self._press_pos = e.position(); self._pan_axis = None

    def mouseMoveEvent(self, e):
        if self._last_pos is None:
            return
        dx = e.position().x() - self._last_pos.x()
        dy = e.position().y() - self._last_pos.y()
        self._last_pos = e.position()
        if e.buttons() & Qt.MouseButton.RightButton:
            if self._pan_axis is None and self._press_pos is not None:
                dp = e.position() - self._press_pos
                if dp.x()**2 + dp.y()**2 > 25:
                    self._pan_axis = 'x' if abs(dp.x()) >= abs(dp.y()) else 'z'
            if self._pan_axis == 'x':   self.pan_x -= dx * 0.5
            elif self._pan_axis == 'z': self.pan_z += dy * 0.5
        else:
            self.rot_y += dx * 0.4; self.rot_x += dy * 0.4
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            dp = e.position() - self._press_pos
            if dp.x()**2 + dp.y()**2 < 25:
                self._pick(int(e.position().x()), int(e.position().y()))
        self._last_pos = None; self._press_pos = None

    def _pick(self, px, py):
        if self._mv_mat is None or not self.model:
            return
        py_gl = self.height() - py - 1
        near = gluUnProject(px, py_gl, 0.0, self._mv_mat, self._proj_mat, self._viewport)
        far  = gluUnProject(px, py_gl, 1.0, self._mv_mat, self._proj_mat, self._viewport)
        ro = np.array(near, dtype=float)
        rd = np.array(far,  dtype=float) - ro
        n  = np.linalg.norm(rd)
        if n < 1e-9: return
        rd /= n
        travel = self.model.max_travel * self._open
        best_t, best_i = np.inf, None
        for i, b in enumerate(self.model.boards):
            bmin = np.array([b.pos[0],        b.pos[1]-travel,         b.pos[2]])
            bmax = np.array([b.pos[0]+b.width, b.pos[1]-travel+b.depth, b.pos[2]+b.height])
            t = _ray_aabb(ro, rd, bmin, bmax)
            if t is not None and t < best_t:
                best_t, best_i = t, i
        self._selected = None if best_i == self._selected else best_i
        self.update()

    def wheelEvent(self, e):
        self.zoom *= 1.0 + e.angleDelta().y() / 1200.0
        self.zoom = max(0.05, min(self.zoom, 20.0)); self.update()


# ── Okno główne ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, yaml_path: str):
        super().__init__()
        self._yaml_path = yaml_path
        self._last_esc  = 0.0       # czas ostatniego Escape
        self._open_pct  = 0         # % otwarcia szuflady

        self.gl = GLWidget()
        self.setCentralWidget(self.gl)

        self._load(yaml_path)
        self.showMaximized()
        self._setup_shortcuts()

    # ── Skróty klawiaturowe ───────────────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=QApplication.quit)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._open_file)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self._reload)

    def keyPressEvent(self, e):
        k   = e.key()
        mod = e.modifiers()
        Key = Qt.Key

        # Wyjście
        if k == Key.Key_Escape:
            now = time.monotonic()
            if now - self._last_esc < 1.0:
                QApplication.quit()
            self._last_esc = now
            return

        # Reset widoku
        if k == Key.Key_Home:
            self.gl.reset_view(); return

        # Szuflada: + / -
        if k in (Key.Key_Plus, Key.Key_Equal):
            self._set_open(self._open_pct + 5); return
        if k == Key.Key_Minus:
            self._set_open(self._open_pct - 5); return

        # Strzałki
        if k not in (Key.Key_Left, Key.Key_Right, Key.Key_Up, Key.Key_Down):
            super().keyPressEvent(e); return

        if mod & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+↑/↓ → zoom
            if k == Key.Key_Up:
                self.gl.zoom = min(self.gl.zoom * (1 + ZOOM_STEP), 20.0)
            elif k == Key.Key_Down:
                self.gl.zoom = max(self.gl.zoom * (1 - ZOOM_STEP), 0.05)
        elif mod & Qt.KeyboardModifier.ShiftModifier:
            # Shift+Strzałki → obrót
            if k == Key.Key_Left:  self.gl.rot_y -= ROT_STEP
            if k == Key.Key_Right: self.gl.rot_y += ROT_STEP
            if k == Key.Key_Up:    self.gl.rot_x -= ROT_STEP
            if k == Key.Key_Down:  self.gl.rot_x += ROT_STEP
        else:
            # Strzałki → pan
            step = PAN_STEP
            if k == Key.Key_Left:  self.gl.pan_x -= step
            if k == Key.Key_Right: self.gl.pan_x += step
            if k == Key.Key_Up:    self.gl.pan_z += step
            if k == Key.Key_Down:  self.gl.pan_z -= step

        self.gl.update()

    # ── Plik ──────────────────────────────────────────────────────────────────

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Otwórz model mebla",
            str(Path(self._yaml_path).parent),
            "YAML (*.yaml *.yml)",
        )
        if path:
            self._load(path)

    def _reload(self):
        self._load(self._yaml_path)

    def _load(self, path: str):
        try:
            model = load_drawer(path)
            self._yaml_path = path
            self._open_pct  = 0
            self.gl.load_model(model)
            self.gl.set_open(0.0)
            self.setWindowTitle(f"Meblarz — {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Błąd wczytywania", str(exc))

    def _set_open(self, pct: int):
        self._open_pct = max(0, min(100, pct))
        self.gl.set_open(self._open_pct / 100.0)


# ── Start ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Użycie: venv/bin/python viewer.py <plik.yaml>", file=sys.stderr)
        sys.exit(1)

    yaml_path = sys.argv[1]
    if not Path(yaml_path).exists():
        print(f"Błąd: plik '{yaml_path}' nie istnieje.", file=sys.stderr)
        sys.exit(1)

    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
    fmt.setVersion(2, 1)
    fmt.setDepthBufferSize(24)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    win = MainWindow(yaml_path)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
