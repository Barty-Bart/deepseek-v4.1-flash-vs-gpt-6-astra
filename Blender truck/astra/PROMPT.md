# Blender benchmark — working pickup truck and mechanical inspection film

Build an original, highly detailed pickup truck in Blender, with an inspectable undercarriage and visibly functioning suspension. Deliver the editable .blend scene with a fully prepared 10-second camera animation. Do not render images, video or frame sequences in this iteration. Work autonomously: make reasonable decisions, document them, and proceed without creative questions. Use local Blender Python scripts through bpy, as detailed below. Do not use paid generation, downloaded vehicle models, external asset packs or public hosting. Do not buy or install paid add-ons.

## Vehicle and visual direction

Create a fictional contemporary midsize four-wheel-drive crew-cab pickup, approximately 5.3 m long, 1.9 m wide and 1.85 m tall, with a 3.2 m wheelbase. Use metric units and believable proportions. Style: purposeful expedition vehicle, satin forest-green paint, dark trim, brushed metal details, warm LED lamps and realistically weathered rubber. No real manufacturer badges. Keep weathering restrained so mechanical detail stays readable.

Model actual geometry for the cab, hood, doors and panel gaps, windows with thickness, mirrors, handles, bumpers, grille, headlights and taillights, wheel arches, bed liner, tailgate, tow hitch, visible interior seats/dashboard/steering wheel, alloy wheels, tread blocks and sidewalls. Use efficient detail where the camera sees it. Prioritize coherent proportions and mechanical readability over arbitrary polygon counts. Do not substitute textures or flat cards for the close-up suspension geometry.

## Inspectable undercarriage

Use a coherent body-on-frame design: twin frame rails and crossmembers; simplified but identifiable engine/transmission/transfer case; front and rear driveshafts and differential housings; fuel tank; exhaust routing, muffler and heat shields; skid plates where appropriate; steering rack and tie rods; brake discs, calipers and plausible brake hoses; suspension mounting brackets, bolts and bushings. Keep the key components visible during the underside camera pass. Skid plates must not conceal the entire drivetrain. Avoid floating components, implausible intersections or exhaust routed through the fuel tank.

Front suspension: independent double wishbones with coil-over dampers and steering knuckles. Rear suspension: a driven solid axle with leaf springs and separate dampers. The rear differential moves with the axle. Make the rear-right leaf spring flex and shock shorten/extend during wheel travel; do not place a decorative coil-over beside a leaf-spring system unless it has an explicitly justified function.

This is a visually credible mechanical demonstration, not an engineering-certified vehicle simulation. State simplifications honestly.

## Rig and motion

Provide clearly named controls for vehicle travel, steering, wheel rotation, body heave/pitch/roll, and each wheel's suspension travel. Use constraints, drivers, bones or scripted animation as appropriate. Mechanical linkages must move coherently rather than merely bobbing the whole truck.

Animate the truck travelling forward at roughly 3 m/s across a compact rough-road set with low rounded bumps. Wheels rotate consistently with distance travelled and tire radius. Tires remain near road contact without obvious sliding, floating or penetration. Maintain plausible suspension travel, approximately +/- 80 mm around normal ride height. Frame/body motion should be smaller and smoother than wheel motion. Steering can remain nearly straight. A deterministic kinematic rig is acceptable; full rigid-body physics is not required.

At the rear-right close-up, show at least one unmistakable compression/rebound cycle. Its wheel, axle, leaf spring, shock and driveshaft relationship must remain coherent throughout. Do not fake this by scaling the whole suspension assembly.

## Exact film deliverable

Prepare a continuous 10-second shot at 24 fps, frames 1–240, with future output configured to 1920x1080. Configure sensible Eevee settings for later use, but do not execute rendering. No narration, music, captions or branded overlays are needed.

Camera choreography:
- 0–2 seconds: low side-profile tracking shot, full truck visible, establishing rolling wheels and road movement.
- 2–3.5 seconds: smooth arc toward the front three-quarter view, then descend toward the underside through a clear route.
- 3.5–6 seconds: travel beneath the chassis, scanning the frame, drivetrain, exhaust and rear axle. Use enough fill light to reveal these components. The lens must not clip through solid parts or the road. A locally recessed inspection channel beneath the camera path is acceptable if the wheels still run on continuous road tracks.
- 6–8 seconds: close-up of the rear-right suspension from an unobstructed rear/side angle. Keep the wheel hub, shock and leaf spring visible as a road bump produces compression and rebound. Hold this shot steady enough to inspect the mechanism.
- 8–10 seconds: pull out smoothly to a rear three-quarter view, then let the truck continue into the distance. End with the whole vehicle visible and moving away.

Use smooth camera curves and controlled easing. Keep motion blur and depth of field modest, especially during inspection. Prioritize seeing the mechanism over dramatic camera movement. If physical clearance makes a transition impossible, adjust the path or inspection-channel geometry rather than passing through objects.

## Scene, organization and deliverables

Create a neutral outdoor industrial test road with soft daylight, grounded shadows and a restrained background. Organize collections: BODY, INTERIOR, CHASSIS, DRIVETRAIN, FRONT_SUSPENSION, REAR_SUSPENSION, WHEELS, RIG, ROAD, CAMERAS and LIGHTS. Name components descriptively. Pack required textures/resources into the .blend and preserve editable geometry and rig controls. Avoid destructive flattening of the truck into one mesh.

Deliver:
1. pickup_truck.blend, opening in a useful full-vehicle three-quarter view.
2. The complete animated camera path and vehicle rig saved inside the .blend, ready for later rendering.
3. Four named inspection cameras: full truck, underside overview, front suspension, rear-right suspension. No rendered stills required.
4. README.md describing controls, scene scale, render settings, how to reproduce the animation, verified results and known limitations.
5. Any local construction/animation scripts used, so the result is reproducible.

## Verification and stopping criteria

First verify Blender connectivity and inspect the scene before changing it. Work in a new scene/file without overwriting unrelated user work. Build and verify a simple rig before adding fine detail. Scrub the timeline or inspect evaluated transforms to verify the complete camera path. Viewport inspection is allowed; do not invoke image or animation rendering.

Check wheel rotation against travelled distance, camera clearance, wheel-ground contact, suspension motion at minimum/maximum travel, and visibility of the required undercarriage parts. Inspect representative frames at every camera segment and both rear-right compression extremes. Correct observed defects, then save the verified scene. Do not loop endlessly over cosmetic tweaks after the required checks pass.

Report measured elapsed time and model/API usage only when available. Rendering is deferred. Clearly distinguish verified behavior from assumptions. If a tool fails, retain the complete editable scene and report the concrete blocker. Do not claim a finished rendered film; this iteration delivers the scene and animation only.

## Local Blender execution — verified workspace method

Blender 5.2.1 LTS is installed at /Applications/Blender.app/Contents/MacOS/Blender. Existing workspace scripts use Python with `import bpy`. Run bpy scripts inside Blender's bundled Python, not ordinary system Python. No Blender MCP installation is needed for this workflow.

Create a reproducible script such as scripts/build_truck.py and run:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_truck.py
```

Save the result with bpy.ops.wm.save_as_mainfile to pickup_truck.blend in this project. Verify by reopening the saved file in a separate background Blender process and running a read-only verification script. Use evaluated dependency-graph transforms to check linkage movement at selected frames. Do not call bpy.ops.render.render, use command-line render flags, or start paid/external generation. A new background process avoids replacing an unrelated open Blender scene. Preserve scripts and verification results.
