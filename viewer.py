#!/usr/bin/env python3
"""
Meblarz Viewer — 3D furniture model viewer.

Usage:
    venv/bin/python viewer.py <file.yaml>

Keyboard shortcuts:
    Ctrl+O          open file
    Ctrl+R          reload current file
    Home            reset view
    Arrows          pan
    Shift+Arrows    rotate
    Ctrl+↑/↓        zoom in / out
    2×Esc / Ctrl+Q  quit
"""

import atexit
import os
import sys
import re
import math
import time
import termios
import tty
from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QDialog, QVBoxLayout, QLabel,
)
from PyQt6.QtCore import QEvent, QSocketNotifier, Qt, QTimer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QFont, QImage, QKeyEvent, QKeySequence, QShortcut, QSurfaceFormat

from OpenGL.GL import *
from OpenGL.GLU import *

import yaml as _yaml
from parts.drawer import DrawerModel, Board, Hole, JointHole, load_drawer
from parts.dresser import load_dresser as load_komoda
from parts.desk_drawer_wall import load_desk_drawer_wall
from parts.kitchen_tall_unit import load_kitchen_tall_unit
from parts.kitchen_ventilation import routable_guide_rectangles
from parts.preview_mesh import board_mesh, ray_mesh


def _load_config() -> dict:
    path = Path(__file__).parent / 'config.yaml'
    try:
        with open(path) as f:
            return _yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def _cfg(key: str, default):
    """Return a nested config value, e.g. 'animation.duration'."""
    node = _CFG
    for k in key.split('.'):
        if not isinstance(node, dict) or k not in node:
            return default
        node = node[k]
    return node


_CFG = _load_config()


# Terminal escape sequences emitted by common SSH terminal emulators.
_TERMINAL_KEYS = {
    b'\x1b[A':    (Qt.Key.Key_Up,    Qt.KeyboardModifier.NoModifier),
    b'\x1b[B':    (Qt.Key.Key_Down,  Qt.KeyboardModifier.NoModifier),
    b'\x1b[C':    (Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier),
    b'\x1b[D':    (Qt.Key.Key_Left,  Qt.KeyboardModifier.NoModifier),
    b'\x1b[1;2A': (Qt.Key.Key_Up,    Qt.KeyboardModifier.ShiftModifier),
    b'\x1b[1;2B': (Qt.Key.Key_Down,  Qt.KeyboardModifier.ShiftModifier),
    b'\x1b[1;2C': (Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier),
    b'\x1b[1;2D': (Qt.Key.Key_Left,  Qt.KeyboardModifier.ShiftModifier),
    b'\x1b[1;5A': (Qt.Key.Key_Up,    Qt.KeyboardModifier.ControlModifier),
    b'\x1b[1;5B': (Qt.Key.Key_Down,  Qt.KeyboardModifier.ControlModifier),
    b'\x1b[H':    (Qt.Key.Key_Home,  Qt.KeyboardModifier.NoModifier),
    b'\x1bOH':    (Qt.Key.Key_Home,  Qt.KeyboardModifier.NoModifier),
    b'\x1b[1~':   (Qt.Key.Key_Home,  Qt.KeyboardModifier.NoModifier),
}

_TERMINAL_CHAR_KEYS = {
    ord('+'): Qt.Key.Key_Plus,
    ord('='): Qt.Key.Key_Equal,
    ord('-'): Qt.Key.Key_Minus,
    ord('p'): Qt.Key.Key_P,
    ord('P'): Qt.Key.Key_P,
    ord('n'): Qt.Key.Key_N,
    ord('N'): Qt.Key.Key_N,
    ord('h'): Qt.Key.Key_H,
    ord('H'): Qt.Key.Key_H,
    ord('q'): Qt.Key.Key_Q,
    ord('Q'): Qt.Key.Key_Q,
    ord('w'): Qt.Key.Key_W,
    ord('W'): Qt.Key.Key_W,
    ord('s'): Qt.Key.Key_S,
    ord('S'): Qt.Key.Key_S,
    ord('a'): Qt.Key.Key_A,
    ord('A'): Qt.Key.Key_A,
    ord('d'): Qt.Key.Key_D,
    ord('D'): Qt.Key.Key_D,
    ord('x'): Qt.Key.Key_X,
    ord('X'): Qt.Key.Key_X,
    ord('y'): Qt.Key.Key_Y,
    ord('Y'): Qt.Key.Key_Y,
    ord('z'): Qt.Key.Key_Z,
    ord('Z'): Qt.Key.Key_Z,
    0x0F:     Qt.Key.Key_O,  # Ctrl+O
    0x11:     Qt.Key.Key_Q,  # Ctrl+Q
    0x12:     Qt.Key.Key_R,  # Ctrl+R
}


