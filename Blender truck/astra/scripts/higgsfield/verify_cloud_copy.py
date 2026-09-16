"""Verify the downloaded cloud scene retains the accepted evaluated animation. Read-only."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path(__file__).resolve().parents[2]
camera_rows=json.loads((ROOT/'reports/v2/camera_samples.json').read_text())
pose_rows=json.loads((ROOT/'reports/v2/evaluated_frames.json').read_text())['frames']
scene=bpy.context.scene; root=bpy.data.objects['CTRL_VEHICLE_TRAVEL'];camera=scene.camera
assert (scene.frame_start,scene.frame_end,scene.render.fps)==(1,498,24)
errors={'camera_position_m':0,'camera_quaternion_components':0,'camera_lens_mm':0,'vehicle_travel_m':0,'suspension_m':0}
for pose,cam in zip(pose_rows,camera_rows):
 f=pose['frame'];scene.frame_set(f);bpy.context.view_layer.update();d=root['travel_m']
 errors['camera_position_m']=max(errors['camera_position_m'],(camera.location-Vector((d,0,0))-Vector(cam['camera_relative'])).length)
 errors['camera_quaternion_components']=max(errors['camera_quaternion_components'],min(max(abs(a-b) for a,b in zip(camera.rotation_quaternion,cam['rotation'])),max(abs(a+b) for a,b in zip(camera.rotation_quaternion,cam['rotation']))))
 errors['camera_lens_mm']=max(errors['camera_lens_mm'],abs(camera.data.lens-cam['lens_mm']))
 errors['vehicle_travel_m']=max(errors['vehicle_travel_m'],abs(d-pose['travel_m']))
 for c in ['FL','FR','RL','RR']: errors['suspension_m']=max(errors['suspension_m'],abs(bpy.data.objects['CTRL_SUSPENSION_'+c]['travel_m']-pose['suspension_m'][c]))
assert max(errors.values())<.0001,errors
invalid=[o.name for o in list(bpy.data.objects)+list(bpy.data.shape_keys) if o.animation_data and any(not fc.driver.is_valid for fc in o.animation_data.drivers)]
assert not invalid,invalid
original_hash=hashlib.sha256((ROOT/'pickup_truck_v2.blend').read_bytes()).hexdigest()
assert original_hash=='87e45acda5c96de74f36f71f2521b6050dbe0c0f29506b9ae2b183f63238bbe2'
result={'file':bpy.data.filepath,'frames_checked':498,'objects':len(scene.objects),'maximum_errors_against_accepted_v2':errors,'invalid_drivers':invalid,'accepted_v2_unchanged':True}
(ROOT/'reports/higgsfield/cloud_pose_verification.json').write_text(json.dumps(result,indent=2))
print('CLOUD_POSE_VERIFICATION_PASS',json.dumps(result),flush=True)
