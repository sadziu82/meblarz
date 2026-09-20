"""Optional, schematic monitor placement; not a manufacturer mounting template."""
from parts.drawer import Board, Hole
import math


def append_monitor_setup(boards, cfg):
    if not cfg.get('enabled', False):
        return []
    shelf = next((b for b in boards if b.name == 'desk_low_shelf'), None)
    if shelf is None:
        raise ValueError('monitor_setup requires desk.low_shelf.enabled')
    x = shelf.pos[0] + shelf.width / 2 + float(cfg.get('offset_x', 0))
    y = shelf.pos[1] + shelf.depth - float(cfg.get('rear_offset', 60))
    z = shelf.pos[2] + shelf.height
    diameter = float(cfg.get('trial_hole_diameter', 10))
    pole = float(cfg.get('pole_width', 35))
    pole_h = float(cfg.get('pole_height', 450))
    base = float(cfg.get('base_size', 80))
    center_z = z + float(cfg.get('vesa_height', 280))
    monitor = cfg.get('monitor', {})
    w, h, d = (float(monitor.get(k, v)) for k, v in
               [('width', 614), ('height', 364), ('depth', 48)])
    gap = float(cfg.get('monitor_gap', 10))
    angle = float(cfg.get('inward_angle', 0))
    if not 0 <= angle <= 30:
        raise ValueError('Monitor inward_angle must be between 0 and 30 degrees')
    projected_width = w * math.cos(math.radians(angle)) + d * math.sin(math.radians(angle))
    screen_x = x
    if 'left_clearance' in cfg:
        left_clearance = float(cfg['left_clearance'])
        if left_clearance < 0:
            raise ValueError('Monitor left_clearance must be nonnegative')
        screen_x = shelf.pos[0] + left_clearance + projected_width + gap/2
    reach = float(cfg.get('forward_reach', 100))
    if min(diameter, pole, pole_h, base, w, h, d, reach) <= 0 or gap < 0:
        raise ValueError('Invalid monitor setup dimensions')
    if diameter >= base or not (shelf.pos[0] + base/2 <= x <= shelf.pos[0]+shelf.width-base/2
            and shelf.pos[1]+base/2 <= y <= shelf.pos[1]+shelf.depth-base/2):
        raise ValueError('Monitor mount base must fit on the low shelf')
    if not z + 60 <= center_z <= z + pole_h - 20:
        raise ValueError('VESA height must fit the monitor pole')
    bottom = center_z - float(monitor.get('vesa_from_bottom', 181))
    if bottom <= z or screen_x-projected_width-gap/2 < shelf.pos[0] or screen_x+projected_width+gap/2 > shelf.pos[0]+shelf.width:
        raise ValueError('Monitors must fit above the low shelf')
    bridge = next(b for b in boards if b.name == 'module_bridge')
    if max(bottom+h, z+pole_h) > bridge.pos[2]:
        raise ValueError('Monitor setup collides with the overhead shelf')
    shelf.holes.append(Hole(x, y, z, diameter, shelf.height, '+z', 'monitor_trial', True))
    black = (0.12, 0.12, 0.14, 1.0)
    def visual(name, width, height, depth, pos, color=black, yaw=0):
        boards.append(Board('monitor_preview_' + name, width, height, depth, pos,
                            color, movable=False, fabrication=False, yaw=yaw))
    visual('base', base, 6, base, (x-base/2, y-base/2, z))
    visual('pole', pole, pole_h, pole, (x-pole/2, y-pole/2, z+6))
    visual('trial_bolt', diameter, shelf.height+12, diameter,
           (x-diameter/2, y-diameter/2, shelf.pos[2]-6))
    # Two equal links per arm approximate the three pivots. The user supplied
    # maximum VESA span; the individual link split remains schematic.
    arm_length = float(cfg.get('max_vesa_span', 735)) / 2
    if arm_length <= 0:
        raise ValueError('Monitor max_vesa_span must be positive')
    def arm_segment(name, start, end):
        dx, dy = end[0]-start[0], end[1]-start[1]
        length = math.hypot(dx, dy)
        yaw = math.degrees(math.atan2(dy, dx))
        visual(name, length, 30, 20,
               (start[0]+10*dy/length, start[1]-10*dx/length, center_z-15), yaw=yaw)
    half_span = (projected_width+gap)/2
    for index, cx in enumerate((screen_x-half_span, screen_x+half_span)):
        face_y = y-reach-6-d
        yaw = angle if index == 0 else -angle
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        cy = face_y + d/2
        def rotated_pos(dx, dy, at_z):
            return (cx+c*dx-s*dy, cy+s*dx+c*dy, at_z)
        end_x, end_y, _ = rotated_pos(0, d/2+6, center_z)
        dx, dy = end_x-x, end_y-y
        distance = math.hypot(dx, dy)
        if not 0 < distance <= arm_length:
            raise ValueError('Monitor position exceeds arm reach; reduce forward_reach or change placement')
        bend = math.sqrt(max(0, (arm_length/2)**2-(distance/2)**2))
        elbows = [(x+dx/2+sign*(-dy/distance)*bend,
                   y+dy/2+sign*(dx/distance)*bend) for sign in (-1, 1)]
        elbow = max(elbows, key=lambda point: point[1])  # fold towards the rear
        arm_segment(f'arm_{index}_inner', (x, y), elbow)
        arm_segment(f'arm_{index}_outer', elbow, (end_x, end_y))
        visual(f'vesa_{index}', 114, 114, 6, rotated_pos(-57, d/2, center_z-57), yaw=yaw)
        visual(f'display_{index}', w, h, d, rotated_pos(-w/2, -d/2, bottom), yaw=yaw)
        visual(f'screen_{index}', w-16, h-26, 1, rotated_pos(-w/2+8, -d/2-1, bottom+18),
               (0.12, 0.25, 0.34, 1.0), yaw=yaw)
    return [
        'PRÓBA: ART L-02N na małej półce, dwa iiyama XUB2797QSNP-B1. '
        'Geometria uchwytu jest uproszczona; podstawa i ramiona mają wymiary założone.',
        f'Próbny otwór Ø{diameter:g} mm NIE jest eksportowany do wierceń ani DXF. '
        'Mocowanie przelotowe i adapter ART wymagają potwierdzenia przed wykonaniem.',
        'Obrys monitora 614 × 364 × 48 mm zaokrąglono w górę z rysunku iiyama '
        '(613,5 × 364 × 47,5 mm).',
    ]