class TerminalInput:
    """Feed keystrokes from the SSH terminal into the Qt window."""

    def __init__(self, window: QMainWindow):
        self.window = window
        self._buffer = bytearray()
        self._saved_termios = None
        self._notifier = None
        self._escape_timer = QTimer(window)
        self._escape_timer.setSingleShot(True)
        self._escape_timer.timeout.connect(self._flush_escape)

        try:
            self._fd = sys.stdin.fileno()
        except (AttributeError, OSError):
            return
        if not os.isatty(self._fd):
            return

        self._saved_termios = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        self._notifier = QSocketNotifier(self._fd, QSocketNotifier.Type.Read, window)
        self._notifier.activated.connect(self._read)
        atexit.register(self.close)
        print('Sterowanie z terminala: strzałki, Shift/Ctrl+strzałki, +/-, P, N, H, Home.')

    def close(self):
        if self._notifier is not None:
            self._notifier.setEnabled(False)
            self._notifier = None
        if self._saved_termios is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved_termios)
            self._saved_termios = None

    def _read(self):
        try:
            data = os.read(self._fd, 1024)
        except BlockingIOError:
            return
        if not data:
            self.close()
            return
        self._buffer.extend(data)
        self._process_buffer()

    def _send(self, key, modifiers=Qt.KeyboardModifier.NoModifier):
        self.window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, modifiers))

    def _process_buffer(self):
        while self._buffer:
            for sequence in sorted(_TERMINAL_KEYS, key=len, reverse=True):
                if self._buffer.startswith(sequence):
                    key, modifiers = _TERMINAL_KEYS[sequence]
                    del self._buffer[:len(sequence)]
                    self._escape_timer.stop()
                    self._send(key, modifiers)
                    break
            else:
                if self._buffer[0] == 0x1B:
                    if any(sequence.startswith(self._buffer) for sequence in _TERMINAL_KEYS):
                        self._escape_timer.start(100)
                        return
                    del self._buffer[0]
                    self._send(Qt.Key.Key_Escape)
                    continue

                char = self._buffer.pop(0)
                key = _TERMINAL_CHAR_KEYS.get(char)
                if key is None:
                    continue
                modifiers = Qt.KeyboardModifier.ControlModifier if char in (0x0F, 0x11, 0x12) else Qt.KeyboardModifier.NoModifier
                self._send(key, modifiers)
                continue
            continue

    def _flush_escape(self):
        if self._buffer and self._buffer[0] == 0x1B:
            del self._buffer[0]
            self._send(Qt.Key.Key_Escape)
            self._process_buffer()


def _movable_group(board: Board) -> str:
    """Return the movable-group key (e.g. 'drawer_0') or 'default' for standalone drawers."""
    if board.motion_parent:
        match = re.match(r'^((?:tower|kitchen)_drawer_\d+)_', board.motion_parent)
        return match.group(1) if match else board.motion_parent
    if board.opening in ('lift_up', 'hinge_left', 'hinge_right'):
        return board.name
    m = re.match(r'^(fridge_(?:lower|upper)_door)_sliding_connector_', board.name)
    if m:
        return m.group(1)
    m = re.match(r'^(drawer_\d+)_', board.name)
    if m:
        return m.group(1)
    m = re.match(r'^((?:tower|kitchen)_drawer_\d+)_', board.name)
    if m:
        return m.group(1)
    return 'keyboard_tray' if board.name.startswith('keyboard_tray') else 'default'


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


# ── Control constants ─────────────────────────────────────────────────────────

PAN_STEP       = _cfg('controls.pan_step',           15.0)
ROT_STEP       = _cfg('controls.rot_step',           4.0)
ZOOM_STEP      = _cfg('controls.zoom_step',          0.12)
ANIM_DURATION  = _cfg('animation.duration',          1.0)
ANIM_FPS       = _cfg('animation.fps',               60)
ALPHA_INACTIVE = _cfg('transparency.inactive',       0.15)
ALPHA_SELECTED = _cfg('transparency.selected',       0.50)

# Visual limit for opening fronts. At 90° the narrow edge of a front stays in
# the side-board outline instead of protruding past the cabinet exterior.
HINGE_OPEN_ANGLE = 90.0
# At 90° the entire 18 mm door thickness is coplanar with the 18 mm side board:
# both its inner and outer faces coincide with the respective faces of the side.
HINGE_SIDE_REVEAL = 2.0
# At 90° the hinge-side edge would otherwise sit 16 mm behind the side front.
# Move it 18 mm forward: 16 mm compensation plus a 2 mm visible clearance.
HINGE_OPEN_FRONT_CLEARANCE = 18.0
# Lift-up flap: with a 2 mm closed top reveal, its full thickness is aligned
# between the inner and outer planes of the top panel at 90°.
LIFT_OPEN_FRONT_CLEARANCE = 2.0
LIFT_CLOSED_TOP_REVEAL = 2.0
EYE_HEIGHT     = _cfg('initial_view.eye_height',     1500.0)   # mm


# ── Help dialog ───────────────────────────────────────────────────────────────

