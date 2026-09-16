"""Geometry inspection aid - NOT a render of the film.

Casts rays with mathutils.bvhtree against the evaluated meshes and writes small
shaded PNGs so the model can be inspected without using any Blender render engine
(no render settings, samples or output of the deliverable are touched).

    Blender --background --factory-startup --python scripts/qa_views.py
"""
import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy                                                     # noqa: E402
from mathutils import Vector                                   # noqa: E402
from mathutils.bvhtree import BVHTree                          # noqa: E402

W, H = 760, 428
LIGHT = Vector((0.45, -0.62, 0.65)).normalized()
UP2 = Vector((-0.35, -0.25, 0.90)).normalized()


def write_png(path, w, h, rgb):
    raw = b''.join(b'\x00' + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 6))
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as fh:
        fh.write(png)


def collect(dg):
    verts = []
    tris = []
    cols = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        oe = ob.evaluated_get(dg)
        me = oe.to_mesh()
        if not me.polygons:
            oe.to_mesh_clear()
            continue
        mw = oe.matrix_world
        base = len(verts)
        palette = {'BODY': (0.22, 0.62, 0.32), 'INTERIOR': (0.72, 0.55, 0.35),
                   'CHASSIS': (0.78, 0.26, 0.22), 'DRIVETRAIN': (0.90, 0.58, 0.16),
                   'FRONT_SUSPENSION': (0.30, 0.55, 0.95),
                   'REAR_SUSPENSION': (0.68, 0.36, 0.92),
                   'WHEELS': (0.80, 0.80, 0.82), 'ROAD': (0.42, 0.41, 0.39)}
        cn = None
        for c in ob.users_collection:
            if c.name in palette:
                cn = c.name
                break
        base_col = palette.get(cn, (0.85, 0.15, 0.75))
        cols_per_mat = [base_col]
        if not cols_per_mat:
            cols_per_mat = [(0.5, 0.5, 0.5)]
        me.calc_loop_triangles()
        for v in me.vertices:
            verts.append(mw @ v.co)
        for t in me.loop_triangles:
            tris.append((base + t.vertices[0], base + t.vertices[1],
                         base + t.vertices[2]))
            idx = t.material_index if t.material_index < len(cols_per_mat) else 0
            cols.append(cols_per_mat[idx])
        oe.to_mesh_clear()
    return verts, tris, cols


def render(name, cam_loc, target, lens, verts, tris, cols, bvh, scene_bg=0.42):
    up = Vector((0, 0, 1))
    fwd = (Vector(target) - Vector(cam_loc)).normalized()
    right = fwd.cross(up).normalized()
    upv = right.cross(fwd).normalized()
    sx = 36.0 / 2.0
    aspect = W / float(H)
    sy = sx / aspect
    img = bytearray(W * H * 3)
    zbuf = [1e9] * (W * H)
    nbuf = [None] * (W * H)
    origin = Vector(cam_loc)
    for j in range(H):
        py = (1.0 - 2.0 * (j + 0.5) / H) * sy
        for i in range(W):
            px = (2.0 * (i + 0.5) / W - 1.0) * sx
            d = (fwd * lens + right * px + upv * py).normalized()
            hit = bvh.ray_cast(origin, d)
            if hit[0] is None:
                c = (scene_bg, scene_bg * 1.05, scene_bg * 1.2)
            else:
                loc, nor, idx, dist = hit
                base = cols[idx] if idx < len(cols) else (0.5, 0.5, 0.5)
                # inspection shading: two-sided so undersides read as clearly as tops
                lam = abs(nor.dot(LIGHT))
                fill = abs(nor.dot(UP2))
                f = 0.55 + 0.85 * lam + 0.30 * fill
                fog = 1.0 / (1.0 + 0.014 * max(0.0, dist - 5.0) ** 1.5)
                c = tuple(min(1.0, base[k] * f) * fog + scene_bg * (1 - fog)
                          for k in range(3))
            o = (j * W + i) * 3
            img[o] = int(min(1.0, c[0]) ** 0.62 * 255)
            img[o + 1] = int(min(1.0, c[1]) ** 0.62 * 255)
            img[o + 2] = int(min(1.0, c[2]) ** 0.62 * 255)
            if hit[0] is not None:
                zbuf[j * W + i] = hit[3]
                nbuf[j * W + i] = hit[1]
    # cheap depth/normal edge overlay so silhouettes and panel breaks read clearly
    for j in range(1, H - 1):
        for i in range(1, W - 1):
            k = j * W + i
            z0 = zbuf[k]
            edge = False
            for (dx, dy) in ((1, 0), (0, 1)):
                k2 = (j + dy) * W + (i + dx)
                z1 = zbuf[k2]
                if abs(z0 - z1) > 0.012 * max(1.0, min(z0, z1)):
                    edge = True
                    break
                n0, n1 = nbuf[k], nbuf[k2]
                if n0 is None or n1 is None:
                    if n0 is not n1:
                        edge = True
                        break
                elif n0.dot(n1) < 0.86:
                    edge = True
                    break
            if edge:
                o = k * 3
                for q in range(3):
                    img[o + q] = int(img[o + q] * 0.25)
    out = os.path.join(ROOT, 'qa')
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, name + '.png')
    write_png(path, W, H, img)
    print('wrote', path)


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, 'pickup_truck.blend'))
    sc = bpy.context.scene
    views = [
        ('v1_full_threequarter_f1', 1, (3.60, -6.60, 2.45), (0.05, 0.0, 0.95), 45.0),
        ('v2_side_low_f20', 20, None, None, 40.0),
        ('v3_underside_f118', 118, None, None, 24.0),
        ('v4_rear_right_f170', 170, None, None, 42.0),
        ('v5_rear_threequarter_f236', 236, None, None, 35.0),
    ]
    film = bpy.data.objects['CAM_Film_Main']
    for (name, frame, loc, tgt, lens) in views:
        sc.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        verts, tris, cols = collect(dg)
        bvh = BVHTree.FromPolygons(verts, tris, all_triangles=True)
        if loc is None:
            ce = film.evaluated_get(dg)
            loc = tuple(ce.matrix_world.translation)
            m = ce.matrix_world.to_3x3()
            tgt = tuple(ce.matrix_world.translation + (m @ Vector((0, 0, -1))) * 4.0)
            lens = ce.data.lens
        render(name, loc, tgt, lens, verts, tris, cols, bvh)
        print('  frame %d: %d verts, %d tris' % (frame, len(verts), len(tris)))


if __name__ == '__main__':
    main()
