# Blender benchmark — working pickup truck and mechanical inspection film

A fictional contemporary midsize four-wheel-drive crew-cab pickup, modelled and rigged
from scratch in Blender 5.2.1 with local `bpy` scripts, plus a fully prepared **28-second**
camera animation whose final act lives under the truck: a five-second centred undercarriage
hold and an axle-line view into the inside of a wheel.

## Deliverables in this folder

| File | What it is |
|---|---|
| `pickup_truck.blend` | The complete scene: model, materials, rig, baked animation, 5 cameras, lighting |
| `README.md` | This document |
| `scripts/build_truck.py` | Builds the whole scene from nothing and saves the `.blend` |
| `scripts/truckbuild/*.py` | The build library (geometry, road, rig, kinematics, cameras, lights) |
| `scripts/verify_scene.py` | Read-only verification; reopens the saved file in a fresh process |
| `verify_report.txt` | Output of the last verification run (60 checks, 0 failures) |
| `build_report.txt` | Object counts per collection and build timing |
| `scripts/render_film.py` | Renders the film (frames or PNG sequence); render pass only |
| `scripts/render_and_encode.py` | Chunked render + system-ffmpeg encode driver |
| `renders/pickup_truck_1080p.mp4` | The rendered film, 1920×1080, 24 fps, H.264 |
| `qa/*.png` | Optional geometry-inspection images (see "Inspection aids" below) |

(Blender also leaves a `pickup_truck.blend1` auto-backup next to the saved file; it is a
byte-identical copy of the previous save and can be ignored or deleted.)

Reproduce everything:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
    --python scripts/build_truck.py          # writes pickup_truck.blend  (~4 s)
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
    --python scripts/verify_scene.py         # read-only checks, writes verify_report.txt