_SHORTCUTS = [
    ("View", [
        ("Home",               "reset view"),
        ("P",                  "toggle perspective / ortho"),
        ("X / Y / Z",          "axis view; repeat for opposite side (keeps P mode)"),
        ("←→↑↓",              "pan"),
        ("Shift + ←→↑↓",      "rotate"),
        ("Ctrl + ↑ / ↓",      "zoom in / out"),
        ("A / D",              "rotate left / right"),
        ("W / S",              "rotate up / down"),
        ("Scroll wheel",       "zoom"),
        ("N",                  "dimensions of selected (next: +holes)"),
    ]),
    ("Mouse", [
        ("Left drag",          "rotate"),
        ("Right drag",         "pan (axis lock)"),
        ("Left click",         "select board"),
        ("Ctrl + left click / double click", "open / close movable element"),
    ]),
    ("Drawers", [
        ("+ / -",              "open / close all"),
    ]),
    ("File", [
        ("Ctrl+O",             "open YAML file"),
        ("Ctrl+R",             "reload current file"),
    ]),
    ("App", [
        ("H",                  "this help"),
        ("2 × Esc / Ctrl+Q",   "quit"),
    ]),
]

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard shortcuts")
        self.setModal(False)
        self.setMinimumWidth(400)

        self.setStyleSheet("""
            QDialog        { background: #232328; color: #ddd; }
            QLabel.header  { color: #8ab4f8; font-weight: bold; margin-top: 8px; }
            QLabel.row     { font-family: monospace; color: #ddd; padding: 1px 0; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(18, 14, 18, 14)

        title = QLabel("Keyboard shortcuts")
        f = QFont(); f.setPointSize(12); f.setBold(True)
        title.setFont(f)
        title.setStyleSheet("color: #fff; margin-bottom: 6px;")
        layout.addWidget(title)

        for section, rows in _SHORTCUTS:
            hdr = QLabel(section)
            hdr.setProperty("class", "header")
            hdr.setStyleSheet("color: #8ab4f8; font-weight: bold; margin-top: 8px;")
            layout.addWidget(hdr)
            for key, desc in rows:
                lbl = QLabel(f"  {key:<22} {desc}")
                lbl.setProperty("class", "row")
                lbl.setStyleSheet("font-family: monospace; color: #ddd; padding: 1px 0;")
                layout.addWidget(lbl)

        hint = QLabel("Close: Esc")
        hint.setStyleSheet("color: #888; margin-top: 10px; font-size: 10pt;")
        layout.addWidget(hint)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)


# ── OpenGL widget ─────────────────────────────────────────────────────────────

class GLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: DrawerModel | None = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.rot_x = _cfg('initial_view.rot_x', 0.0)
        self.rot_y = _cfg('initial_view.rot_y', -35.0)
        self.zoom  = _cfg('initial_view.zoom', 1.0)
        self.pan_x = 0.0
        self.pan_z = 0.0

        self._last_pos  = None
        self._press_pos = None
        self._pan_axis: str | None = None
        self._pending_click_pos: tuple[int, int] | None = None
        self._suppress_click_release = False
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._finish_single_click)
        self._open_per_group: dict[str, float] = {}
        self._board_group_keys: list[str] = []
        self._model_center_z: float = 0.0
        self._grid_back_y:    float = 0.0   # back face of furniture (max Y)
        self._grid_left_x:    float = 0.0   # left face of furniture (min X)
        self._anim_targets: dict[str, float] = {}                   # grupa → cel (0.0–1.0)
        self._anim_start: dict[str, tuple[float, float]] = {}       # grupa → (wartość_startowa, czas)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(1000 // ANIM_FPS)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._scene_size  = 500.0
        self._selected: int | None = None
        self._mv_mat   = None
        self._proj_mat = None
        self._viewport = None
        self._perspective    = True
        self._axis_centered = False
        self._axis_view = None
        self._texture_ids: dict[str, int] = {}

    # ── API ───────────────────────────────────────────────────────────────────

    def set_open_group(self, key: str, v: float, _repaint: bool = True):
        self._anim_targets.pop(key, None)
        self._anim_start.pop(key, None)
        self._open_per_group[key] = max(0.0, min(1.0, v))
        if _repaint:
            self.update()

    def animate_group(self, key: str, target: float):
        cur = self._open_per_group.get(key, 0.0)
        if abs(cur - target) < 1e-4:
            return
        self._anim_targets[key] = max(0.0, min(1.0, target))
        self._anim_start[key]   = (cur, time.monotonic())
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _anim_tick(self):
        now  = time.monotonic()
        done = []
        for key, target in self._anim_targets.items():
            start_val, start_time = self._anim_start[key]
            t = min((now - start_time) / ANIM_DURATION, 1.0)
            # smoothstep ease-in-out
            eased = t * t * (3.0 - 2.0 * t)
            self._open_per_group[key] = start_val + (target - start_val) * eased
            if t >= 1.0:
                self._open_per_group[key] = target
                done.append(key)
        for key in done:
            del self._anim_targets[key]
            del self._anim_start[key]
        if not self._anim_targets:
            self._anim_timer.stop()
        self.update()

    def reset_view(self):
        self._axis_centered = False
        self._axis_view = None
        self.rot_x = _cfg('initial_view.rot_x', 0.0)
        self.rot_y = _cfg('initial_view.rot_y', -35.0)
        self.zoom  = _cfg('initial_view.zoom', 1.0)
        self.pan_x = 0.0; self.pan_z = 0.0
        self.update()

    def set_axis_view(self, axis: str):
        """View an axis, alternating sides without changing projection mode."""
        views = {
            'x': ((0.0, -90.0), (0.0, 90.0)),  # right / left
            'y': ((0.0, 0.0), (0.0, 180.0)),   # front / back
            'z': ((90.0, 0.0), (-90.0, 0.0)),  # top / bottom
        }
        positive, negative = views[axis]
        repeat = self._axis_view == axis and (self.rot_x, self.rot_y) == positive
        self.rot_x, self.rot_y = negative if repeat else positive
        self._axis_view = axis
        self._axis_centered = True
        self.pan_x = 0.0
        self.pan_z = 0.0
        self.update()

    def load_model(self, model: DrawerModel):
        self.model = model
        self._selected = None
        self._board_group_keys = [_movable_group(b) for b in model.boards]
        self._open_per_group = {}
        self._anim_targets.clear()
        self._anim_start.clear()
        self._anim_timer.stop()
        if model.boards:
            xs = [b.pos[0] for b in model.boards] + [b.pos[0]+b.width  for b in model.boards]
            ys = [b.pos[1] for b in model.boards] + [b.pos[1]+b.depth  for b in model.boards]
            zs = [b.pos[2] for b in model.boards] + [b.pos[2]+b.height for b in model.boards]
            self._scene_size     = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs), 300)
            self._model_center_z = (min(zs) + max(zs)) / 2
            self._grid_back_y    = max(ys)
            self._grid_left_x    = min(xs)
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

    def toggle_perspective(self):
        self._perspective = not self._perspective
        self.update()

    def resizeGL(self, w, h):
        glViewport(0, 0, w, max(h, 1))

    def _update_projection(self):
        w, h = self.width(), self.height()
        aspect = w / max(h, 1)
        dist   = self._scene_size * 2.5 / self.zoom
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        if self._perspective:
            gluPerspective(45.0, aspect, 1.0, 10000.0)
        else:
            s = dist * math.tan(math.radians(22.5))
            glOrtho(-s * aspect, s * aspect, -s, s, -10000.0, 10000.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        self._update_projection()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        dist     = self._scene_size * 2.5 / self.zoom
        orbit_z  = self._model_center_z + self.pan_z   # camera orbits around furniture centre
        eye_z    = EYE_HEIGHT           + self.pan_z   # camera stays at eye level above floor
        if self._axis_centered:
            eye_z = orbit_z
        gluLookAt(self.pan_x, -dist, eye_z,
                  self.pan_x,     0, orbit_z,
                  0, 0, 1)
        if self._axis_centered:
            glTranslatef(0, 0, self._model_center_z)
        glRotatef(self.rot_x, 1, 0, 0)
        glRotatef(self.rot_y, 0, 0, 1)
        if self._axis_centered:
            glTranslatef(0, 0, -self._model_center_z)
        self._mv_mat   = glGetDoublev(GL_MODELVIEW_MATRIX)
        self._proj_mat = glGetDoublev(GL_PROJECTION_MATRIX)
        self._viewport = glGetIntegerv(GL_VIEWPORT)
        if self.model:
            self._draw_model()
        else:
            self._draw_placeholder()

    # ── Rysowanie modelu ──────────────────────────────────────────────────────

    def _draw_model(self):
        sel      = self._selected
        boards   = self.model.boards
        sel_name = boards[sel].name if sel is not None else None
        _bidx    = {id(b): i for i, b in enumerate(boards)}
        by_name = {b.name: b for b in boards}

        def _apply_board_transform(b):
            """Apply drawer translation or a door rotation around its real hinge axis."""
            if b.motion_parent:
                parent = by_name[b.motion_parent]
                _apply_board_transform(parent)
                glTranslatef(*(b.pos[i] - parent.pos[i] for i in range(3)))
                glRotatef(b.yaw, 0, 0, 1)
                return
            glTranslatef(*b.pos)
            if not b.movable:
                glRotatef(b.yaw, 0, 0, 1)
                return
            key = self._board_group_keys[_bidx[id(b)]]
            travel = self.model.max_travel if b.travel is None else b.travel
            amount = self._open_per_group.get(key, 0.0) * b.move_fraction
            if b.opening == 'lift_up':
                # Top flap: horizontal X axis along its upper rear edge.
                glTranslatef(0, -LIFT_OPEN_FRONT_CLEARANCE * amount,
                             -(b.depth - LIFT_CLOSED_TOP_REVEAL) * amount)
                glTranslatef(0, b.depth, b.height)
                glRotatef(-90 * amount, 1, 0, 0)
                glTranslatef(0, -b.depth, -b.height)
            elif b.opening == 'hinge_left':
                pivot_x = b.depth - HINGE_SIDE_REVEAL
                glTranslatef(0, -HINGE_OPEN_FRONT_CLEARANCE * amount, 0)
                glTranslatef(pivot_x, b.depth, 0)
                # Free edge swings towards the viewer (negative Y), outside
                # the carcass, rather than into the cabinet.
                glRotatef(-HINGE_OPEN_ANGLE * amount, 0, 0, 1)
                glTranslatef(-pivot_x, -b.depth, 0)
            elif b.opening == 'hinge_right':
                pivot_x = b.width - (b.depth - HINGE_SIDE_REVEAL)
                glTranslatef(0, -HINGE_OPEN_FRONT_CLEARANCE * amount, 0)
                glTranslatef(pivot_x, b.depth, 0)
                glRotatef(HINGE_OPEN_ANGLE * amount, 0, 0, 1)
                glTranslatef(-pivot_x, -b.depth, 0)
            else:
                glTranslatef(0, -travel * amount, 0)
            glRotatef(b.yaw, 0, 0, 1)

        def draw_body(b, alpha):
            r, g, bv, _ = b.color
            glPushMatrix()
            _apply_board_transform(b)
            if b.texture:
                self._draw_textured_face(b, alpha)
                glPopMatrix()
                return
            glColor4f(r, g, bv, alpha)
            if b.preview_mesh:
                vertices, normals = board_mesh(b)
                glPushClientAttrib(GL_CLIENT_VERTEX_ARRAY_BIT)
                glEnableClientState(GL_VERTEX_ARRAY)
                glEnableClientState(GL_NORMAL_ARRAY)
                glVertexPointer(3, GL_FLOAT, 0, vertices)
                glNormalPointer(GL_FLOAT, 0, normals)
                glDrawArrays(GL_TRIANGLES, 0, len(vertices))
                glPopClientAttrib()
                glPopMatrix()
                return
            rabbets = [g for g in b.grooves if g['kind'] in ('back_rabbet', 'drawer_bottom')]
            if rabbets:
                depth = rabbets[0]['depth']
                self._draw_box(b.width, b.depth - depth, b.height)
                # Split the rear layer at every machining boundary; omit cut cells.
                xs = sorted({0, b.width, *[v for q in rabbets for v in (q['x'], q['x'] + q['span_x'])]})
                zs = sorted({0, b.height, *[v for q in rabbets for v in (q['z'], q['z'] + q['span_z'])]})
                for x1, x2 in zip(xs, xs[1:]):
                    for z1, z2 in zip(zs, zs[1:]):
                        if any(q['x'] <= (x1+x2)/2 <= q['x']+q['span_x'] and
                               q['z'] <= (z1+z2)/2 <= q['z']+q['span_z'] for q in rabbets):
                            continue
                        glPushMatrix()
                        glTranslatef(x1, b.depth - depth, z1)
                        glColor4f(r, g, bv, alpha)
                        self._draw_box(x2-x1, depth, z2-z1)
                        glPopMatrix()
            elif b.preview_shape == 'cylinder_z':
                glPushMatrix()
                glTranslatef(b.width / 2, b.depth / 2, 0)
                q = gluNewQuadric()
                gluQuadricNormals(q, GLU_SMOOTH)
                radius = b.width / 2
                gluCylinder(q, radius, radius, b.height, 24, 1)
                gluQuadricOrientation(q, GLU_INSIDE)
                gluDisk(q, 0, radius, 24, 1)
                glTranslatef(0, 0, b.height)
                gluQuadricOrientation(q, GLU_OUTSIDE)
                gluDisk(q, 0, radius, 24, 1)
                gluDeleteQuadric(q)
                glPopMatrix()
            elif b.corner_radius > 0 and any(b.rounded_front_corners):
                self._draw_rounded_box(b.width, b.depth, b.height, b.corner_radius,
                                       b.rounded_front_corners)
            else:
                self._draw_box(b.width, b.depth, b.height)
            glPopMatrix()

        def draw_slide_holes(b):
            glPushMatrix()
            _apply_board_transform(b)
            for h in b.holes:
                glPushMatrix()
                glTranslatef(h.x - b.pos[0], h.y - b.pos[1], h.z - b.pos[2])
                self._draw_hole(h.direction, h.diameter, h.depth, h.through)
                glPopMatrix()
            glPopMatrix()

        def draw_grooves(b):
            glPushAttrib(GL_ENABLE_BIT | GL_CURRENT_BIT | GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDepthMask(GL_FALSE)
            glPushMatrix()
            _apply_board_transform(b)
            for groove in b.grooves:
                depth = groove.get('depth', 0)
                if groove['kind'] == 'manual_cutout_guide':
                    y, z = groove['y'], groove['z']
                    span_y, span_z = groove['span_y'], groove['span_z']
                    frame = 1.0
                    face_x = b.width - 0.2 if groove['face'] == '+x' else -0.3
                    for pos, size in (
                        ((face_x, y, z), (0.5, span_y, frame)),
                        ((face_x, y, z + span_z - frame), (0.5, span_y, frame)),
                        ((face_x, y, z), (0.5, frame, span_z)),
                        ((face_x, y + span_y - frame, z), (0.5, frame, span_z)),
                    ):
                        glPushMatrix()
                        glTranslatef(*pos)
                        glColor4f(1, 0.05, 0.05, 0.65)
                        self._draw_box(*size)
                        glPopMatrix()
                    continue
                if groove['kind'] == 'ventilation_cut_guide':
                    for x1, y1, x2, y2 in routable_guide_rectangles(b, groove):
                        if groove['face'] == '-y':
                            pos = (x1, -0.3, y1)
                            size = (x2-x1, depth+0.3, y2-y1)
                        else:
                            pos = (x1, y1, b.height-depth)
                            size = (x2-x1, y2-y1, depth+0.3)
                        glPushMatrix()
                        glTranslatef(*pos)
                        glColor4f(1, 0.05, 0.05, 0.65)
                        self._draw_box(*size)
                        glPopMatrix()
                    continue
                if groove['kind'] in ('back_rabbet', 'drawer_bottom'):
                    pos = (groove['x'], b.depth-depth, groove['z'])
                    size = (groove['span_x'], depth+0.3, groove['span_z'])
                elif groove['kind'] == 'ventilation_grille':
                    pos = (groove['x'], -0.3, groove['z'])
                    size = (groove['span_x'], depth + 0.6, groove['span_z'])
                elif groove['kind'] == 'led_wire':
                    pos = (groove['x'], groove['y'], b.height-depth if groove['face'] == '+z' else -0.3)
                    size = (groove['span_x'], groove['span_y'], depth+0.3)
                elif groove['kind'] == 'led' and groove['face'] in ('+z', '-z'):
                    y1 = max(0, groove['offset']-groove['width']/2)
                    y2 = min(b.depth, groove['offset']+groove['width']/2)
                    pos = (groove.get('x', 0), y1, b.height-depth if groove['face'] == '+z' else -0.3)
                    size = (groove.get('span_x', b.width), y2-y1, depth+0.3)
                else:
                    continue
                glPushMatrix()
                glTranslatef(*pos)
                glColor4f(1, 0.05, 0.05, 0.65)
                self._draw_box(*size)
                glPopMatrix()
            glPopMatrix()
            glPopAttrib()

        def draw_joint_holes(b, filter_partner=None):
            glPushMatrix()
            _apply_board_transform(b)
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
                draw_body(boards[i], ALPHA_INACTIVE)
            draw_body(boards[sel], ALPHA_SELECTED)
            glDepthMask(GL_TRUE)
            glDisable(GL_BLEND)
            for b in boards:
                draw_slide_holes(b)
            draw_joint_holes(boards[sel])
            for i in others:
                draw_joint_holes(boards[i], filter_partner=sel_name)

        for b in boards:
            draw_grooves(b)
        self._draw_grid()

    def _draw_textured_face(self, board, alpha):
        """Draw a project image on the front face of a preview board."""
        texture_id = self._texture_ids.get(board.texture)
        if texture_id is None:
            path = Path(board.texture)
            if not path.is_absolute():
                path = Path(__file__).parent / path
            image = QImage(str(path)).convertToFormat(QImage.Format.Format_RGBA8888)
            if image.isNull():
                return
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width(), image.height(), 0,
                         GL_RGBA, GL_UNSIGNED_BYTE,
                         image.constBits().asstring(image.sizeInBytes()))
            self._texture_ids[board.texture] = texture_id
        glPushAttrib(GL_ENABLE_BIT | GL_CURRENT_BIT | GL_COLOR_BUFFER_BIT)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glColor4f(1, 1, 1, alpha)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex3f(0, 0, 0)
        glTexCoord2f(1, 1); glVertex3f(board.width, 0, 0)
        glTexCoord2f(1, 0); glVertex3f(board.width, 0, board.height)
        glTexCoord2f(0, 0); glVertex3f(0, 0, board.height)
        glEnd()
        glPopAttrib()

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

    def _draw_rounded_box(self, w, d, h, radius, rounded):
        """Draw a board with optional rounded front-left and front-right corners."""
        left, right = rounded
        r = min(radius, w / 2, d)
        outline = [(0, d)]
        if left:
            outline.append((0, r))
            for step in range(1, 9):
                angle = math.pi + step * math.pi / 16
                outline.append((r + r * math.cos(angle), r + r * math.sin(angle)))
        else:
            outline.append((0, 0))
        if right:
            outline.append((w - r, 0))
            for step in range(1, 9):
                angle = -math.pi / 2 + step * math.pi / 16
                outline.append((w - r + r * math.cos(angle), r + r * math.sin(angle)))
        else:
            outline.append((w, 0))
        outline.append((w, d))

        glNormal3f(0, 0, 1); glBegin(GL_POLYGON)
        for x, y in outline: glVertex3f(x, y, h)
        glEnd()
        glNormal3f(0, 0, -1); glBegin(GL_POLYGON)
        for x, y in reversed(outline): glVertex3f(x, y, 0)
        glEnd()
        glBegin(GL_QUADS)
        for index, (x1, y1) in enumerate(outline):
            x2, y2 = outline[(index + 1) % len(outline)]
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            glNormal3f(dy / length, -dx / length, 0)
            glVertex3f(x1, y1, 0); glVertex3f(x2, y2, 0)
            glVertex3f(x2, y2, h); glVertex3f(x1, y1, h)
        glEnd()
        glLineWidth(1.0); glDisable(GL_LIGHTING); glColor3f(0.2, 0.15, 0.1)
        glBegin(GL_LINE_LOOP)
        for x, y in outline: glVertex3f(x, y, 0)
        glEnd(); glBegin(GL_LINE_LOOP)
        for x, y in outline: glVertex3f(x, y, h)
        glEnd(); glBegin(GL_LINES)
        for x, y in outline:
            glVertex3f(x, y, 0); glVertex3f(x, y, h)
        glEnd(); glEnable(GL_LIGHTING)

    def _draw_hole(self, direction, diameter, depth, through=False):
        surface_r = diameter / 2; tip_r = surface_r if through else 0.0; overshoot = 0.3
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
        if through:
            # The board is opaque: show the exit on its opposite face too.
            # Local +Z points into the material; step just past the exit face.
            glTranslatef(0, 0, depth + 2 * overshoot)
            gluDisk(q, 0, surface_r, 24, 1)
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
        s  = self._scene_size * 0.8; step = 100
        bk = self._grid_back_y   # back wall: max Y of furniture
        lx = self._grid_left_x   # left wall: min X of furniture
        r  = range(-int(s)//step*step, int(s)+step, step)
        glBegin(GL_LINES)
        for i in r:
            # floor (Z=0)
            glColor4f(0.35,0.40,0.55,0.25)
            glVertex3f(i,-s,0); glVertex3f(i,s,0); glVertex3f(-s,i,0); glVertex3f(s,i,0)
            # back wall (Y=back_y, XZ plane)
            glColor4f(0.30,0.48,0.36,0.25)
            glVertex3f(i,bk,-s); glVertex3f(i,bk,s); glVertex3f(-s,bk,i); glVertex3f(s,bk,i)
            # left wall (X=left_x, YZ plane)
            glColor4f(0.50,0.32,0.32,0.25)
            glVertex3f(lx,i,-s); glVertex3f(lx,i,s); glVertex3f(lx,-s,i); glVertex3f(lx,s,i)
        glEnd()
        glLineWidth(1.2); glBegin(GL_LINES)
        # axis lines at the furniture's back-left corner
        glColor4f(0.75,0.20,0.20,0.7); glVertex3f(-s,bk,0); glVertex3f(s,bk,0)   # X axis on back wall
        glColor4f(0.20,0.75,0.20,0.7); glVertex3f(lx,-s,0); glVertex3f(lx,s,0)   # Y axis on left wall
        glColor4f(0.25,0.45,0.90,0.7); glVertex3f(lx,bk,-s); glVertex3f(lx,bk,s) # Z axis at back-left corner
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
                px, py = int(e.position().x()), int(e.position().y())
                if self._suppress_click_release:
                    # The release completing a double-click must not become a
                    # separate single-click selection.
                    self._suppress_click_release = False
                elif e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    idx = self._pick_idx(px, py)
                    if idx is not None and self.model and self.model.boards[idx].movable:
                        if isinstance(self.parent(), QMainWindow):
                            self.parent()._toggle_group(self._board_group_keys[idx])
                else:
                    # Wait for Qt's double-click interval before selecting.  A
                    # double-click cancels this pending single-click below.
                    self._pending_click_pos = (px, py)
                    self._click_timer.start(QApplication.styleHints().mouseDoubleClickInterval())
        self._last_pos = None; self._press_pos = None

    def mouseDoubleClickEvent(self, e):
        """Toggle a drawer without relying on a Ctrl modifier from the VNC client."""
        if e.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(e)
            return
        self._click_timer.stop()
        self._pending_click_pos = None
        self._suppress_click_release = True
        idx = self._pick_idx(int(e.position().x()), int(e.position().y()))
        if idx is not None and self.model and self.model.boards[idx].movable:
            if isinstance(self.parent(), QMainWindow):
                self.parent()._toggle_group(self._board_group_keys[idx])

    def _finish_single_click(self):
        if self._pending_click_pos is not None:
            self._pick(*self._pending_click_pos)
        self._pending_click_pos = None

    def keyPressEvent(self, e):
        """Keep application shortcuts working while the OpenGL view has focus."""
        if isinstance(self.parent(), QMainWindow):
            self.parent().keyPressEvent(e)
            e.accept()
        else:
            super().keyPressEvent(e)

    def _pick_idx(self, px, py) -> "int | None":
        if self._mv_mat is None or not self.model:
            return None
        py_gl = self.height() - py - 1
        near = gluUnProject(px, py_gl, 0.0, self._mv_mat, self._proj_mat, self._viewport)
        far  = gluUnProject(px, py_gl, 1.0, self._mv_mat, self._proj_mat, self._viewport)
        ro = np.array(near, dtype=float)
        rd = np.array(far,  dtype=float) - ro
        n  = np.linalg.norm(rd)
        if n < 1e-9:
            return None
        rd /= n
        best_t, best_i = np.inf, None
        by_name = {b.name: b for b in self.model.boards}
        for i, target in enumerate(self.model.boards):
            b = by_name[target.motion_parent] if target.motion_parent else target
            # Rendered transform is: position → opening motion → yaw.  Transform
            # the ray by its inverse so picking follows a rotated door, not its
            # closed-position bounding box.
            point = ro - np.array(b.pos, dtype=float)
            direction = rd.copy()
            yaw = math.radians(b.yaw)
            if yaw:
                c, s = math.cos(yaw), math.sin(yaw)
                inverse_yaw = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
                point, direction = inverse_yaw @ point, inverse_yaw @ direction
            if b.movable:
                key  = self._board_group_keys[i]
                travel = self.model.max_travel if b.travel is None else b.travel
                amount = self._open_per_group.get(key, 0.0) * b.move_fraction
                if b.opening == 'lift_up':
                    pivot = np.array([0.0, b.depth, b.height])
                    point[1] += LIFT_OPEN_FRONT_CLEARANCE * amount
                    point[2] += (b.depth - LIFT_CLOSED_TOP_REVEAL) * amount
                    angle = math.radians(90 * amount)  # inverse of -90° render rotation
                    c, s = math.cos(angle), math.sin(angle)
                    inverse_motion = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
                    point = pivot + inverse_motion @ (point - pivot)
                    direction = inverse_motion @ direction
                elif b.opening in ('hinge_left', 'hinge_right'):
                    pivot = np.array([
                        b.depth - HINGE_SIDE_REVEAL if b.opening == 'hinge_left'
                        else b.width - (b.depth - HINGE_SIDE_REVEAL),
                        b.depth, 0.0,
                    ])
                    point[1] += HINGE_OPEN_FRONT_CLEARANCE * amount
                    # Inverse of the sign used by _apply_board_transform.
                    sign = 1 if b.opening == 'hinge_left' else -1
                    open_angle = math.radians(HINGE_OPEN_ANGLE * amount)
                    angle = sign * open_angle
                    c, s = math.cos(angle), math.sin(angle)
                    inverse_motion = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
                    point = pivot + inverse_motion @ (point - pivot)
                    direction = inverse_motion @ direction
                else:
                    point[1] += travel * amount
            if target.motion_parent:
                point -= np.array(target.pos) - np.array(b.pos)
                if target.yaw:
                    angle = math.radians(target.yaw)
                    c, s = math.cos(angle), math.sin(angle)
                    inverse = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
                    point, direction = inverse @ point, inverse @ direction
            t = _ray_aabb(point, direction,
                          np.zeros(3), np.array([target.width, target.depth, target.height]))
            if t is not None and target.preview_mesh:
                t = ray_mesh(point, direction, board_mesh(target)[0])
            if t is not None and t < best_t:
                best_t, best_i = t, i
        return best_i

    def _pick(self, px, py):
        best_i = self._pick_idx(px, py)
        self._selected = None if best_i == self._selected else best_i
        self.update()
        if isinstance(self.parent(), QMainWindow):
            self.parent()._update_info()

    def wheelEvent(self, e):
        self.zoom *= 1.0 + e.angleDelta().y() / 1200.0
        self.zoom = max(0.05, min(self.zoom, 20.0)); self.update()


# ── Info overlay ─────────────────────────────────────────────────────────────

def _board_info_text(board: Board, level: int) -> str:
    """Dimensions / holes text in local coordinates (x=width, y=height, depth=Y)."""
    lines = [
        f"  {board.name}",
        f"  {board.width:.1f} × {board.height:.1f} × {board.depth:.1f} mm",
        f"  (W × H × thickness)",
    ]
    if level >= 2 and (board.holes or board.joint_holes):
        lines.append("")
        lines.append("  Holes (x, y from bottom-left):")
        for h in board.holes:
            lx = h.x - board.pos[0]
            ly = h.z - board.pos[2]
            lines.append(f"   slide   x={lx:.1f}  y={ly:.1f}  ø{h.diameter:.1f}  depth={h.depth:.1f}")
        for jh in board.joint_holes:
            lx = jh.x - board.pos[0]
            ly = jh.z - board.pos[2]
            ld = jh.y - board.pos[1]
            label = "dowel" if jh.hole_type == 'dowel' else "confirmat"
            elem  = "e1" if jh.element == 1 else "e2"
            depth_info = "mid-thickness" if abs(ld - board.depth / 2) < 1.0 else f"depth={ld:.1f}"
            lines.append(f"   {label} ({elem}) → {jh.partner:<12} x={lx:.1f}  y={ly:.1f}  {depth_info}")
    return "\n".join(lines)


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, yaml_path: str):
        super().__init__()
        self._yaml_path = yaml_path
        self._last_esc  = 0.0
        self._group_open: dict[str, int] = {}  # group_key → 0–100
        self._dims_level = 0   # 0=off, 1=dimensions, 2=dimensions+holes

        self.gl = GLWidget()
        self.setCentralWidget(self.gl)

        # Dimensions overlay — top-right corner
        self._info = QLabel(self)
        self._info.setStyleSheet(
            "color: #eee; background: rgba(0,0,0,160);"
            "padding: 8px; font-family: monospace; font-size: 10pt;"
        )
        self._info.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._info.hide()

        self._load(yaml_path)
        self.showMaximized()
        self._setup_shortcuts()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reposition_info()

    def _reposition_info(self):
        self._info.adjustSize()
        margin = 10
        self._info.move(self.width() - self._info.width() - margin, margin)

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=QApplication.quit)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._open_file)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self._reload)

    def keyPressEvent(self, e):
        k   = e.key()
        mod = e.modifiers()
        Key = Qt.Key

        # Quit
        if k == Key.Key_Escape:
            now = time.monotonic()
            if now - self._last_esc < 1.0:
                QApplication.quit()
            self._last_esc = now
            return

        # Help
        if k == Key.Key_H:
            HelpDialog(self).show(); return

        # Perspective / ortho
        if k == Key.Key_P:
            self.gl.toggle_perspective(); return

        # Dimensions of selected board
        if k == Key.Key_N:
            self._cycle_dims(); return

        # Reset view
        if k == Key.Key_Home:
            self.gl.reset_view(); return

        # Axis views preserve the projection selected with P.
        if k in (Key.Key_X, Key.Key_Y, Key.Key_Z):
            self.gl.set_axis_view({Key.Key_X: 'x', Key.Key_Y: 'y', Key.Key_Z: 'z'}[k])
            return

        # Drawers: + / - (all groups simultaneously)
        if k in (Key.Key_Plus, Key.Key_Equal):
            self._adjust_all(+5); return
        if k == Key.Key_Minus:
            self._adjust_all(-5); return

        # WASD → rotate
        if k == Key.Key_W:
            self.gl.rot_x -= ROT_STEP
            self.gl.update(); return
        if k == Key.Key_S:
            self.gl.rot_x += ROT_STEP
            self.gl.update(); return
        if k == Key.Key_A:
            self.gl.rot_y -= ROT_STEP
            self.gl.update(); return
        if k == Key.Key_D:
            self.gl.rot_y += ROT_STEP
            self.gl.update(); return

        # Arrow keys
        if k not in (Key.Key_Left, Key.Key_Right, Key.Key_Up, Key.Key_Down):
            super().keyPressEvent(e); return

        if mod & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+↑/↓ → zoom
            if k == Key.Key_Up:
                self.gl.zoom = min(self.gl.zoom * (1 + ZOOM_STEP), 20.0)
            elif k == Key.Key_Down:
                self.gl.zoom = max(self.gl.zoom * (1 - ZOOM_STEP), 0.05)
        elif mod & Qt.KeyboardModifier.ShiftModifier:
            # Shift+arrows → rotate
            if k == Key.Key_Left:  self.gl.rot_y -= ROT_STEP
            if k == Key.Key_Right: self.gl.rot_y += ROT_STEP
            if k == Key.Key_Up:    self.gl.rot_x -= ROT_STEP
            if k == Key.Key_Down:  self.gl.rot_x += ROT_STEP
        else:
            # Arrows → pan
            step = PAN_STEP
            if k == Key.Key_Left:  self.gl.pan_x += step
            if k == Key.Key_Right: self.gl.pan_x -= step
            if k == Key.Key_Up:    self.gl.pan_z -= step
            if k == Key.Key_Down:  self.gl.pan_z += step

        self.gl.update()

    # ── Dimensions overlay ────────────────────────────────────────────────────

    def _cycle_dims(self):
        self._dims_level = (self._dims_level + 1) % 3
        self._update_info()

    def _update_info(self):
        if self._dims_level == 0 or not self.gl.model:
            self._info.hide(); return
        model = self.gl.model
        sel   = self.gl._selected

        lines = []
        if model.slide_model:
            lines.append(f"  Slide: {model.slide_model}   NL = {model.slide_nl} mm")
            lines.append("")

        if sel is None:
            lines.append("  (click a board to see dimensions)")
        else:
            lines.append(_board_info_text(model.boards[sel], self._dims_level))

        self._info.setText("\n".join(lines))
        self._reposition_info()
        self._info.show()

    # ── File ──────────────────────────────────────────────────────────────────

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open furniture model",
            str(Path(self._yaml_path).parent),
            "YAML (*.yaml *.yml)",
        )
        if path:
            self._load(path)

    def _reload(self):
        self._load(self._yaml_path)

    def _load(self, path: str):
        try:
            with open(path) as f:
                keys = _yaml.safe_load(f).keys()
            if 'desk_drawer_wall' in keys:
                model = load_desk_drawer_wall(path)
            elif 'kitchen_tall_unit' in keys:
                model = load_kitchen_tall_unit(path)
            elif 'carcass' in keys:
                model = load_komoda(path)
            else:
                model = load_drawer(path)
            self._yaml_path = path
            self._group_open = {}
            self.gl.load_model(model)
            self.setWindowTitle(f"Meblarz — {Path(path).name}")
            if model.machining_issues:
                self.statusBar().showMessage(
                    f'Podgląd dostępny. Eksport zablokowany — braki obróbki: {len(model.machining_issues)} (szczegóły po najechaniu).')
                self.statusBar().setToolTip('\n'.join(
                    f'{issue["reason"]} Elementy: {", ".join(issue["boards"])}'
                    for issue in model.machining_issues))
            else:
                self.statusBar().clearMessage()
                self.statusBar().setToolTip('')
        except Exception as exc:
            QMessageBox.critical(self, "Load error", str(exc))

    def _toggle_group(self, key: str):
        cur = self._group_open.get(key, 0)
        self._group_open[key] = 0 if cur > 50 else 100
        self.gl.animate_group(key, self._group_open[key] / 100.0)

    def _adjust_all(self, delta: int):
        if not self.gl.model:
            return
        keys = {k for k, b in zip(self.gl._board_group_keys, self.gl.model.boards) if b.movable}
        for key in keys:
            pct = max(0, min(100, self._group_open.get(key, 0) + delta))
            self._group_open[key] = pct
            self.gl.set_open_group(key, pct / 100.0, _repaint=False)
        self.gl.update()


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
    terminal = TerminalInput(win)
    try:
        sys.exit(app.exec())
    finally:
        terminal.close()


if __name__ == '__main__':
    main()
