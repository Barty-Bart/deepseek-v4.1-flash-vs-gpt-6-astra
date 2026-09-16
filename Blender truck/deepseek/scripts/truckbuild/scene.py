"""Scene, render-engine and collection setup."""
import bpy
from . import spec
from . import util as U


def setup_scene():
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = 'METERS'
    sc.render.fps = spec.FPS
    sc.render.fps_base = 1.0
    sc.frame_start = spec.FRAME_START
    sc.frame_end = spec.FRAME_END
    sc.frame_set(spec.FRAME_START)
    sc.render.resolution_x = spec.RES_X
    sc.render.resolution_y = spec.RES_Y
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.35
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'

    engines = [i.identifier for i in
               bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in engines else engines[0]
    ee = sc.eevee
    for attr, val in (('taa_render_samples', 128), ('taa_samples', 32),
                      ('use_shadows', True), ('use_raytracing', True),
                      ('shadow_ray_count', 3), ('shadow_step_count', 6),
                      ('use_shadow_jitter_viewport', True),
                      ('motion_blur_steps', 4), ('motion_blur_max', 0.4),
                      ('direct_light_intensity', 1.0), ('indirect_light_intensity', 1.0),
                      ('volumetric_samples', 48)):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, val)
            except Exception:
                pass
    for attr, val in (('resolution_scale', None),):
        pass
    if hasattr(sc, 'render') and hasattr(sc.render, 'use_high_quality_normals'):
        sc.render.use_high_quality_normals = True

    for vt in ('AgX', 'Filmic', 'Standard'):
        try:
            sc.view_settings.view_transform = vt
            break
        except Exception:
            continue
    sc.view_settings.exposure = 0.42
    sc.view_settings.look = 'None'

    world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0.34, 0.40, 0.48, 1.0)
    bg.inputs['Strength'].default_value = 1.35
    grad = nt.nodes.new('ShaderNodeTexGradient')
    grad.gradient_type = 'LINEAR'
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.30, 0.36, 0.44, 1.0)
    ramp.color_ramp.elements[1].color = (0.62, 0.70, 0.80, 1.0)
    map_ = nt.nodes.new('ShaderNodeMapping')
    texc = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(texc.outputs['Generated'], map_.inputs['Vector'])
    nt.links.new(map_.outputs['Vector'], grad.inputs['Vector'])
    nt.links.new(grad.outputs['Color'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs[0], out.inputs['Surface'])

    colls = {}
    for c in spec.COLLECTIONS:
        colls[c] = U.ensure_collection(c)
    return colls
