"""The 28 second film camera plus four named inspection cameras.

Camera keys are (time, position, target, focal length).  Positions are either
absolute world points ('A') or relative to the moving truck ('R', offset from the
truck origin).  Relative keys keep the 3 m/s tracking speed regardless of the
smoothstep easing applied to the offsets, so tracking shots never stall.
"""
import math
import bpy
from mathutils import Vector
from . import spec as S
from . import util as U


def _P(kind, x, y, z):
    return (kind, Vector((x, y, z)))


# time, position, target, focal length (mm)
KEYS = [
    # --- 0.0-3.0 s : low side-profile tracking shot, whole truck in frame -------
    (0.00, _P('R', 3.10, -7.10, 1.02), _P('R', 0.10, 0.00, 0.88), 40.0),
    (1.40, _P('R', 1.70, -7.45, 1.06), _P('R', -0.10, -0.05, 0.86), 40.0),
    (3.00, _P('R', 0.60, -7.25, 0.94), _P('R', 0.20, 0.00, 0.90), 40.0),
    # --- 3.0-5.8 s : arc round the front three-quarter, descend into the channel -
    (3.60, _P('R', 3.10, -6.30, 1.30), _P('R', 0.40, 0.00, 0.95), 38.0),
    (4.20, _P('R', 5.00, -3.90, 1.72), _P('R', 0.10, -0.10, 0.95), 34.0),
    (4.80, _P('R', 6.10, -1.60, 1.30), _P('R', 0.40, -0.10, 0.90), 30.0),
    (5.30, _P('R', 5.30, -0.40, 0.45), _P('R', 1.20, 0.00, 0.88), 28.0),
    (5.80, _P('R', 4.90, -0.06, -0.22), _P('R', 2.00, -0.05, 0.78), 28.0),
    # --- 5.8-9.6 s : the truck overtakes the camera; scan the underside ---------
    (6.60, _P('R', 3.10, -0.04, -0.20), _P('R', 1.60, -0.05, 0.75), 26.0),
    (7.60, _P('R', 0.90, -0.06, -0.18), _P('R', 0.40, -0.12, 0.68), 24.0),
    (8.60, _P('R', -1.20, -0.06, -0.17), _P('R', -0.80, -0.28, 0.62), 25.0),
    (9.60, _P('R', -3.20, -0.05, -0.18), _P('R', -1.60, -0.36, 0.58), 26.0),
    # --- 9.6-11.2 s : settle behind the rear axle ------------------------------
    (10.40, _P('R', -3.20, -0.04, -0.24), _P('R', -1.60, -0.10, 0.52), 22.0),
    (11.20, _P('R', -3.20, -0.04, -0.26), _P('R', -1.60, -0.05, 0.50), 20.0),
    # --- 11.2-16.2 s : centred undercarriage hold (5 s) ------------------------
    (13.00, _P('R', -3.05, -0.02, -0.25), _P('R', -1.55, -0.02, 0.50), 22.0),
    (14.60, _P('R', -3.15, 0.02, -0.24), _P('R', -1.52, -0.06, 0.52), 23.0),
    (16.20, _P('R', -3.30, 0.04, -0.25), _P('R', -1.60, -0.08, 0.50), 24.0),
    # --- 16.2-18.6 s : rear-right leaf-spring close-up, held steady ------------
    (16.45, _P('R', -3.35, -0.10, 0.24), _P('R', -1.70, -0.45, 0.50), 26.0),
    (16.70, _P('R', -3.45, -0.62, 0.30), _P('R', -1.90, -0.55, 0.50), 34.0),
    (16.95, _P('R', -3.90, -1.25, 0.38), _P('R', -1.95, -0.66, 0.50), 40.0),
    (17.80, _P('R', -3.88, -1.22, 0.40), _P('R', -1.95, -0.66, 0.50), 42.0),
    (18.60, _P('R', -3.90, -1.25, 0.38), _P('R', -1.95, -0.66, 0.50), 40.0),
    # --- 18.6-21.4 s : back under the tail, then glide forward along the drivetrain
    (18.80, _P('R', -3.58, -0.75, 0.45), _P('R', -2.10, -0.55, 0.48), 34.0),
    (19.05, _P('R', -3.25, -0.34, 0.16), _P('R', -1.90, -0.35, 0.52), 30.0),
    (19.30, _P('R', -3.00, -0.28, -0.08), _P('R', -1.70, -0.30, 0.55), 28.0),
    (19.60, _P('R', -2.40, -0.22, -0.10), _P('R', -1.20, -0.20, 0.60), 28.0),
    (20.40, _P('R', -1.30, -0.18, -0.12), _P('R', 0.10, -0.15, 0.62), 26.0),
    (21.40, _P('R', -0.10, -0.12, -0.12), _P('R', 0.80, -0.10, 0.62), 26.0),
    # --- 21.4-23.0 s : glide back to the rear axle -----------------------------
    (22.30, _P('R', -1.00, -0.20, -0.10), _P('R', -0.60, -0.20, 0.58), 26.0),
    (23.00, _P('R', -1.78, -0.26, -0.06), _P('R', -1.60, -0.62, 0.48), 24.0),
    # --- 23.0-25.8 s : look along the axle at the inside of the rear-right wheel
    (24.20, _P('R', -1.78, -0.26, -0.06), _P('R', -1.62, -0.78, 0.45), 24.0),
    (25.00, _P('R', -1.80, -0.28, -0.05), _P('R', -1.60, -0.80, 0.46), 25.0),
    (25.80, _P('R', -1.82, -0.28, -0.05), _P('R', -1.60, -0.78, 0.45), 26.0),
    # --- 25.8-28.0 s : truck clears the camera and drives away -----------------
    (26.70, _P('R', -2.05, -0.30, -0.05), _P('R', -1.60, -0.35, 0.62), 28.0),
    (27.10, _P('A', 77.30, -0.85, 0.45), _P('R', -2.55, -0.10, 0.72), 30.0),
    (27.70, _P('A', 77.45, -2.30, 1.05), _P('R', -2.60, 0.00, 0.85), 34.0),
    (28.00, _P('A', 77.60, -3.10, 1.55), _P('R', -2.60, 0.00, 0.90), 32.0),
]


