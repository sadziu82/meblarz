"""Input behaviour without requiring an OpenGL render context or a real TTY."""
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
import pytest
from PyQt6.QtCore import Qt, QEvent, QPointF, QTimer
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication, QMainWindow
from viewer import GLWidget, MainWindow, TerminalInput


@pytest.fixture(scope='module')
def app():
    import os
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication.instance() or QApplication([])
    yield app


def view():
    gl = SimpleNamespace(rot_x=17, rot_y=23, pan_x=10, pan_z=20, zoom=1,
                         _axis_view=None, _axis_centered=False, update=Mock())
    gl.set_axis_view = MethodType(GLWidget.set_axis_view, gl)
    return gl


@pytest.mark.parametrize('axis,key,positive,negative', [
    ('x', Qt.Key.Key_X, (0, -90), (0, 90)),
    ('y', Qt.Key.Key_Y, (0, 0), (0, 180)),
    ('z', Qt.Key.Key_Z, (90, 0), (-90, 0)),
])
@pytest.mark.parametrize('perspective', [False, True])
def test_axis_keys_alternate_without_changing_projection(axis, key, positive, negative, perspective):
    gl = view()
    gl.perspective = perspective
    window = SimpleNamespace(gl=gl)
    for expected in (positive, negative, positive):
        MainWindow.keyPressEvent(window, QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))
        assert (gl.rot_x, gl.rot_y) == expected
        assert gl.perspective is perspective
        assert (gl.pan_x, gl.pan_z) == (0, 0)


def test_terminal_fragmented_arrow_and_wasd_use_same_shortcuts():
    gl = view()
    window = SimpleNamespace(gl=gl)
    window.keyPressEvent = MethodType(MainWindow.keyPressEvent, window)
    terminal = TerminalInput.__new__(TerminalInput)
    terminal.window, terminal._buffer, terminal._escape_timer = window, bytearray(), Mock()
    terminal._buffer.extend(b'\x1b[')
    terminal._process_buffer()
    assert (gl.pan_x, gl.rot_x, gl.rot_y) == (10, 17, 23)
    terminal._buffer.extend(b'D')  # Left arrow, completed by a later stdin read.
    terminal._process_buffer()
    assert gl.pan_x > 10 and (gl.rot_x, gl.rot_y) == (17, 23)
    terminal._buffer.extend(b'aw')
    terminal._process_buffer()
    assert gl.rot_x < 17 and gl.rot_y < 23
    terminal._buffer.extend(b'ds')
    terminal._process_buffer()
    assert (gl.rot_x, gl.rot_y, gl.zoom) == (17, 23, 1)
    assert not terminal._buffer


def mouse_event(kind):
    return QMouseEvent(kind, QPointF(10, 20), QPointF(10, 20),
                       Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)


def test_double_click_cancels_single_click_and_release(app):
    parent = QMainWindow()
    parent._toggle_group = Mock()
    gl = SimpleNamespace(_press_pos=None, _last_pos=None, _pending_click_pos=None,
                         _suppress_click_release=False, _click_timer=QTimer(),
                         _pick=Mock(), _pick_idx=Mock(return_value=0),
                         parent=lambda: parent, _board_group_keys=['drawer'],
                         model=SimpleNamespace(boards=[SimpleNamespace(movable=True)]))
    gl._click_timer.setSingleShot(True)
    GLWidget.mousePressEvent(gl, mouse_event(QEvent.Type.MouseButtonPress))
    GLWidget.mouseReleaseEvent(gl, mouse_event(QEvent.Type.MouseButtonRelease))
    assert gl._click_timer.isActive()
    gl._pick.assert_not_called()
    GLWidget.mouseDoubleClickEvent(gl, mouse_event(QEvent.Type.MouseButtonDblClick))
    gl._press_pos = QPointF(10, 20)
    GLWidget.mouseReleaseEvent(gl, mouse_event(QEvent.Type.MouseButtonRelease))
    GLWidget._finish_single_click(gl)
    gl._pick.assert_not_called()
    assert not gl._click_timer.isActive()
    parent._toggle_group.assert_called_once_with('drawer')
    # A later ordinary click still selects exactly once.
    GLWidget.mousePressEvent(gl, mouse_event(QEvent.Type.MouseButtonPress))
    GLWidget.mouseReleaseEvent(gl, mouse_event(QEvent.Type.MouseButtonRelease))
    gl._click_timer.stop()
    GLWidget._finish_single_click(gl)
    gl._pick.assert_called_once_with(10, 20)
    parent.close()


def test_board_info_identifies_lift_bores():
    from parts.drawer import Board, Hole
    from viewer import _board_info_text
    board = Board('flap', 700, 350, 18, (0, 0, 0))
    board.holes.append(Hole(40, 18, 200, 2.5, 10, '+y', 'gas_lift_mount'))
    text = _board_info_text(board, 2)
    assert 'gas_lift_mount' in text
    assert 'slide' not in text
