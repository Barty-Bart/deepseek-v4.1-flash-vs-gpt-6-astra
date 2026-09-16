"""Shared mesh, material and collection helpers for the pickup truck build.

All geometry is authored directly with bpy/bmesh data APIs (no ops-based modelling)
so the build is deterministic and reproducible in background Blender.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Euler

TAU = math.tau

# --------------------------------------------------------------------------------------
# scene / collection
# --------------------------------------------------------------------------------------

def purge_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures,
                bpy.data.curves, bpy.data.cameras, bpy.data.lights,
                bpy.data.actions, bpy.data.images):
        for b in list(blk):
            if b.users == 0:
                blk.remove(b)


def ensure_collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def link(obj, coll):
    coll.objects.link(obj)
    return obj


# --------------------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------------------

_MAT_CACHE = {}
PARTS_LAST = None


def _set_last(ob):
    global PARTS_LAST
    PARTS_LAST = ob
    return ob



def _set_in(node, names, value):
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return True
    return False


def material(name, color, rough=0.5, metal=0.0, ior=1.45, alpha=1.0,
             transmission=0.0, coat=0.0, coat_rough=0.1, spec=0.5,
             emission=None, emission_strength=0.0, sheen=0.0):
    """Create (or fetch) a simple Principled BSDF material."""
    key = name
    if key in _MAT_CACHE:
        return _MAT_CACHE[key]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (300, 0)
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    col = tuple(color) + (1.0,) if len(color) == 3 else tuple(color)
    _set_in(bsdf, ['Base Color'], col)
    _set_in(bsdf, ['Roughness'], rough)
    _set_in(bsdf, ['Metallic'], metal)
    _set_in(bsdf, ['IOR'], ior)
    _set_in(bsdf, ['Alpha'], alpha)
    _set_in(bsdf, ['Transmission Weight', 'Transmission'], transmission)
    _set_in(bsdf, ['Coat Weight', 'Clearcoat'], coat)
    _set_in(bsdf, ['Coat Roughness', 'Clearcoat Roughness'], coat_rough)
    _set_in(bsdf, ['Specular IOR Level', 'Specular'], spec)
    _set_in(bsdf, ['Sheen Weight', 'Sheen'], sheen)
    if emission is not None:
        _set_in(bsdf, ['Emission Color', 'Emission'], tuple(emission) + (1.0,) if len(emission) == 3 else tuple(emission))
        _set_in(bsdf, ['Emission Strength'], emission_strength)
    if alpha < 1.0:
        mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else mat.blend_method
    mat.diffuse_color = col
    _MAT_CACHE[key] = mat
    return mat


def noise_bump(mat, scale=40.0, strength=0.15, detail=3.0, rough_var=0.0):
    """Add a small procedural noise bump (and optional roughness variation)."""
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexNoise')
    tex.location = (-600, -200)
    tex.inputs['Scale'].default_value = scale
    if 'Detail' in tex.inputs:
        tex.inputs['Detail'].default_value = detail
    bump = nt.nodes.new('ShaderNodeBump')
    bump.location = (-300, -250)
    bump.inputs['Strength'].default_value = strength
    nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    if rough_var > 0.0:
        ramp = nt.nodes.new('ShaderNodeMapRange')
        ramp.location = (-300, 0)
        ramp.inputs['To Min'].default_value = max(0.0, bsdf.inputs['Roughness'].default_value - rough_var)
        ramp.inputs['To Max'].default_value = min(1.0, bsdf.inputs['Roughness'].default_value + rough_var)
        nt.links.new(tex.outputs['Fac'], ramp.inputs['Value'])
        nt.links.new(ramp.outputs['Result'], bsdf.inputs['Roughness'])
    return mat


# --------------------------------------------------------------------------------------
# low level mesh creation
# --------------------------------------------------------------------------------------

def _recalc(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()


def mesh_obj(name, verts, faces, coll, mat=None, smooth=False, recalc=True,
             smooth_faces=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [list(f) for f in faces])
    me.validate(verbose=False)
    if recalc:
        _recalc(me)
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    _set_last(ob)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if smooth_faces is not None:
        for i, p in enumerate(me.polygons):
            p.use_smooth = smooth_faces(i, p)
    return ob


def bm_obj(name, build, coll, mat=None, smooth=False, recalc=True):
    """Create an object from a bmesh build callback."""
    bm = bmesh.new()
    build(bm)
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    _set_last(ob)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return ob


class Builder:
    """Accumulate several primitives into one mesh with per-face material slots."""

    def __init__(self):
        self.v = []
        self.f = []
        self.m = []
        self.smooth = []

    def add(self, verts, faces, mat=0, smooth=False):
        o = len(self.v)
        self.v.extend([tuple(x) for x in verts])
        for f in faces:
            self.f.append([o + i for i in f])
            self.m.append(mat)
            self.smooth.append(smooth)
        return self

    def revolve(self, section, nseg, mat=0, rfun=None, smooth=True, yfun=None,
                offset=(0.0, 0.0, 0.0), rot=None):
        """Revolve a closed (r, y) section around the Y axis (the wheel axis)."""
        n = len(section)
        verts = []
        for j in range(nseg):
            a = TAU * j / nseg
            ca, sa = math.cos(a), math.sin(a)
            for (r, y) in section:
                rr = r if rfun is None else rfun(a, y, r)
                yy = y if yfun is None else yfun(a, y)
                verts.append((rr * ca, yy, rr * sa))
        if rot is not None:
            M = Euler(rot, 'XYZ').to_matrix()
            verts = [tuple(M @ Vector(v)) for v in verts]
        verts = [(v[0] + offset[0], v[1] + offset[1], v[2] + offset[2]) for v in verts]
        faces = []
        for j in range(nseg):
            j2 = (j + 1) % nseg
            for i in range(n):
                i2 = (i + 1) % n
                faces.append([j * n + i, j * n + i2, j2 * n + i2, j2 * n + i])
        self.add(verts, faces, mat, smooth)
        return self

    def object(self, name, coll, mats, recalc=True):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.validate(verbose=False)
        if recalc:
            _recalc(me)
        me.update()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        for m in mats:
            me.materials.append(m)
        for i, p in enumerate(me.polygons):
            if i < len(self.m):
                p.material_index = self.m[i]
                p.use_smooth = self.smooth[i]
        _set_last(ob)
        return ob


def bevel(ob, width=0.008, segments=2, angle=35.0, clamp=True):
    m = ob.modifiers.new('bevel', 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.use_clamp_overlap = clamp
    return m


def subsurf(ob, levels=1, render=2):
    m = ob.modifiers.new('subsurf', 'SUBSURF')
    m.levels = levels
    m.render_levels = render
    return m


# --------------------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------------------

def box(name, size, loc=(0, 0, 0), coll=None, mat=None, bev=0.0, segments=2,
        rot=(0, 0, 0), smooth=False):
    sx, sy, sz = size
    def build(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Euler(rot, 'XYZ').to_matrix())
        bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    ob = bm_obj(name, build, coll, mat=mat, smooth=smooth)
    if bev > 0:
        bevel(ob, bev, segments)
    return ob


def cylinder(name, radius, depth, loc=(0, 0, 0), axis='Z', coll=None, mat=None,
             verts=24, bev=0.0, cap=True, smooth=True, rot=(0, 0, 0)):
    def build(bm):
        bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=verts,
                              radius1=radius, radius2=radius, depth=depth)
    ob = bm_obj(name, build, coll, mat=mat, smooth=False)
    me = ob.data
    for p in me.polygons:
        p.use_smooth = smooth and len(p.vertices) == 4
    if axis == 'X':
        ob.rotation_euler = (0, math.pi / 2, 0)
    elif axis == 'Y':
        ob.rotation_euler = (math.pi / 2, 0, 0)
    if any(rot):
        ob.rotation_euler = Euler(rot, 'XYZ')
    ob.location = loc
    if bev > 0:
        bevel(ob, bev, 2, 40)
    return ob


def tube(name, r_out, r_in, depth, loc=(0, 0, 0), axis='Z', coll=None, mat=None,
         verts=24, rot=(0, 0, 0)):
    """Hollow tube (open ends)."""
    def build(bm):
        bmesh.ops.create_cone(bm, cap_ends=False, segments=verts,
                              radius1=r_out, radius2=r_out, depth=depth)
        inner = bmesh.ops.create_cone(bm, cap_ends=False, segments=verts,
                                      radius1=r_in, radius2=r_in, depth=depth)
        # bridge: build rings manually instead (handled below by face creation)
        for f in inner['verts']:
            pass
    # simpler: build rings by hand
    n = verts
    v = []
    for zz in (-depth / 2, depth / 2):
        for i in range(n):
            a = TAU * i / n
            v.append((r_out * math.cos(a), r_out * math.sin(a), zz))
    for zz in (-depth / 2, depth / 2):
        for i in range(n):
            a = TAU * i / n
            v.append((r_in * math.cos(a), r_in * math.sin(a), zz))
    O0, O1, I0, I1 = 0, n, 2 * n, 3 * n
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append([O0 + i, O0 + j, O1 + j, O1 + i])          # outer wall
        faces.append([I1 + i, I1 + j, I0 + j, I0 + i])          # inner wall
        faces.append([O1 + i, O1 + j, I1 + j, I1 + i])          # top rim
        faces.append([I0 + i, I0 + j, O0 + j, O0 + i])          # bottom rim
    ob = mesh_obj(name, v, faces, coll, mat=mat, recalc=True)
    for p in ob.data.polygons:
        p.use_smooth = len(p.vertices) == 4 and p.normal.z < 0.9
    if axis == 'X':
        ob.rotation_euler = (0, math.pi / 2, 0)
    elif axis == 'Y':
        ob.rotation_euler = (math.pi / 2, 0, 0)
    if any(rot):
        ob.rotation_euler = Euler(rot, 'XYZ')
    ob.location = loc
    return ob


def sphere(name, radius, loc=(0, 0, 0), coll=None, mat=None, segs=16, rings=8,
           scale=(1, 1, 1), rot=(0, 0, 0)):
    def build(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
        bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Euler(rot, 'XYZ').to_matrix())
        bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    return bm_obj(name, build, coll, mat=mat, smooth=True)


def torus(name, major, minor, loc=(0, 0, 0), coll=None, mat=None, mseg=24, nseg=10,
          rot=(0, 0, 0), arc=TAU):
    verts = []
    faces = []
    for i in range(mseg):
        u = arc * i / mseg - (0 if arc >= TAU else 0)
        cu, su = math.cos(u), math.sin(u)
        for j in range(nseg):
            v = TAU * j / nseg
            r = major + minor * math.cos(v)
            verts.append((r * cu, r * su, minor * math.sin(v)))
    closed = abs(arc - TAU) < 1e-6
    for i in range(mseg if closed else mseg - 1):
        i2 = (i + 1) % mseg
        for j in range(nseg):
            j2 = (j + 1) % nseg
            faces.append([i * nseg + j, i2 * nseg + j, i2 * nseg + j2, i * nseg + j2])
    ob = mesh_obj(name, verts, faces, coll, mat=mat, smooth=True)
    if any(rot):
        ob.rotation_euler = Euler(rot, 'XYZ')
    ob.location = loc
    return ob


# --------------------------------------------------------------------------------------
# panel / loft / strip builders (the workhorses for body and chassis panels)
# --------------------------------------------------------------------------------------

def panel(name, outline, y_in, y_out, coll, mat=None, bev=0.0, segments=2,
          closed=True, loc=(0, 0, 0)):
    """Extrude a 2D (x,z) outline along Y.

    y_in / y_out may be floats or callables f(z) -> y.  Using a linear y_out(z)
    gives a planar outer skin with tumblehome.
    """
    fi = y_in if callable(y_in) else (lambda z: y_in)
    fo = y_out if callable(y_out) else (lambda z: y_out)
    n = len(outline)
    verts = []
    for (x, z) in outline:
        verts.append((x, fi(z), z))
    for (x, z) in outline:
        verts.append((x, fo(z), z))
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    ob = mesh_obj(name, verts, faces, coll, mat=mat)
    ob.location = loc
    if bev > 0:
        bevel(ob, bev, segments)
    return ob


def loft_x(name, sections, coll, mat=None, cap_front=True, cap_back=True,
           bev=0.0, segments=2, loc=(0, 0, 0), smooth=False):
    """Loft closed cross-sections along X.

    sections: list of (x, [(y,z), ...]) all with the same point count, listed in a
    consistent rotational order.
    """
    m = len(sections[0][1])
    verts = []
    for (x, pts) in sections:
        for (y, z) in pts:
            verts.append((x, y, z))
    faces = []
    for s in range(len(sections) - 1):
        a = s * m
        b = (s + 1) * m
        for i in range(m):
            j = (i + 1) % m
            faces.append([a + i, a + j, b + j, b + i])
    if cap_front:
        faces.append(list(range(m - 1, -1, -1)))
    if cap_back:
        off = (len(sections) - 1) * m
        faces.append([off + i for i in range(m)])
    ob = mesh_obj(name, verts, faces, coll, mat=mat, smooth=smooth)
    ob.location = loc
    if bev > 0:
        bevel(ob, bev, segments)
    return ob


def loft_pts(name, sections, coll, mat=None, cap_start=True, cap_end=True,
             closed_section=True, bev=0.0, segments=2, smooth=False, loc=(0, 0, 0)):
    """General loft: sections is a list of equal-length lists of 3D points."""
    m = len(sections[0])
    verts = []
    for sec in sections:
        for p in sec:
            verts.append(tuple(p))
    faces = []
    span = m if closed_section else m - 1
    for s in range(len(sections) - 1):
        a = s * m
        b = (s + 1) * m
        for i in range(span):
            j = (i + 1) % m
            faces.append([a + i, a + j, b + j, b + i])
    if cap_start and closed_section:
        faces.append(list(range(m - 1, -1, -1)))
    if cap_end and closed_section:
        off = (len(sections) - 1) * m
        faces.append([off + i for i in range(m)])
    ob = mesh_obj(name, verts, faces, coll, mat=mat, smooth=smooth)
    ob.location = loc
    if bev > 0:
        bevel(ob, bev, segments)
    return ob


def solidify(ob, thickness, offset=-1.0):
    m = ob.modifiers.new('solidify', 'SOLIDIFY')
    m.thickness = thickness
    m.offset = offset
    return m


def sweep_ribbon(name, path, half_w, half_t, coll, mat=None, width_axis=(0, 1, 0),
                 bev=0.0, segments=1):
    """Sweep a rectangular cross-section along a 3D polyline lying in a plane.

    half_w is along width_axis, half_t is the in-plane normal thickness.
    """
    P = [Vector(p) for p in path]
    W = Vector(width_axis).normalized()
    verts = []
    for i, p in enumerate(P):
        if i == 0:
            t = (P[1] - P[0])
        elif i == len(P) - 1:
            t = (P[-1] - P[-2])
        else:
            t = (P[i + 1] - P[i - 1])
        t.normalize()
        n = t.cross(W).normalized()
        verts += [p + W * half_w + n * half_t,
                  p - W * half_w + n * half_t,
                  p - W * half_w - n * half_t,
                  p + W * half_w - n * half_t]
    faces = []
    for i in range(len(P) - 1):
        a = i * 4
        b = (i + 1) * 4
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append([a + k, a + k2, b + k2, b + k])
    faces.append([0, 1, 2, 3])
    o = (len(P) - 1) * 4
    faces.append([o + 3, o + 2, o + 1, o + 0])
    ob = mesh_obj(name, verts, faces, coll, mat=mat)
    if bev > 0:
        bevel(ob, bev, segments)
    return ob


def ensure_empty(name, coll, size=0.25):
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, None)
        coll.objects.link(ob)
    ob.empty_display_type = 'PLAIN_AXES'
    ob.empty_display_size = size
    return ob


def ensure_armature(name, coll):
    ob = bpy.data.objects.get(name)
    if ob is not None:
        return ob
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    coll.objects.link(ob)
    return ob


def enter_edit(ob):
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')


def exit_edit(ob):
    bpy.ops.object.mode_set(mode='OBJECT')
    ob.select_set(False)


def helix(name, radius, wire_r, length, turns, coll, mat=None, segs=10, nseg=8):
    pts = []
    n = int(turns * segs)
    for i in range(n + 1):
        t = i / n
        a = TAU * turns * t
        pts.append((radius * math.cos(a), radius * math.sin(a), length * t))
    return pipe(name, pts, wire_r, coll, mat=mat, nseg=nseg)


def pipe(name, path, r, coll, mat=None, nseg=12, cap=True, r_end=None):
    """Sweep a circular section along a 3D polyline (exhaust, hoses, shafts)."""
    P = [Vector(p) for p in path]
    tangents = []
    for i in range(len(P)):
        if i == 0:
            t = P[1] - P[0]
        elif i == len(P) - 1:
            t = P[-1] - P[-2]
        else:
            t = (P[i + 1] - P[i]).normalized() + (P[i] - P[i - 1]).normalized()
        if t.length < 1e-9:
            t = Vector((1, 0, 0))
        tangents.append(t.normalized())
    up = Vector((0, 0, 1))
    if abs(tangents[0].dot(up)) > 0.95:
        up = Vector((0, 1, 0))
    u = (up - tangents[0] * up.dot(tangents[0])).normalized()
    verts = []
    for i, p in enumerate(P):
        t = tangents[i]
        u = (u - t * u.dot(t))
        if u.length < 1e-7:
            u = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((0, 1, 0))
            u = (u - t * u.dot(t))
        u.normalize()
        v = t.cross(u).normalized()
        rr = r if r_end is None else U_lerp(r, r_end, i / max(1, len(P) - 1))
        for k in range(nseg):
            a = TAU * k / nseg
            verts.append(tuple(p + u * (rr * math.cos(a)) + v * (rr * math.sin(a))))
    faces = []
    for i in range(len(P) - 1):
        a = i * nseg
        b = (i + 1) * nseg
        for k in range(nseg):
            k2 = (k + 1) % nseg
            faces.append([a + k, a + k2, b + k2, b + k])
    if cap:
        faces.append(list(range(nseg - 1, -1, -1)))
        o = (len(P) - 1) * nseg
        faces.append([o + k for k in range(nseg)])
    return mesh_obj(name, verts, faces, coll, mat=mat, smooth=True)


def aim(ob, direction, track='X', up='Z'):
    """Rotate an object so its local `track` axis points along `direction`."""
    d = Vector(direction)
    if d.length < 1e-9:
        return ob
    q = d.normalized().to_track_quat(track, up)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = q
    return ob


def aim_euler(ob, direction, track='X', up='Z'):
    aim(ob, direction, track, up)
    ob.rotation_mode = 'XYZ'
    return ob


def parent(child, parent_ob, keep_transform=True, update=None):
    child.parent = parent_ob
    if not keep_transform:
        return child
    if update is None:
        # matrix_world is cached until the depsgraph runs; refresh when the parent
        # has a real transform so matrix_parent_inverse is correct.
        update = (any(abs(v) > 1e-9 for v in parent_ob.location)
                  or any(abs(v) > 1e-9 for v in parent_ob.rotation_euler)
                  or any(abs(v) > 1e-9 for v in parent_ob.rotation_quaternion))
    if update:
        bpy.context.view_layer.update()
    child.matrix_parent_inverse = parent_ob.matrix_world.inverted()
    return child


def U_lerp(a, b, t):
    return a + (b - a) * t


def strip(name, path2d, half_t, y_in, y_out, coll, mat=None, bev=0.0, segments=2,
          cap=True):
    """Solid strip following a 2D (x,z) polyline, extruded between y_in and y_out."""
    P = [Vector((p[0], p[1])) for p in path2d]
    verts = []
    for i, p in enumerate(P):
        if i == 0:
            t = (P[1] - P[0])
        elif i == len(P) - 1:
            t = (P[-1] - P[-2])
        else:
            t = (P[i + 1] - P[i - 1])
        t.normalize()
        n = Vector((-t.y, t.x))
        for y in (y_in, y_out):
            verts.append((p.x + n.x * half_t, y, p.y + n.y * half_t))
            verts.append((p.x - n.x * half_t, y, p.y - n.y * half_t))
    # per path point: [in+, in-, out+, out-]
    faces = []
    for i in range(len(P) - 1):
        a = i * 4
        b = (i + 1) * 4
        faces.append([a + 0, a + 1, b + 1, b + 0])   # inner
        faces.append([a + 3, b + 3, b + 2, a + 2])   # outer
        faces.append([a + 0, b + 0, b + 3, a + 3])   # side +
        faces.append([a + 1, a + 2, b + 2, b + 1])   # side -
    if cap:
        faces.append([0, 1, 3, 2])
        o = (len(P) - 1) * 4
        faces.append([o + 0, o + 2, o + 3, o + 1])
    ob = mesh_obj(name, verts, faces, coll, mat=mat)
    if bev > 0:
        bevel(ob, bev, segments)
    return ob


# --------------------------------------------------------------------------------------
# 2d shape helpers
# --------------------------------------------------------------------------------------

def rounded_rect(w, h, r, cx=0.0, cz=0.0, corner_segs=4, top_r=None):
    """Closed CCW outline of a rounded rectangle in (x, z)."""
    tr = r if top_r is None else top_r
    pts = []
    # start bottom-right, go CCW (x right, z up)
    corners = [
        (cx + w / 2 - r, cz - h / 2, -math.pi / 2, 0.0, r),
        (cx + w / 2 - tr, cz + h / 2, 0.0, math.pi / 2, tr),
        (cx - w / 2 + tr, cz + h / 2, math.pi / 2, math.pi, tr),
        (cx - w / 2 + r, cz - h / 2, math.pi, 3 * math.pi / 2, r),
    ]
    for (px, pz, a0, a1, rr) in corners:
        for s in range(corner_segs + 1):
            a = a0 + (a1 - a0) * s / corner_segs
            pts.append((px + rr * math.cos(a), pz + rr * math.sin(a)))
    # drop duplicated corner endpoints
    out = []
    for p in pts:
        if not out or (abs(p[0] - out[-1][0]) > 1e-6 or abs(p[1] - out[-1][1]) > 1e-6):
            out.append(p)
    if (abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6):
        out.pop()
    return out


def circle_pts(cx, cz, r, n=24, a0=0.0, a1=TAU):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n),
             cz + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def arc_pts(cx, cz, r, a0, a1, n=16):
    return circle_pts(cx, cz, r, n, a0, a1)


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def join_outline(segments):
    """Concatenate outline segments dropping duplicated joints."""
    out = []
    for seg in segments:
        for p in seg:
            if not out or (abs(p[0] - out[-1][0]) > 1e-7 or abs(p[1] - out[-1][1]) > 1e-7):
                out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-7 and abs(out[0][1] - out[-1][1]) < 1e-7:
        out.pop()
    return out


def circle_profile(half_w, z_bot, z_top, r, segs=4, n_top=1):
    """Closed (y,z) cross-section: rounded rectangle spanning +-half_w."""
    return rounded_rect(2 * half_w, z_top - z_bot, r, cx=0.0,
                        cz=(z_top + z_bot) / 2, corner_segs=segs)


def offset_profile(prof, d):
    """Offset a closed (y,z) profile outward from its centroid by d (approximate)."""
    cy = sum(p[0] for p in prof) / len(prof)
    cz = sum(p[1] for p in prof) / len(prof)
    out = []
    for (y, z) in prof:
        vy, vz = y - cy, z - cz
        L = math.hypot(vy, vz) or 1.0
        out.append((y + d * vy / L, z + d * vz / L))
    return out
