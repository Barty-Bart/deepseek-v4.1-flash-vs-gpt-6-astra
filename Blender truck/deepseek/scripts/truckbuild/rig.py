"""Rig hierarchy and named controls; parenting of every moving part."""
import bpy
from mathutils import Vector
from . import spec as S
from . import util as U


def build(colls, reg, body_colls):
    R = colls['RIG']
    steer = U.ensure_empty('CTRL_Steering', R, 0.30)
    U.parent(steer, U.ensure_empty('RIG_Truck', R, 0.70), keep_transform=False)
    reg.put('ctrl_steering', steer)
    truck = bpy.data.objects['RIG_Truck']
    sprung = U.ensure_empty('RIG_Sprung', R, 0.55)
    body = U.ensure_empty('RIG_Body', R, 0.45)
    frame = U.ensure_empty('RIG_Frame', R, 0.45)
    U.parent(sprung, truck)
    U.parent(body, sprung)
    U.parent(frame, sprung)
    reg.put('rig_truck', truck)
    reg.put('rig_sprung', sprung)
    reg.put('rig_body', body)
    reg.put('rig_frame', frame)

    # every BODY / INTERIOR mesh rides on the sprung mass (body-on-frame)
    for cname in ('BODY',):
        for ob in list(colls[cname].objects):
            U.parent(ob, body)
    for ob in list(colls['INTERIOR'].objects):
        U.parent(ob, body)
    for cname in ('CHASSIS', 'DRIVETRAIN'):
        for ob in list(colls[cname].objects):
            if ob.parent is not None:
                continue
            if reg.get('driveshaft_rear') is ob or reg.get('cvshaft_L') is ob or \
               reg.get('cvshaft_R') is ob:
                U.parent(ob, sprung)
            else:
                U.parent(ob, frame)
    # suspension links + armatures ride on the sprung mass; parts already bound to
    # a mechanism control (knuckle, hub, caliper, axle) keep that parent
    for cname in ('FRONT_SUSPENSION', 'REAR_SUSPENSION'):
        for ob in list(colls[cname].objects):
            if ob.parent is not None or ob.name.startswith('CTRL_'):
                continue
            U.parent(ob, sprung)
    for name in ('LeafArm_L', 'LeafArm_R'):
        arm = bpy.data.objects.get(name)
        if arm:
            U.parent(arm, sprung)
    # named suspension controls live on the sprung mass
    for key in ('fctrl_L', 'fctrl_R', 'axle_ctrl'):
        c = reg.get(key)
        if c is not None and c.parent is None:
            U.parent(c, sprung)
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        c = reg.get('fctrl_' + tag)
        if c:
            U.parent(c, sprung)
    # wheels
    for side, tag in ((1, 'L'), (-1, 'R')):
        fw = bpy.data.objects.get('WHEEL_F' + tag)
        rw = bpy.data.objects.get('WHEEL_R' + tag)
        c = reg.get('fctrl_' + tag)
        if fw is not None and c is not None:
            U.parent(fw, c)
        reg.put('wheel_f' + tag, fw)
        rc = U.ensure_empty('CTRL_RSusp_R' + tag, R, 0.26)
        rc.location = (S.AXLE_R, side * S.WHEEL_Y, S.RIDE_Z)
        U.parent(rc, sprung)
        reg.put('rctrl_' + tag, rc)
        if rw is not None:
            U.parent(rw, rc)
        reg.put('wheel_r' + tag, rw)
    return truck, sprung


def tag_props(reg):
    """Documentation-only custom properties visible in the Blender UI."""
    doc = {
        'RIG_Truck': {'role': 'vehicle travel along +X (metres)',
                      'range': 'animates 0 -> 30 m over frames 1-240'},
        'RIG_Sprung': {'role': 'sprung mass heave / pitch / roll',
                       'note': 'rigid-body fit of filtered corner road inputs'},
        'RIG_Body': {'role': 'body shell + interior parent'},
        'RIG_Frame': {'role': 'chassis + drivetrain parent'},
        'CTRL_FSusp_L': {'role': 'front-left knuckle/hub/wheel mechanism output'},
        'CTRL_FSusp_R': {'role': 'front-right knuckle/hub/wheel mechanism output'},
        'CTRL_RSusp_RL': {'role': 'rear-left wheel travel'},
        'CTRL_RSusp_RR': {'role': 'rear-right wheel travel'},
        'CTRL_RearAxle': {'role': 'rear beam axle: travel + roll'},
        'CTRL_Steering': {'role': 'steering input: rotation_euler.z in radians',
                          'note': 'rack travel = -angle * 0.30 m; drives both front knuckles'},
        'LeafArm_L': {'role': 'rear-left leaf-spring bend (bone chain)'},
        'LeafArm_R': {'role': 'rear-right leaf-spring bend (bone chain)'},
    }
    for name, props in doc.items():
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        for k, v in props.items():
            ob[k] = v
