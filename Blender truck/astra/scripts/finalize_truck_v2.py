"""Embed passing v2 documentation, restore the opening pose, pack and save only v2.

Run after build_truck_v2.py and verify_truck_v2.py. Never renders.
"""
import bpy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'pickup_truck_v2.blend'
BASE = ROOT / 'pickup_truck.blend'
REPORT_PATH = ROOT / 'reports/v2/verification.json'
report = json.loads(REPORT_PATH.read_text())
manifest = json.loads((ROOT / 'reports/v2/build_manifest.json').read_text())
assert Path(bpy.data.filepath).resolve() == OUT.resolve(), 'Open v2 before finalizing'
assert Path(report['file']).resolve() == OUT.resolve(), 'Report must describe v2'
assert all(report['checks'].values()), 'Cannot finalize with failing checks'
assert REPORT_PATH.stat().st_mtime >= OUT.stat().st_mtime, 'Verify the latest saved scene first'
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == manifest['base_sha256']
scene = bpy.context.scene
assert (scene.frame_start, scene.frame_end, scene.render.fps) == (1, 498, 24)

for name in ['README.md', 'verification.json', 'build_truck.py', 'verify_scene.py', 'finalize_scene.py']:
    block = bpy.data.texts.get(name)
    if block:
        block.name = 'V1 ARCHIVE | ' + name

def embed(name, content):
    block = bpy.data.texts.get(name) or bpy.data.texts.new(name)
    block.clear()
    block.write(content)
    return block

embed('README | START HERE',
      'KESTREL v2 — 20.75 seconds / 24 fps / 1920x1080\n\n'
      'Read embedded README_v2.md for the current timeline, controls and limitations.\n'
      'Opening: engine bay, pan out, hood closes, smooth launch.\n'
      'Frames 361–420: additional 2.5-second rear suspension hold while driving.\n'
      'Active camera: CAM_ANIMATION_V2 | engine and dual rear inspection.\n'
      'Press Numpad 0 for the camera; scrub frames 1–498.\n'
      'All 19 verification checks pass; see verification_v2.json.\n'
      'V1 ARCHIVE text blocks describe the preserved original, not this revision.\n'
      'All animation is native; no runtime scripts needed. Nothing rendered.\n')
embed('verification_v2.json', REPORT_PATH.read_text())
for path in [ROOT / 'README_v2.md', *[ROOT / 'scripts' / name for name in
             ['build_truck_v2.py', 'verify_truck_v2.py', 'finalize_truck_v2.py', 'viewport_inspect_v2.py']]]:
    embed(path.name, path.read_text())

scene.camera = bpy.data.objects['CAM_ANIMATION_V2 | engine and dual rear inspection']
scene.frame_set(1)
bpy.context.view_layer.update()
scene['verification_status'] = f"PASS: {len(report['checks'])} checks; 498 evaluated output frames"
scene['verification_report'] = 'Embedded verification_v2.json and README_v2.md; external reports/v2 contains full samples.'
scene['rendering_status'] = 'DEFERRED — no image, animation or frame sequence rendering performed'
scene['measured_camera_clearance_m'] = report['minimum_camera_clearance']['distance_m']
scene['measured_max_leaf_saddle_error_m'] = report['maximum_leaf_saddle_error_m']
scene['v2_build_seconds'] = manifest['build_seconds']
scene['v2_verification_seconds'] = report['verification_seconds']
scene['historical_metadata_note'] = 'construction_elapsed_seconds refers to the original build; current revision has v2 timing fields.'
for obj in bpy.context.selected_objects:
    obj.select_set(False)
hood_control = bpy.data.objects['CTRL_HOOD_OPEN']
hood_control.select_set(True)
bpy.context.view_layer.objects.active = hood_control
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == manifest['base_sha256'], 'Original file changed'
print('V2_FINALIZED', bpy.data.filepath, scene['verification_status'], flush=True)
