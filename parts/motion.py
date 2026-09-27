"""Shared movement grouping for preview and construction visibility."""
import re


def movable_group(board) -> str:
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
