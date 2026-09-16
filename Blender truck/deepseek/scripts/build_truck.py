"""Build the complete pickup-truck scene and animation.

Run with Blender's bundled Python:

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --factory-startup --python scripts/build_truck.py

Produces pickup_truck.blend (scene + rig + baked 10 s camera animation).
No rendering is performed in this iteration.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy                                                    # noqa: E402
from truckbuild import (util as U, spec as S, scene as SC, materials as MAT,   # noqa: E402
                        road, body, interior, chassis, drivetrain, suspension,
                        wheels, rig as RIG, anim, cameras, lights, registry as reg)


def count_fcurves():
    n = 0
    for a in bpy.data.actions:
        if hasattr(a, 'fcurves'):
            n += len(a.fcurves)
        for layer in getattr(a, 'layers', []):
            for strip in layer.strips:
                for cb in getattr(strip, 'channelbags', []):
                    n += len(cb.fcurves)
    return n


def main():
    t0 = time.time()
    print('=== pickup truck build ===')
    U.purge_scene()
    colls = SC.setup_scene()
    mats = MAT.build()
    print('[1] materials + collections')

    road.build(colls['ROAD'], mats)
    lights.build_props(colls, mats)
    print('[2] road set')

    body.build_front(colls, mats)
    body.build_fenders(colls, mats, reg)
    body.build_cab(colls, mats)
    body.build_bed(colls, mats)
    body.build_expedition(colls, mats)
    print('[3] body shell')

    interior.build(colls, mats)
    print('[4] interior')

    chassis.build(colls, mats, reg)
    drivetrain.build(colls, mats, reg)
    print('[5] chassis + drivetrain')

    suspension.build_front(colls, mats, reg)
    suspension.build_rear(colls, mats, reg)
    print('[6] suspension')

    for name, side in (('FL', 1), ('FR', -1), ('RL', 1), ('RR', -1)):
        pre = 'F' if name[0] == 'F' else 'R'
        kind = 'front' if pre == 'F' else 'rear'
        ob = wheels.build_wheel('WHEEL_' + name, colls['WHEELS'], mats,
                                flip=(side > 0))
        ax = S.AXLE_F if pre == 'F' else S.AXLE_R
        ob.location = (ax, side * S.WHEEL_Y, S.RIDE_Z)
        print('     wheel', name)
    print('[7] wheels')

    RIG.build(colls, reg, colls)
    RIG.tag_props(reg)
    print('[8] rig hierarchy')

    lights.build(colls, mats, reg)
    print('[9] lighting')

    film = cameras.build(colls, mats, reg)
    sc = bpy.context.scene
    sc.camera = film

    t1 = time.time()
    stats = anim.bake(sc, reg, colls, cam=lambda i, f, x, t: cameras.bake(film, reg, i, f, x, t))
    print('[10] animation baked in %.1f s' % (time.time() - t1))

    # summary + saved verification data
    path = os.path.join(os.path.dirname(HERE), 'pickup_truck.blend')
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=False)
    print('[11] saved %s (%.1f MB)' % (path, os.path.getsize(path) / 1e6))
    print('total build %.1f s, objects %d, fcurves %d'
          % (time.time() - t0, len(bpy.data.objects), count_fcurves()))
    with open(os.path.join(os.path.dirname(HERE), 'build_report.txt'), 'w') as fh:
        fh.write('objects %d\n' % len(bpy.data.objects))
        fh.write('actions %d\n' % len(bpy.data.actions))
        fh.write('build_seconds %.2f\n' % (time.time() - t0))
        for c in S.COLLECTIONS:
            fh.write('collection %s objects %d\n' % (c, len(colls[c].objects)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
