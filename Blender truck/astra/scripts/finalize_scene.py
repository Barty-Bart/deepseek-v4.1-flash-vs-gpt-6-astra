"""Embed documentation and the passing report, restore frame 1, and save. Never renders."""
import bpy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
report=json.loads((ROOT/'reports/verification.json').read_text())
assert all(report['checks'].values()),'Cannot finalize a scene with failing checks'
assert Path(bpy.data.filepath).resolve()==(ROOT/'pickup_truck.blend').resolve()
assert (ROOT/'reports/verification.json').stat().st_mtime >= (ROOT/'pickup_truck.blend').stat().st_mtime,'Re-run verification on the latest scene before finalizing'
for path in [ROOT/'README.md',ROOT/'reports/verification.json',ROOT/'scripts/build_truck.py',ROOT/'scripts/verify_scene.py',ROOT/'scripts/finalize_scene.py']:
    block=bpy.data.texts.get(path.name) or bpy.data.texts.new(path.name)
    block.clear();block.write(path.read_text())
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
scene['verification_status']='PASS: '+str(len(report['checks']))+' checks; 240 evaluated output frames'
scene['verification_report']='Embedded verification.json and README.md; external reports/ contains the full evaluated data.'
scene['rendering_status']='DEFERRED — no image, animation, or frame sequence rendering performed'
scene['measured_camera_clearance_m']=report['min_camera_mesh_clearance_m']
scene['measured_max_leaf_saddle_error_m']=report['max_leaf_saddle_error_m']
for o in bpy.context.selected_objects:o.select_set(False)
root=bpy.data.objects['CTRL_VEHICLE_TRAVEL'];root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'pickup_truck.blend'))
print('FINAL_SCENE_SAVED',bpy.data.filepath,scene['verification_status'])