```

## Scene scale and conventions

* Metric, metres, `scale_length = 1.0`, ground plane at `z = 0`.
* `+X` = forward (direction of travel), `+Z` = up, `+Y` = vehicle **left**.
  The film views the vehicle's **right** side (negative Y).
* Measured envelope (from evaluated geometry, frame 1):

| Measure | Value |
|---|---|
| Wheelbase | 3.200 m (front axle +1.600, rear −1.600) |
| Body length (bumper to tailgate) | 5.377 m; 5.42 m including hitch/licence plate |
| Body width over the flares | 1.92 m; 2.016 m over the rock sliders; 2.204 m over the mirrors |
| Height | 1.886 m to the roof; 1.983 m to the snorkel head |
| Tyre | 0.790 m diameter (rolling radius 0.395 m), 0.28 m section |
| Frame rails | 100 mm × 180 mm box, top at z = 0.78, at y = ±0.44 |
| Ride height | wheel centres at z = 0.395; ~0.28 m under the rear differential |

## Controls — how to drive the vehicle by hand

The rig is deliberately named and shallow. Collections: `BODY`, `INTERIOR`, `CHASSIS`,
`DRIVETRAIN`, `FRONT_SUSPENSION`, `REAR_SUSPENSION`, `WHEELS`, `RIG`, `ROAD`, `CAMERAS`,
`LIGHTS`. Nothing is flattened — every panel, link and control is a separate editable object.

| Control | Type | Role |
|---|---|---|
| `RIG_Truck` | Empty | Vehicle travel along `+X` in metres (0 → 29.875 m over frames 1–240) |
| `RIG_Sprung` | Empty | Sprung-mass heave (`location.z`), pitch (`rotation_euler.y`), roll (`.x`) |
| `CTRL_Steering` | Empty | Steering input, `rotation_euler.z` in radians (rack travel = −angle × 0.30 m) |
| `RIG_Body` | Empty | Parent of all `BODY` + `INTERIOR` meshes |
| `RIG_Frame` | Empty | Parent of `CHASSIS` + `DRIVETRAIN` |
| `CTRL_FSusp_L/R` | Empty | Front knuckle assembly output (position + orientation). Its children are the knuckle, hub, brake caliper and the wheel |
| `CTRL_RSusp_RL/RR` | Empty | Rear wheel travel: `location.z` is the wheel-centre height in the sprung frame, `rotation_euler.x` is axle roll |
| `CTRL_RearAxle` | Empty | The driven beam axle: travel + roll; the differential, hubs, leaf seats and calipers are its children |
| `LeafArm_L/R` | Armature | The leaf spring itself: a 14-bone chain skinned to the blade pack |
| `WHEEL_FL/FR/RL/RR` | Mesh | Wheel rotation is `rotation_euler.y` = travelled distance ÷ tyre radius |
| `FS_LowerArm_*`, `FS_UpperArm_*` | Mesh | Wishbone links; rotate about their own pivot origins on local X |
| `FS_CoilBody/Rod/Spring_*`, `Rear_ShockBody/Rod_*` | Mesh | Damper bodies, sliding rods and the compressing coil spring |
| `FS_TieRod_*`, `Drive_CVShaft_*`, `Drive_RearShaft` | Mesh | Aimed links driven from their base end |
| `CAM_Film_Main` | Camera | The 10-second shot (active scene camera) |
| `CAM_Full_Truck`, `CAM_Underside_Overview`, `CAM_Front_Suspension`, `CAM_RearRight_Suspension` | Cameras | Named inspection cameras, all aimed at the parked truck at rest |

Every control is keyframed on every frame of 1–240, so scrubbing the timeline in a plain
Blender session reproduces the verified motion exactly. Useful UI notes: `RIG_Truck` has a
`role` custom property, the empties use `PLAIN_AXES` display, and the leaf armatures show
their bone chain in wireframe.

To hand-animate instead of using the bake: delete the keyframes you want to drive and set
`CTRL_RSusp_*`/`CTRL_FSusp_*` by hand — the leaf springs and dampers are *not* script-driven
at playback time, they are baked, so manual edits to those controls need the same solver
(`scripts/truckbuild/suspension.py`) re-run to regenerate the link motion.

## How the animation is produced (`scripts/truckbuild/anim.py`)

Deterministic kinematic bake, no physics engine:

1. The truck travels at exactly **3.000 m/s** (0 → 29.875 m) along `+X`.
2. `road.wheel_center_z()` solves the tyre contact point against the analytic road surface
   (the contact normal passes through the wheel centre, so tyres neither sink into bump
   crests nor float).
3. Each corner's road input is low-pass filtered (2nd-order, 1.30 Hz, zero phase) and scaled
   by 0.42 — the sprung mass absorbs a little under half of the wheel input. A rigid-body
   fit through the four filtered corner responses gives heave, pitch and roll.
4. The resulting per-corner wheel heights in the sprung frame drive the mechanisms:
   * **Front** — planar 4-bar (frame / lower wishbone / knuckle / upper wishbone) solved by
     bisection on the lower-arm angle for the demanded wheel height. Camber, track change
     and the steering-knuckle pose are outputs of the linkage, not inputs.
   * **Rear** — the beam axle is placed by the two wheel centres (position + roll); each leaf
     spring is solved with FABRIK as a fixed-length chain pinned at the front eye, clamped
     to the axle in the middle and shackled at the rear eye; the damper re-aims and its rod
     slides so its length stays exact.
5. Wheel rotation = travelled distance ÷ 0.395 m for all four wheels.
6. Keyframes are inserted for every driven control. The leaf bone chains are keyed every
   second frame (the event is smooth at that rate); everything else is keyed per frame.

## Camera shot breakdown (24 fps, frames 1–672, 1920×1080)

| Time | Frames | Shot |
|---|---|---|
| 0.0–3.0 s | 1–72 | Low tracking shot close to the profile (opens on a three-quarter that settles to a side profile), whole truck in frame at ~7 m |
| 3.0–5.8 s | 72–139 | Smooth arc around the front three-quarter and a descent into the recessed inspection channel ahead of the truck |
| 5.8–9.6 s | 139–230 | The truck overtakes the camera; the lens scans the frame rails, drivetrain and exhaust from below |
| 9.6–11.2 s | 230–268 | Settles behind the rear axle, still in the channel |
| **11.2–16.2 s** | **268–389** | **Centred undercarriage hold — five seconds looking up at the rear axle, differential, leaf packs, dampers, prop shaft and exhaust while the suspension works** |
| 16.2–18.6 s | 389–447 | Rear-right leaf-spring close-up, held steady at ~2.1 m through a full compression/rebound cycle |
| 18.6–21.4 s | 447–513 | Dips back under the tail and glides forward along the drivetrain: prop shaft, transfer case, transmission, exhaust and tank |
| 21.4–23.0 s | 513–551 | Glides back to the rear axle |
| **23.0–25.8 s** | **551–619** | **Looks along the axle at the inside of the rear-right wheel: brake rotor, caliper, hub, axle tube, leaf U-bolts and damper, with the suspension moving up and down** |
| 25.8–28.0 s | 619–672 | The truck clears the camera and drives away; the camera rises and swings out to hold the whole vehicle |

Position, aim point and focal length (24–42 mm) are keyframed on every frame with smoothstep
easing between shot keys; relative keys keep the 3 m/s tracking speed regardless of easing.
Depth of field is on with f/11 (modest) and the focus distance tracks the aim point.

## Render settings and the rendered film

`BLENDER_EEVEE` (Eevee Next), 1920×1080, 24 fps, frames 1–672, `AgX` view transform
(exposure +0.42), shadows and screen-space raytracing on, 4 motion-blur steps with a 0.35
shutter.

Rendered: `renders/pickup_truck_1080p.mp4` — H.264, 1920×1080, 24 fps, 28.0 s. Reproduce with

```bash
python3 scripts/render_and_encode.py 96 48      # chunk size, Eevee samples
```

Two constraints shaped that driver: this Blender 5.2.1 build does **not** offer `FFMPEG` in
`scene.render.image_settings.file_format` at runtime (the type-level enum lists it, the
instance-level enum does not), so Blender cannot write video itself and PNG frames are piped
through the system `ffmpeg`; and the boot disk was at 98 % full, so frames are rendered in
96-frame chunks, encoded to an H.264 segment and deleted before the next chunk, then
stream-copied into the final MP4. Lighting is one soft sun (4.5° angle) plus sky/ground/rim area
fills, nine strip lights inside the inspection channel, and two local fills for the
suspension close-ups. Materials are procedural Principled setups (satin forest green paint
with a subtle noise bump, tinted glass, brushed metal, weathered rubber, asphalt, concrete,
dark interior trim) — no external texture files, so nothing needs packing.

## Verified results

`verify_report.txt` — all checks pass, 0 failures (66 checks). Measured highlights:

* Scene: 24 fps, frames 1–672 (28.0 s), 1920×1080, Eevee, metric; all 11 collections
  populated (516 objects total), 346 animated F-curves over 44 actions.
* Wheel rotation matches travelled distance ÷ radius to < 1e-4 rad at frames 1/61/121/181/240.
* Suspension travel (sprung frame, rest = 0): FL −5.6…+43.3 mm, FR −9.3…+63.8 mm,
  RL −7.1…+42.6 mm, RR −8.8…+64.2 mm — all inside ±80 mm.
* Rear-right wheel travel peaks at 56.4 mm with a 65.2 mm stroke over the film, and the
  2.4 s rear-right close-up (frames 389–447) contains a **61.7 mm compression/rebound
  cycle** of its own. Bumps are seeded across the whole 140 m road so the suspension keeps
  working through the five-second hold and both axle-view shots.
* Tyre/road contact over all four wheels across the film: worst case −3.4 mm (sub-millimetre
  scale shoulder contact at one bump) and worst gap +12.4 mm, i.e. no visible penetration or
  floating. The residual is the rigid-tyre approximation of tread deflection.
* Prop shaft endpoint tracks the differential pinion to **0.0 mm** across the film; the
  exhaust routes 91 mm clear of the fuel tank and the front skid plate sits 334 mm from the
  crank pulley, so no drivetrain or exhaust component fouls a neighbour.
* Leaf spring: segment lengths hold to 0.94 mm (no stretching); at the axle clamp the pack
  rises 50.1 mm during the close-up and its arc depth changes by 55.1 mm — the spring bends,
  it is not translated or scaled.
* Camera: minimum distance to any surface (true triangle test, sampled every 6 frames)
  **185 mm** (a channel-wall lip), closest vehicle part 223 mm (the tailpipe); stays inside
  the recessed channel for both under-truck passages and never passes beneath the road solid;
  continuous path (max 2.91 m per 8 frames during the deliberate fast arc).
* Undercarriage visibility: all 11 required components (frame rails, engine, transfer case,
  prop shaft, fuel tank, rear axle, diff, exhaust pipe and muffler, transfer-case skid) are
  inside the camera frustum for ≥ 8 frames of the underside pass.
* Tyre/road contact over all four wheels across all 672 frames: worst case −4.2 mm and worst
  gap +12.4 mm (the rigid-tyre approximation of tread deflection).
* Camera count 5, all named; the film camera's location is keyed on all 672 frames.
* Named controls exist for travel, steering, body heave/pitch/roll, all four wheel-travel
  outputs and both front knuckle mechanisms, and each is keyed on every frame.

## Known limitations and honest simplifications

* **Not an engineering simulation.** The rig is a deterministic kinematic mechanism driven
  from the road profile; there is no rigid-body solver, no tyre slip, no engine torque, no
  compliance in the frame and no dynamic load transfer.
* The chassis uses straight frame rails (no kick-up over the axle), and the suspension pivots
  are bracketed to them rather than modelling every factory gusset.
* Suspension geometry is a planar (2-D) 4-bar per side; anti-roll bar, jounce bumpers'
  interaction, steering-rack compliance and bushing deflection are represented only as static
  hardware. Steering is deliberately near-straight (≈ ±1.2°) so the tie rod's small length
  error (< 2 mm) is invisible; it is not a full steering linkage solve.
* The leaf spring is modelled as a constant-length chain of 14 rigid segments with four blades
  that follow the same arc; real leaves interleave and slide at their tips. The rear shackle
  swings, but the front eye is pinned with no bushing rotation.
* The damper rod slides and the coil spring compresses along its axis (correct for those
  parts); nothing else in the assembly is scaled to fake travel.
* The recessed inspection channel in the road is a deliberate set-design device so the camera
  can pass beneath the truck; it is 0.88 m wide and 0.55 m deep, and the wheels still run on
  continuous road tracks either side.
* The road surface is real geometry (analytic bumps sampled at 60 mm) rather than a texture,
  so the tyre/road contact check is meaningful, but the mesh is a polyline approximation of
  the analytic curve (sub-millimetre error on the flanks).
* Tyres are rigid; the true contact patch deformation is approximated by the small float
  reported above.
* Weathering is restrained on purpose (procedural noise bump and roughness variation only);
  no dirt, decals, badges or real-manufacturer marks exist anywhere in the model.
* 461 objects and ~140 k triangles; the model is built for mechanical readability and for the
  framed shots, not for arbitrary close-up hero detail on every fastener.

## Inspection aids

`qa/*.png` are produced by `scripts/qa_views.py`, a ray-casting geometry viewer written with
`mathutils.bvhtree` + a small PNG writer. It exists only because Blender's renderer must not
be invoked in this iteration: it lets the model be inspected (silhouettes, panel breaks,
which component sits where, colour-coded by collection) without touching any render setting
or producing any deliverable imagery. These are **not** rendered frames of the film and are
not part of the deliverable.

## Provenance

Everything here was authored locally in this workspace with Blender's bundled Python.
No downloaded vehicle models, asset packs, paid generation, external hosting or add-ons were
used, and no image/video rendering was performed.
