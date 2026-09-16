"""Optional UI-only inspection. Captures Blender's ordinary solid viewport, never renders."""
import bpy, os
from pathlib import Path
stage=0
frames=[1,62,93,107,158,165,240]
def inspect():
 global stage
 try:
  if stage>=len(frames):
   bpy.ops.wm.quit_blender();return None
  scene=bpy.context.scene;scene.frame_set(frames[stage])
  win=bpy.context.window_manager.windows[0]
  area=next(a for a in win.screen.areas if a.type=='VIEW_3D')
  area.spaces.active.shading.type='SOLID'
  area.spaces.active.overlay.show_relationship_lines=False
  area.spaces.active.overlay.show_extras=False
  if stage:
   area.spaces.active.region_3d.view_perspective='CAMERA'
   area.spaces.active.region_3d.view_camera_zoom=0
  area.tag_redraw()
  def capture():
   global stage
   try:
    with bpy.context.temp_override(window=win,area=area):
     bpy.ops.screen.screenshot(filepath='/tmp/kestrel_viewport_%03d.png'%frames[stage])
    print('VIEWPORT_CAPTURED',frames[stage],flush=True)
   except Exception as e:print('VIEWPORT_CAPTURE_FAILED',str(e),flush=True)
   stage+=1
   return None
  bpy.app.timers.register(capture,first_interval=2)
  return 4
 except Exception as e:
  print('VIEWPORT_BLOCKER',str(e),flush=True);bpy.ops.wm.quit_blender();return None
bpy.app.timers.register(inspect,first_interval=5)
