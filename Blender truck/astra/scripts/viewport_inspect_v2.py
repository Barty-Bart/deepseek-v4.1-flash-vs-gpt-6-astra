"""Capture ordinary solid Blender viewports for v2 inspection. No rendering."""
import bpy
from pathlib import Path
stage=0
frames=[1,84,108,378,386,410,498]
def inspect():
 global stage
 if stage>=len(frames):bpy.ops.wm.quit_blender();return None
 scene=bpy.context.scene;scene.frame_set(frames[stage]);win=bpy.context.window_manager.windows[0];area=next(a for a in win.screen.areas if a.type=='VIEW_3D')
 sp=area.spaces.active;sp.shading.type='SOLID';sp.shading.color_type='MATERIAL';sp.overlay.show_overlays=False;sp.region_3d.view_perspective='CAMERA';sp.region_3d.view_camera_zoom=20;area.tag_redraw()
 def capture():
  global stage
  with bpy.context.temp_override(window=win,area=area):bpy.ops.screen.screenshot(filepath='/tmp/kestrel_v2_%03d.png'%frames[stage])
  print('V2_VIEWPORT_CHECK',frames[stage],flush=True);stage+=1
  return None
 bpy.app.timers.register(capture,first_interval=2)
 return 4
bpy.app.timers.register(inspect,first_interval=5)
