import time, json, math
scene=bpy.context.scene
assert len(scene.objects)==1403, len(scene.objects)
assert scene.frame_end==498 and scene.render.fps==24
assert scene.camera.name=='CAM_ANIMATION_V2 | engine and dual rear inspection'
root=bpy.data.objects['CTRL_VEHICLE_TRAVEL']
samples=[]
for f in [1,84,108,133,324,361,378,386,420,451,498]:
    scene.frame_set(f)
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    samples.append({'frame':f,'travel':root['travel_m'],'hood':bpy.data.objects['CTRL_HOOD_OPEN']['open_deg'],'camera_relative':list(scene.camera.location-__import__('mathutils').Vector((root['travel_m'],0,0))),'RR_travel':bpy.data.objects['CTRL_SUSPENSION_RR']['travel_m']})
invalid=[o.name for o in list(bpy.data.objects)+list(bpy.data.shape_keys) if o.animation_data and any(not fc.driver.is_valid for fc in o.animation_data.drivers)]
assert not invalid, invalid
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=768
scene.render.resolution_y=432
scene.render.resolution_percentage=100
scene.render.image_settings.media_type='IMAGE'
scene.render.image_settings.file_format='PNG'
scene.eevee.taa_render_samples=16
scene.view_settings.view_transform='AgX'
timings=[]
for f in [1,133,386]:
    scene.frame_set(f)
    target=artifacts.file(name='kestrel_preview_%03d.png'%f,media_type='image/png')
    scene.render.filepath=str(target.path)
    start=time.perf_counter()
    bpy.ops.render.render(write_still=True)
    target.publish()
    timings.append({'frame':f,'render_seconds':time.perf_counter()-start})
result={'samples':samples,'invalid_drivers':invalid,'render_timings':timings,'objects':len(scene.objects),'fps':scene.render.fps,'frames':[scene.frame_start,scene.frame_end]}
