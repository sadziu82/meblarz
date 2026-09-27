"""Common storage-shelf depth policy, measured from the carcass front plane."""
import math


def default_shelf_setback(root):
    value = float(root.get('shelf_front_setback', 10))
    if not math.isfinite(value) or value < 0:
        raise ValueError('shelf_front_setback must be a finite, non-negative distance')
    return value


def shelf_geometry(carcass_depth, config, default_setback=10, rear_clearance=0):
    available = carcass_depth - rear_clearance
    if 'front_setback' in config:
        setback = float(config['front_setback'])
        depth = available - setback
    elif 'depth' in config:
        requested = float(config['depth'])
        if not math.isfinite(requested) or requested <= 0 or requested > carcass_depth:
            raise ValueError('Shelf depth must fit the carcass')
        depth = min(requested, available)
        setback = available - depth
    else:
        setback = default_setback
        depth = available - setback
    if not all(math.isfinite(v) for v in (setback, depth)) or setback < 0 or depth <= 0:
        raise ValueError('Shelf front_setback must leave positive shelf depth')
    return setback, depth
