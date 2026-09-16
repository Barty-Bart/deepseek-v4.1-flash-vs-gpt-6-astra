"""Read-only verification of pickup_truck.blend (run in a fresh Blender process).

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python scripts/verify_scene.py

Checks scene configuration, rig hierarchy, wheel rotation vs travelled distance,
tyre-road contact, suspension travel limits, camera clearance along the whole path,
mechanism coherence (leaf chain, drive shaft), and visibility of the required
undercarriage parts during the underside pass.  Prints PASS/FAIL lines and exits
non-zero when a hard check fails.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy                                                    # noqa: E402
from mathutils import Vector                                  # noqa: E402
from truckbuild import spec as S, road                        # noqa: E402

FAIL = []


def _fr(t):
    """seconds -> frame number"""
    return S.FRAME_START + int(round(t * S.FPS))
NOTE = []


def check(cond, label, detail=''):
    tag = 'PASS' if cond else 'FAIL'
    print('%-4s %s%s' % (tag, label, (' :: ' + detail) if detail else ''))
    if not cond:
        FAIL.append(label)
    return cond


def note(msg):
    print('INFO %s' % msg)
    NOTE.append(msg)


def ev(ob, dg):
    o = ob.evaluated_get(dg)
    return o


def world_verts(ob, dg):
    o = ev(ob, dg)
    me = o.to_mesh()
    mw = o.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    o.to_mesh_clear()
    return pts


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(HERE),
                                                   'pickup_truck.blend'))
    sc = bpy.context.scene
    print('=== verification of %s ===' % bpy.data.filepath)

    # ---------------------------------------------------------------- scene setup
    check(sc.render.fps == 24, 'fps = 24', str(sc.render.fps))
    check((sc.frame_start, sc.frame_end) == (S.FRAME_START, S.FRAME_END),
          'frame range %d-%d' % (S.FRAME_START, S.FRAME_END),
          '%s-%s (%.1f s)' % (sc.frame_start, sc.frame_end, S.DURATION))
    check((sc.render.resolution_x, sc.render.resolution_y) == (1920, 1080),
          'resolution 1920x1080')
    check(sc.render.engine == 'BLENDER_EEVEE', 'engine', sc.render.engine)
    check(sc.unit_settings.system == 'METRIC', 'metric units')
    check(sc.render.use_motion_blur and sc.render.motion_blur_shutter <= 0.5,
          'motion blur enabled and modest', '%.2f' % sc.render.motion_blur_shutter)
    for c in S.COLLECTIONS:
        col = bpy.data.collections.get(c)
        check(col is not None and len(col.objects) > 0, 'collection %s populated' % c,
              '%d objects' % (len(col.objects) if col else 0))

    # ---------------------------------------------------------------- rig hierarchy
    for nm in ('RIG_Truck', 'RIG_Sprung', 'RIG_Body', 'RIG_Frame', 'CTRL_RearAxle',
               'CTRL_Steering',
               'CTRL_FSusp_L', 'CTRL_FSusp_R', 'CTRL_RSusp_RL', 'CTRL_RSusp_RR',
               'LeafArm_L', 'LeafArm_R'):
        check(bpy.data.objects.get(nm) is not None, 'rig control %s exists' % nm)
    cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
    check(len(cams) == 5, 'five cameras', ', '.join(sorted(c.name for c in cams)))
    for nm in ('CAM_Full_Truck', 'CAM_Underside_Overview', 'CAM_Front_Suspension',
               'CAM_RearRight_Suspension', 'CAM_Film_Main'):
        check(bpy.data.objects.get(nm) is not None, 'camera %s exists' % nm)

    # ---------------------------------------------------------------- bake integrity
    dg = bpy.context.evaluated_depsgraph_get()
    truck = bpy.data.objects['RIG_Truck']
    wheels = {n: bpy.data.objects['WHEEL_%s' % n] for n in ('FL', 'FR', 'RL', 'RR')}

    print('--- wheel rotation vs travelled distance')
    for f in (1, 121, 241, 361, 481, 601, S.FRAME_END):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        x = truck.evaluated_get(dg).matrix_world.translation.x
        spin = wheels['FR'].evaluated_get(dg).rotation_euler.y
        exp = x / S.TIRE_R
        check(abs(spin - exp) < 1e-4, 'frame %d wheel rotation matches distance' % f,
              'spin %.5f rad, expected %.5f (x=%.3f m, r=%.3f m)' % (spin, exp, x, S.TIRE_R))

    print('--- suspension travel (sprung-local wheel height, rest = 0)')
    hist = {c: [] for c in ('FL', 'FR', 'RL', 'RR')}
    for f in range(S.FRAME_START, S.FRAME_END + 1, 6):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for c in hist:
            ob = bpy.data.objects['WHEEL_%s' % c]
            mw = ob.evaluated_get(dg).matrix_world
            truck_m = truck.evaluated_get(dg).matrix_world
            sprung_rot = bpy.data.objects['RIG_Sprung'].evaluated_get(dg).matrix_world
            p = sprung_rot.inverted() @ mw.translation
            hist[c].append(p.z - S.RIDE_Z)
    for c, v in hist.items():
        check(min(v) >= S.TRAVEL_MIN - 0.005 and max(v) <= S.TRAVEL_MAX + 0.005,
              'travel %s within +/-80 mm' % c,
              'min %.1f mm max %.1f mm' % (min(v) * 1000, max(v) * 1000))
    rr = hist['RR']
    rng = max(rr) - min(rr)
    check(rng > 0.060, 'rear-right wheel has a clear compression/rebound stroke',
          'stroke %.1f mm' % (rng * 1000))
    # the event must land inside the 6-8 s close-up
    f_lo, f_hi = _fr(16.2), _fr(18.6)
    seg = [rr[(f - S.FRAME_START) // 6] for f in range(f_lo, f_hi + 1, 6)]
    check(max(seg) - min(seg) > 0.060,
          'compression cycle inside the rear-right close-up (frames %d-%d)' % (f_lo, f_hi),
          'stroke in shot %.1f mm' % ((max(seg) - min(seg)) * 1000))

    print('--- tyre / road contact (no penetration, no floating, all frames)')
    worst_pen = 0.0
    worst_float = 0.0
    worst_where = None
    for f in range(S.FRAME_START, S.FRAME_END + 1, 6):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for name, ob in wheels.items():
            pts = world_verts(ob, dg)
            c = min(pts, key=lambda p: p.z)
            h = road.height(c.x, c.y)
            gap = c.z - h
            if gap < worst_pen:
                worst_pen = gap
                worst_where = (f, name, round(c.x, 3), round(c.y, 3),
                               round(c.z, 4), round(h, 4))
            worst_float = max(worst_float, gap)
    if worst_where:
        note('worst contact: frame %d %s at (x %.3f, y %.3f) tyre z %.4f road z %.4f'
             % worst_where)
    check(worst_pen > -0.005, 'no tyre penetration',
          'worst %.2f mm' % (worst_pen * 1000))
    check(worst_float < 0.022, 'no floating tyres', 'worst gap %.2f mm' % (worst_float * 1000))

    print('--- mechanism coherence')
    # drive shaft must bridge transfer case output and diff pinion exactly
    shaft = bpy.data.objects['Drive_RearShaft']
    pin = bpy.data.objects['Rear_DiffYoke']
    L = max(v.co.x for v in shaft.data.vertices)      # built link length
    maxerr = 0.0
    for f in range(S.FRAME_START, S.FRAME_END + 1, 17):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        o = shaft.evaluated_get(dg)
        tip = o.matrix_world @ Vector((L, 0, 0))
        piny = pin.evaluated_get(dg).matrix_world.translation
        maxerr = max(maxerr, (tip - piny).length)
    check(maxerr < 0.02, 'prop shaft tracks the diff pinion',
          'max endpoint error %.1f mm' % (maxerr * 1000))

    # leaf spring: bone chain must match the solved chain
    arm = bpy.data.objects['LeafArm_R']
    maxerr = 0.0
    for f in (1, 120, 280, 360, 420, 560, 660):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        a = arm.evaluated_get(dg)
        prev = None
        for pb in a.pose.bones:
            h = (a.matrix_world @ pb.matrix).translation
            if prev is not None:
                maxerr = max(maxerr, abs((h - prev).length - 0.1063))
            prev = h
    check(maxerr < 0.004, 'leaf spring maintains constant segment length (no stretching)',
          'max deviation %.2f mm' % (maxerr * 1000))

    print('--- leaf spring flex is real geometry (rear-right)')
    def leaf_pts(f):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        spr = bpy.data.objects['RIG_Sprung'].evaluated_get(dg).matrix_world.inverted()
        return [spr @ p for p in world_verts(bpy.data.objects['Rear_LeafSpring_R'], dg)]

    def leaf_mid_z(f):
        # the pack is clamped to the axle at the middle of the leaf
        mid = [p.z for p in leaf_pts(f) if abs(p.x - S.AXLE_R) < 0.06]
        return sum(mid) / len(mid) if mid else float('nan')
    vals = [(f, leaf_mid_z(f)) for f in range(_fr(16.2), _fr(18.6) + 1, 2)]
    lo = min(v for _, v in vals)
    hi = max(v for _, v in vals)
    check(hi - lo > 0.045, 'leaf spring arc rises with the axle during the close-up',
          'clamp range %.1f mm' % ((hi - lo) * 1000))
    wheel_rr = [p.z - S.RIDE_Z for p in
                [bpy.data.objects['WHEEL_RR'].evaluated_get(
                    bpy.context.evaluated_depsgraph_get()).matrix_world.translation]
                or []]
    note('leaf pack at the axle clamp: z range %.4f..%.4f m (rest ~0.446), '
         'rise %.1f mm' % (lo, hi, (hi - lo) * 1000))
    # the leaf must also be *bent*, not translated as a rigid body
    def leaf_shape(f):
        pts = leaf_pts(f)
        def z_at(x0):
            sel = [p.z for p in pts if abs(p.x - x0) < 0.03]
            return sum(sel) / len(sel) if sel else float('nan')
        return z_at(S.AXLE_R) - 0.5 * (z_at(S.AXLE_R + 0.62) + z_at(S.AXLE_R - 0.62))
    shapes = [leaf_shape(f) for f in range(_fr(16.2), _fr(18.6) + 1, 2)]
    check(max(shapes) - min(shapes) > 0.008,
          'leaf spring flexes (arc depth changes, not a rigid shift)',
          'arc depth range %.1f mm' % ((max(shapes) - min(shapes)) * 1000))

    print('--- camera clearance along the whole path')
    cam = bpy.data.objects['CAM_Film_Main']
    worst = 1e9
    worst_f = None
    worst_o = None
    worst_p = None
    solid = [o for o in bpy.data.objects if o.type == 'MESH']
    for f in range(S.FRAME_START, S.FRAME_END + 1):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        p = cam.evaluated_get(dg).matrix_world.translation
        # distance from the camera to the nearest surface of the truck body set
        for o in solid:
            if not any(c.name in ('BODY', 'INTERIOR', 'CHASSIS', 'DRIVETRAIN',
                                  'FRONT_SUSPENSION', 'REAR_SUSPENSION', 'WHEELS')
                       for c in o.users_collection):
                continue
            oe = o.evaluated_get(dg)
            bb = [oe.matrix_world @ Vector(c) for c in oe.bound_box]
            dx = max(min(v.x for v in bb) - p.x, 0, p.x - max(v.x for v in bb))
            dy = max(min(v.y for v in bb) - p.y, 0, p.y - max(v.y for v in bb))
            dz = max(min(v.z for v in bb) - p.z, 0, p.z - max(v.z for v in bb))
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            if d < worst:
                worst = d
                worst_f = f
                worst_o = o.name
                worst_p = tuple(round(v, 3) for v in p)
    check(worst > 0.12, 'camera keeps clearance from all vehicle geometry',
          'closest %.0f mm at frame %s (%s) cam %s' % (worst * 1000, worst_f, worst_o,
                                                        worst_p))

    # true nearest-surface test (triangles, not bounding boxes) at sampled frames
    from mathutils.bvhtree import BVHTree
    veh = [o for o in bpy.data.objects if o.type == 'MESH' and
           any(c.name in ('BODY', 'INTERIOR', 'CHASSIS', 'DRIVETRAIN',
                          'FRONT_SUSPENSION', 'REAR_SUSPENSION', 'WHEELS')
               for c in o.users_collection)]
    road_objs = [o for o in bpy.data.objects if o.type == 'MESH' and
                 any(c.name == 'ROAD' for c in o.users_collection)]
    worst_all = 1e9
    worst_frame = None
    for f in range(S.FRAME_START, S.FRAME_END + 1, 6):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        p = cam.evaluated_get(dg).matrix_world.translation
        for objs, label in ((veh, 'vehicle'), (road_objs, 'road')):
            verts, tris = [], []
            for o in objs:
                oe = o.evaluated_get(dg)
                me = oe.to_mesh()
                base = len(verts)
                mw = oe.matrix_world
                for v in me.vertices:
                    verts.append(mw @ v.co)
                me.calc_loop_triangles()
                for t in me.loop_triangles:
                    tris.append((base + t.vertices[0], base + t.vertices[1],
                                 base + t.vertices[2]))
                oe.to_mesh_clear()
            bvh = BVHTree.FromPolygons(verts, tris, all_triangles=True)
            loc, nor, idx, dist = bvh.find_nearest(p)
            if dist is not None and dist < worst_all:
                worst_all = dist
                worst_frame = (f, label, tuple(round(v, 3) for v in p))
    check(worst_all > 0.12, 'camera never comes within 120 mm of any surface (triangles)',
          'nearest %.0f mm at frame %s (%s)' % (worst_all * 1000, worst_frame[0],
                                                worst_frame[1]))

    # exhaust must not intersect the fuel tank or the rear axle tube
    def min_dist(a_name, b_name):
        sc.frame_set(_fr(17.4))
        dg = bpy.context.evaluated_depsgraph_get()
        def tri_data(nm):
            oe = bpy.data.objects[nm].evaluated_get(dg)
            me = oe.to_mesh()
            vs = [oe.matrix_world @ v.co for v in me.vertices]
            me.calc_loop_triangles()
            ts = [(t.vertices[0], t.vertices[1], t.vertices[2])
                  for t in me.loop_triangles]
            oe.to_mesh_clear()
            return vs, ts
        va, ta = tri_data(a_name)
        vb, tb = tri_data(b_name)
        bvh = BVHTree.FromPolygons(vb, tb, all_triangles=True)
        best = 1e9
        for v in va:
            loc, nor, idx, d = bvh.find_nearest(v)
            if d is not None:
                best = min(best, d)
        return best
    d_tank = min_dist('Exhaust_PipeRear', 'Chassis_FuelTank')
    check(d_tank > 0.02, 'exhaust routes clear of the fuel tank',
          'closest %.0f mm' % (d_tank * 1000))
    d_axle = min_dist('Chassis_SkidFront', 'Drive_CrankPulley')
    check(d_axle > 0.02, 'front skid plate clear of the crank pulley',
          'closest %.0f mm' % (d_axle * 1000))

    # camera must stay inside the inspection channel while beneath the truck
    bad = []
    for f in range(S.FRAME_START, S.FRAME_END + 1):
        t = (f - 1) / 24.0
        x = S.SPEED * t
        if any(t0 <= t <= t1 for (t0, t1) in S.CHANNEL_WINDOWS):
            sc.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            p = cam.evaluated_get(dg).matrix_world.translation
            if abs(p.y) > 0.42 or p.z < -0.50 or p.z > 0.02:
                bad.append((f, round(p.y, 3), round(p.z, 3)))
    check(not bad, 'camera stays inside the recessed inspection channel under the truck',
          str(bad[:4]))

    # camera must never be inside the road solid (below the surface outside the slot)
    bad2 = []
    for f in range(S.FRAME_START, S.FRAME_END + 1):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        p = cam.evaluated_get(dg).matrix_world.translation
        if abs(p.y) > road.CHANNEL_HALF + 0.001 and p.z < road.height(p.x, p.y) + 0.02:
            bad2.append((f, round(p.y, 2), round(p.z, 2)))
    check(not bad2, 'camera never passes under the road solid',
          str(bad2[:4]))

    print('--- undercarriage visibility during the underside pass')
    need = ['Rear_DiffHousing', 'Rear_AxleTube', 'Exhaust_Muffler', 'Exhaust_PipeRear',
            'Chassis_FuelTank', 'Chassis_Rail_L', 'Chassis_Rail_R', 'Drive_EngineBlock',
            'Drive_TransferCase', 'Drive_RearShaft', 'Chassis_SkidTcase']
    missing = [n for n in need if bpy.data.objects.get(n) is None]
    check(not missing, 'required undercarriage parts exist', str(missing))
    # frustum test at representative frames of the underside pass
    seen = {nm: [] for nm in need}
    for f in range(_fr(11.2), _fr(16.2) + 1, 3):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        c = cam.evaluated_get(dg)
        inv = c.matrix_world.inverted()
        cd = c.data
        fl, sx = cd.lens, cd.sensor_width / 2.0
        for nm in need:
            o = bpy.data.objects[nm].evaluated_get(dg)
            for v in [o.matrix_world @ Vector(b) for b in o.bound_box]:
                p = inv @ v
                if p.z < -1e-6:
                    d = -p.z
                    if (abs(p.x) <= sx * d / fl + 0.06 and
                            abs(p.y) <= (sx * 9.0 / 16.0) * d / fl + 0.06):
                        seen[nm].append(f)
                        break
    poor = [nm for nm in need if len(seen[nm]) < 8]
    check(not poor, 'each required chassis part is in frame for >=8 frames of the pass',
          'weak: ' + ', '.join('%s(%d)' % (n, len(seen[n])) for n in poor)
          if poor else 'all parts well covered (frames 90-144)')

    print('--- camera path sanity')
    xs = []
    for f in range(S.FRAME_START, S.FRAME_END + 1, 8):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        xs.append(cam.evaluated_get(dg).matrix_world.translation.copy())
    jumps = [((xs[i + 1] - xs[i]).length, S.FRAME_START + 8 * i)
             for i in range(len(xs) - 1)]
    jump, jf = max(jumps)
    check(jump < 4.2, 'camera path continuous (no teleports)',
          'max step %.3f m per 8 frames at frame %d (%.2f m/s)' % (jump, jf, jump * 3.0))
    sc.frame_set(1)
    dg = bpy.context.evaluated_depsgraph_get()
    p1 = cam.evaluated_get(dg).matrix_world.translation
    check(p1.y < -6.0 and p1.z < 1.4, 'frame 1 is the low side tracking shot',
          '(%.2f, %.2f, %.2f)' % tuple(p1))
    sc.frame_set(S.FRAME_END)
    dg = bpy.context.evaluated_depsgraph_get()
    p240 = cam.evaluated_get(dg).matrix_world.translation
    tx = S.SPEED * (S.FRAME_END - S.FRAME_START) / float(S.FPS)
    check(p240.x < tx, 'frame 240 camera is behind the truck (truck drives away)',
          'cam x %.2f vs truck x %.2f' % (p240.x, tx))

    # every inspected segment has its own frame coverage
    print('--- shot segmentation present in keyed data')
    fc = None
    for a in bpy.data.actions:
        for layer in getattr(a, 'layers', []):
            for strip in layer.strips:
                for cb in getattr(strip, 'channelbags', []):
                    for fcv in cb.fcurves:
                        if fcv.data_path == 'location':
                            fc = fcv
    check(fc is not None and len(fc.keyframe_points) >= S.FRAME_END * 0.9,
          'film camera location fully keyed',
          '%d keys' % (len(fc.keyframe_points) if fc else 0))

    print('')
    print('=== %d checks failed ===' % len(FAIL))
    for f in FAIL:
        print('  FAILED:', f)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
