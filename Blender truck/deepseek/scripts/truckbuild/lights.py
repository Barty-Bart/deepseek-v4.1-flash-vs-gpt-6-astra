"""Soft daylight, grounded shadows, lit inspection channel and restrained set dressing."""
import math
import bpy
from mathutils import Vector
from . import util as U


def build(colls, mats, reg):
    L = colls['LIGHTS']
    sd = bpy.data.lights.new('LIGHT_Sun', 'SUN')
    sd.energy = 4.6
    sd.angle = math.radians(4.5)
    sd.color = (1.0, 0.965, 0.925)
    sun = bpy.data.objects.new('LIGHT_Sun', sd)
    L.objects.link(sun)
    sun.location = (6.0, 8.0, 12.0)
    U.aim(sun, Vector((-0.55, -0.35, -1.0)), 'Z', 'Y')

    def area(name, loc, target, energy, size, color=(1.0, 1.0, 1.0), spread=None):
        d = bpy.data.lights.new(name, 'AREA')
        d.energy = energy
        d.color = color
        d.shape = 'RECTANGLE'
        d.size = size[0]
        d.size_y = size[1]
        if spread is not None:
            d.spread = spread
        ob = bpy.data.objects.new(name, d)
        L.objects.link(ob)
        ob.location = loc
        U.aim(ob, Vector(target) - Vector(loc), 'Z', 'Y')
        return ob

    area('LIGHT_Fill_Sky', (-9.0, -11.0, 9.0), (1.0, 0.0, 0.8), 1500.0, (14.0, 14.0),
         (0.84, 0.90, 1.0))
    area('LIGHT_Fill_Ground', (4.0, -12.0, 0.6), (0.5, 0.0, 0.7), 320.0, (16.0, 3.0),
         (0.92, 0.92, 0.88))
    area('LIGHT_Rim', (-14.0, 3.0, 4.0), (0.0, 0.0, 1.0), 620.0, (8.0, 6.0),
         (1.0, 0.93, 0.84))
    for i, x in enumerate(range(-10, 39, 7)):
        area('LIGHT_Channel_%02d' % i, (x, -0.10, -0.42), (x + 0.4, -0.05, 0.75),
             90.0, (2.0, 0.5), (1.0, 0.97, 0.93), spread=math.radians(120.0))
    area('LIGHT_RearRight', (-2.0, -4.2, 2.6), (-1.8, -0.7, 0.5), 260.0, (3.0, 3.0),
         (0.98, 0.97, 0.96))
    area('LIGHT_FrontLeft', (5.5, 3.4, 2.2), (1.8, 0.0, 0.9), 260.0, (3.0, 3.0))
    reg.put('lights', [o for o in L.objects])
    return L


def build_props(colls, mats):
    C, M = colls['ROAD'], mats
    for i, x in enumerate(range(-24, 137, 8)):
        for side in (1, -1):
            U.box('ROAD_Barrier_%02d_%s' % (i, 'L' if side > 0 else 'R'),
                  (2.2, 0.55, 0.85), (x, side * 6.4, 0.42), C, M['concrete'],
                  bev=0.030, segments=2)
    for i, x in enumerate(range(-20, 137, 10)):
        for side in (1, -1):
            tag = 'L' if side > 0 else 'R'
            U.cylinder('ROAD_Post_%02d_%s' % (i, tag), 0.045, 1.05,
                       (x, side * 3.1, 0.52), coll=C, mat=M['steel'], verts=10)
            U.box('ROAD_PostTop_%02d_%s' % (i, tag), (0.10, 0.10, 0.14),
                  (x, side * 3.1, 1.10), C, M['marking'], bev=0.010)
    for i, (x, y, w, d, h) in enumerate(((70, -78, 30, 20, 10), (110, -64, 22, 28, 13),
                                         (150, 72, 24, 22, 9), (196, -58, 34, 24, 12),
                                         (238, 24, 26, 32, 15), (48, 66, 20, 18, 8),
                                         (14, -70, 22, 20, 9))):
        U.box('ROAD_DistantBlock_%d' % i, (w, d, h), (x, y, h / 2.0), C,
              M['structure'], bev=0.20, segments=2)
    # low earth berms close the horizon instead of hard walls
    for i, (x0, x1, yy) in enumerate(((-40, 160, -34.0), (-40, 160, 34.0))):
        U.box('ROAD_Berm_%d' % i, (x1 - x0, 9.0, 1.5), ((x0 + x1) / 2, yy, 0.75),
              C, M['berm'], bev=0.60, segments=3)
    return C
