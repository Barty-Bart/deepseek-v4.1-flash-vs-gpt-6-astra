"""Deterministic kinematic bake of the whole film: vehicle travel, body motion,
suspension mechanisms, wheel rotation and the camera path.

Nothing here is physics-based: every quantity is computed from the road profile and
the linkage geometry, then keyframed at every frame so the saved scene plays back
exactly as verified.
"""
import math
import bpy
from mathutils import Vector, Matrix, Euler
from . import spec as S
from . import util as U
from . import road
from . import suspension as SUS

CORNERS = ('FL', 'FR', 'RL', 'RR')
WX = {'FL': S.AXLE_F, 'FR': S.AXLE_F, 'RL': S.AXLE_R, 'RR': S.AXLE_R}
WY = {'FL': S.WHEEL_Y, 'FR': -S.WHEEL_Y, 'RL': S.WHEEL_Y, 'RR': -S.WHEEL_Y}


# ------------------------------------------------------------------ filtering
def biquad_lp(series, fc, fs=24.0):
    w0 = 2.0 * math.pi * fc / fs
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2.0 * 0.7071)
    b0, b1, b2 = (1 - cw) / 2, 1 - cw, (1 - cw) / 2
    a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
    out = []
    z1 = z2 = 0.0
    for v in series:
        y = b0 * v + z1
        z1 = b1 * v - a1 * y + z2
        z2 = b2 * v - a2 * y
        out.append(y)
    out = list(reversed(out))
    z1 = z2 = 0.0
    res = []
    for v in out:
        y = b0 * v + z1
        z1 = b1 * v - a1 * y + z2
        z2 = b2 * v - a2 * y
        res.append(y)
    return list(reversed(res))


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ main bake
def bake(scene, reg, colls, cam=None):
    n = S.FRAME_END - S.FRAME_START + 1
    frames = list(range(S.FRAME_START, S.FRAME_END + 1))
    tt = [(f - S.FRAME_START) / float(S.FPS) for f in frames]
    xx = [S.SPEED * t for t in tt]

    wz = {c: [road.wheel_center_z(xx[i] + WX[c], WY[c]) for i in range(n)]
          for c in CORNERS}
    rise = {c: [wz[c][i] - S.TIRE_R for i in range(n)] for c in CORNERS}
    # sprung-mass response: heavily filtered, 42 % of the wheel input (spring share)
    resp = {c: [0.42 * v for v in biquad_lp(rise[c], 1.30)] for c in CORNERS}

    truck = reg.require('rig_truck')
    sprung = reg.require('rig_sprung')

    travel_hist = {c: [] for c in CORNERS}
    for i in range(n):
        m = sum(resp[c][i] for c in CORNERS) / 4.0
        dF = 0.5 * (resp['FL'][i] + resp['FR'][i])
        dR = 0.5 * (resp['RL'][i] + resp['RR'][i])
        dL = 0.5 * (resp['FL'][i] + resp['RL'][i])
        dRt = 0.5 * (resp['FR'][i] + resp['RR'][i])
        pitch = -math.asin(max(-0.05, min(0.05, (dF - dR) / S.WHEELBASE)))
        roll = math.asin(max(-0.05, min(0.05, (dL - dRt) / S.TRACK)))

        truck.location = (xx[i], 0.0, 0.0)
        sprung.location = (0.0, 0.0, m)
        sprung.rotation_mode = 'XYZ'
        sprung.rotation_euler = (roll, pitch, 0.0)

        Msp = (Matrix.Translation((xx[i], 0.0, m))
               @ Euler((roll, pitch, 0.0), 'XYZ').to_matrix().to_4x4())
        inv = Msp.inverted()
        local_z = {}
        for c in CORNERS:
            lp = inv @ Vector((xx[i] + WX[c], WY[c], wz[c][i]))
            local_z[c] = lp.z
            travel_hist[c].append(lp.z - S.RIDE_Z)

        steer = math.radians(1.2) * math.sin(2.0 * math.pi * tt[i] / 19.0)
        sctrl = reg.require('ctrl_steering')
        sctrl.rotation_mode = 'XYZ'
        sctrl.rotation_euler = (0.0, 0.0, steer)
        mFL = SUS.apply_front(reg, 'L', 1, local_z['FL'], steer)
        mFR = SUS.apply_front(reg, 'R', -1, local_z['FR'], steer)

        zL = local_z['RL']
        zR = local_z['RR']
        rr = SUS.apply_rear(reg, zL, zR)
        axle_M = rr['axle_M']

        for tag, side, z_local in (('L', 1, zL), ('R', -1, zR)):
            rc = reg.require('rctrl_' + tag)
            rc.location = (S.AXLE_R, side * S.WHEEL_Y, z_local)
            rc.rotation_mode = 'XYZ'
            rc.rotation_euler = (rr['roll'], 0.0, 0.0)

        # rear prop shaft aims from the transfer case to the diff pinion
        pin = axle_M @ reg.require('ds_rear_pinloc')
        SUS.place_link(reg.require('driveshaft_rear'), reg.require('ds_rear_base'),
                       pin, reg.require('ds_rear_len'))

        # wheel rotation consistent with travelled distance / tyre radius
        spin = xx[i] / S.TIRE_R
        for tag in ('L', 'R'):
            for kind in ('f', 'r'):
                w = reg.require('wheel_%s%s' % (kind, tag))
                w.rotation_mode = 'XYZ'
                w.rotation_euler = (0.0, spin, 0.0)

        f = frames[i]
        kf(truck, 'location', f, 0)
        kf(reg.require('ctrl_steering'), 'rotation_euler', f)
        kf(sprung, 'location', f, 2)
        kf(sprung, 'rotation_euler', f)
        for c, tag in (('FL', 'L'), ('FR', 'R')):
            ctl = reg.require('fctrl_' + tag)
            kf(ctl, 'location', f)
            kf(ctl, 'rotation_quaternion', f)
        for tag in ('L', 'R'):
            kf(reg.require('rctrl_' + tag), 'location', f)
            kf(reg.require('rctrl_' + tag), 'rotation_euler', f)
            kf(reg.require('axle_ctrl'), 'location', f)
            kf(reg.require('axle_ctrl'), 'rotation_euler', f)
        for c in CORNERS:
            kf(reg.require('wheel_f' + c[1]) if c[0] == 'F' else
               reg.require('wheel_r' + c[1]), 'rotation_euler', f)
        # mechanism parts
        for tag in ('L', 'R'):
            for k in ('front_lower_arm_', 'front_upper_arm_'):
                kf(reg.require(k + tag), 'rotation_euler', f)
            for k in ('coil_body_', 'coil_rod_', 'tierod_', 'cvshaft_'):
                kf(reg.require(k + tag), 'location', f)
                kf(reg.require(k + tag), 'rotation_quaternion', f)
            kf(reg.require('coil_spring_' + tag), 'location', f)
            kf(reg.require('coil_spring_' + tag), 'rotation_quaternion', f)
            kf(reg.require('coil_spring_' + tag), 'scale', f)
            for k in ('shock_body_', 'shock_rod_', 'shackle_'):
                kf(reg.require(k + tag), 'location', f)
                kf(reg.require(k + tag), 'rotation_quaternion', f)
            kf(reg.require('shackle_' + tag), 'scale', f)
            for h in reg.require('brakehose_' + tag):
                kf(h, 'location', f)
                kf(h, 'rotation_quaternion', f)
            for h in reg.require('rbrakehose_' + tag):
                kf(h, 'location', f)
                kf(h, 'rotation_quaternion', f)
            arm = reg.require('leaf_arm_' + tag)
            if (i % 2) == 0 or i == n - 1:
                for pb in arm.pose.bones:
                    pb.keyframe_insert('rotation_euler', frame=f)
        kf(reg.require('driveshaft_rear'), 'location', f)
        kf(reg.require('driveshaft_rear'), 'rotation_quaternion', f)
        kf(reg.require('driveshaft_rear'), 'scale', f)
        if cam is not None:
            cam(i, f, xx[i], tt[i])
    return dict(travel=travel_hist, wz=wz, resp=resp, xx=xx, tt=tt)


def kf(ob, path, frame, index=-1):
    try:
        ob.keyframe_insert(data_path=path, index=index, frame=frame)
    except Exception as exc:
        raise RuntimeError('keyframe %s.%s failed: %s' % (ob.name, path, exc))