def _val(p, truck_x):
    kind, v = p
    return Vector(v) + Vector((truck_x, 0.0, 0.0)) if kind == 'R' else Vector(v)


def sample(t, truck_x):
    """Return (position, target, focal length) at time t seconds."""
    keys = KEYS
    if t <= keys[0][0]:
        tk, p, tg, fl = keys[0]
        return _val(p, truck_x), _val(tg, truck_x), fl
    if t >= keys[-1][0]:
        tk, p, tg, fl = keys[-1]
        return _val(p, truck_x), _val(tg, truck_x), fl
    for i in range(len(keys) - 1):
        t0, p0, g0, f0 = keys[i]
        t1, p1, g1, f1 = keys[i + 1]
        if t0 <= t <= t1:
            w = U.smoothstep((t - t0) / (t1 - t0))
            a = _val(p0, truck_x).lerp(_val(p1, truck_x), w)
            b = _val(g0, truck_x).lerp(_val(g1, truck_x), w)
            return a, b, f0 + (f1 - f0) * w
    tk, p, tg, fl = keys[-1]
    return _val(p, truck_x), _val(tg, truck_x), fl


def make_camera(name, loc, target, lens, coll, clip_start=0.06, clip_end=600.0,
                dof=False, aperture=11.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.sensor_width = 36.0
    cam_data.clip_start = clip_start
    cam_data.clip_end = clip_end
    if dof:
        cam_data.dof.use_dof = True
        cam_data.dof.aperture_fstop = aperture
        cam_data.dof.focus_distance = (Vector(target) - Vector(loc)).length
    ob = bpy.data.objects.new(name, cam_data)
    coll.objects.link(ob)
    ob.location = loc
    U.aim(ob, Vector(target) - Vector(loc), '-Z', 'Y')
    ob.rotation_mode = 'XYZ'
    return ob


def build(colls, mats, reg):
    C = colls['CAMERAS']
    film = make_camera('CAM_Film_Main', (0, 0, 2.0), (0, 0, 0.9), 40.0, C, dof=True,
                       aperture=11.0)
    reg.put('cam_film', film)
    inspections = [
        ('CAM_Full_Truck', (3.60, -6.60, 2.45), (0.05, 0.0, 0.95), 45.0, 0.10, False),
        ('CAM_Underside_Overview', (3.40, 0.0, -0.34), (-0.60, 0.0, 0.62), 28.0, 0.05, False),
        ('CAM_Front_Suspension', (2.90, -0.42, -0.25), (1.55, -0.62, 0.55), 35.0, 0.05, False),
        ('CAM_RearRight_Suspension', (-3.90, -1.25, 0.38), (-1.95, -0.66, 0.50), 40.0, 0.05,
         False),
    ]
    for (nm, loc, tgt, lens, cs, dof) in inspections:
        ob = make_camera(nm, loc, tgt, lens, C, clip_start=cs, dof=dof)
        reg.put(nm, ob)
    return film


def bake(film, reg, i, f, truck_x, t):
    """Per-frame key insertion for the film camera (called by the anim baker)."""
    pos, tgt, lens = sample(t, truck_x)
    film.location = tuple(pos)
    U.aim(film, tgt - pos, '-Z', 'Y')
    film.rotation_mode = 'XYZ'
    film.data.lens = lens
    film.data.dof.focus_distance = max(0.5, (tgt - pos).length)
    film.keyframe_insert('location', frame=f)
    film.keyframe_insert('rotation_euler', frame=f)
    film.data.keyframe_insert('lens', frame=f)
    film.data.keyframe_insert('dof.focus_distance', frame=f)
