# Kestrel 4×4 — editable pickup and mechanical inspection shot

`pickup_truck.blend` contains an original forest-green, crew-cab expedition pickup, its native animation rig, an industrial test road, lighting, and a continuous camera shot. **No image, video, or animation rendering has been performed.** The saved file opens at frame 1 in a useful full-vehicle three-quarter viewport.

Everything was authored locally with Blender Python. There are no downloaded models, external asset packs, paid tools, external textures, or runtime Python handlers. Procedural materials and the built-in font require no external resources. Construction source is also embedded as a Blender text block.

## Opening and playback

Open `pickup_truck.blend` in Blender 5.2.1 LTS. Press Numpad 0 for the animated camera and Space to play, or scrub frames 1–240. Actual viewport playback speed depends on the machine; frame evaluation is deterministic.

The scene uses meters, +X forward, +Z up, and **−Y as vehicle right**. Wheel centers are 3.2 m apart longitudinally, with a 1.66 m track and 0.405 m rolling radius. The body is approximately 5.3 × 1.9 × 1.85 m. Mirrors, the hitch, and roof rails extend beyond that envelope. The bed is open, and the five-seat interior is modeled behind thick glazing.

The main collections are BODY, INTERIOR, CHASSIS, DRIVETRAIN, FRONT_SUSPENSION, REAR_SUSPENSION, WHEELS, RIG, ROAD, CAMERAS, and LIGHTS. Body panels, glazing, bolts, suspension components, tires, tread meshes, wheel spokes, and drivetrain parts remain separate and editable. Small bevels and leaf deformation remain live.

## Controls

Select controls in the RIG collection and expand Custom Properties in Object Properties. The opening viewport hides helper displays and relationship lines for clarity; enable overlays to see them.

| Control | Editable properties and behavior |
| --- | --- |
| `CTRL_VEHICLE_TRAVEL` | `travel_m` drives forward translation and wheel spin. `steering_deg` steers both front carriers. `body_heave_m`, `body_pitch_deg`, and `body_roll_deg` move the sprung body and its mounts. `wheel_rotation_offset_deg` changes the common starting wheel angle. |
| `CTRL_BODY_HEAVE_PITCH_ROLL` | Driven transform for the body, chassis, engine, and their attachment points. Adjust the corresponding master properties. |
| `CTRL_SUSPENSION_FL`, `FR`, `RL`, `RR` | Each has `travel_m`: displacement relative to body heave, in meters. Positive values compress the suspension. |
| `CTRL_WHEEL_ROTATION_FL`, `FR`, `RL`, `RR` | Native driven wheel spin. Angle equals traveled distance divided by rolling radius, plus the master offset. |
| `RIG_REAR_SOLID_AXLE` | Height and roll derive from the two rear travel controls. Differential, axle hardware, brakes, and rear wheel carriers move together. |
| `Leaf local deformation target RL/RR` | Constraint-derived saddle positions in body coordinates. Three native shape-key channels keep each five-leaf pack attached while it flexes. |

The main travel, steering, body, and suspension properties have keys on every frame. For a manual pose, remove or mute animation on the particular property before adjusting it; otherwise scrubbing restores its keyed value. To revise the road or driving profile, edit `BUMPS`, `ground()`, and `pose()` in the build script and rebuild so the road and wheel-contact animation stay synchronized.

Linkages use native endpoint constraints and distance drivers. The front coil springs shorten with their dampers. The rear has **leaf springs and separate dampers only**. Chrome damper rods slide into fixed-length outer bodies. The rear driveshaft continuously aims between the transfer-case output and moving differential pinion.

## Shot and inspection cameras

| Frames | Prepared camera action |
| --- | --- |
| 1–48 | Low side tracking shot; whole truck visible. |
| 49–84 | Front three-quarter arc, followed by descent ahead of the bumper into the channel. |
| 85–144 | Underside scan from the front suspension through the drivetrain to the rear axle. |
| 145–192 | Stable rear-right suspension view from a rear/inboard position. Frame 158 is the local rebound extreme; frame 165 is maximum compression. |
| 193–240 | Smooth rear three-quarter pullout; the truck continues away and finishes wholly in frame. |

`CAM_ANIMATION | continuous 10 second inspection` is the active shot camera. Its position, orientation, and focal length are saved on every frame. Smooth Hermite paths are sampled into dense keys; linear interpolation between those samples prevents overshoot. No camera cuts or runtime scripts are needed.

Four additional cameras follow vehicle travel: `INSPECT_01_FULL_TRUCK`, `INSPECT_02_UNDERSIDE_OVERVIEW`, `INSPECT_03_FRONT_SUSPENSION`, and `INSPECT_04_REAR_RIGHT_SUSPENSION`. Select one and use Ctrl–Numpad 0 to inspect through it. Restore `CAM_ANIMATION` before eventual output.

Two continuous concrete wheel tracks flank an open recessed inspection channel. The camera enters ahead of the truck, moves below the chassis, and exits behind the rear axle. The tires stay on their tracks. Additional broad fill lights reveal the undercarriage during future output; those lights are invisible light objects, not cards covering the mechanism.

## Prepared output settings

- Eevee, 1920 × 1080 at 100%, 24 fps, frames 1–240: exactly 240 output frames / 10 seconds.
- 64 output samples, 32 viewport samples, AgX, soft daylight and underside fill.
- Screen-space ray tracing enabled, half-resolution tracing, denoising, 0.5 trace quality, 0.03 m trace thickness.
- Motion blur and depth of field disabled to keep the mechanism readable.
- PNG output configured at `//renders/kestrel_`; no render folder or output sequence has been created.

The last sample is at 239/24 seconds. At 3 m/s, the sampled travel from frame 1 to 240 is 29.875 m; the 240-frame output duration is 10 seconds.

## Verification

`reports/verification.json` contains the machine-readable results from reopening the saved scene in a separate background Blender process. `reports/evaluated_frames.json` records all 240 evaluated poses and camera clearance checks. `reports/tire_surface_contact.json` records evaluated tire-surface checks at representative frames and both rear-right extremes.

The verified mechanical results are:

- Wheel-center contact-envelope error below **0.028 mm**, and wheel spin error below **0.000004 radians** relative to distance/radius, over all 240 frames.
- Wheel travel approximately **−17.7 to +66.9 mm**; body heave approximately **0.3 to 18.6 mm**.
- Rear-right travel approximately **−13.1 to +66.9 mm** during the close-up. Its shock changes length by approximately **36.9 mm**, with visible compression and rebound.
- The rigid rear axle preserves its span. Driven linkage endpoint errors are below **0.001 mm**. The main rear-right leaf center stays within approximately **0.012 mm** of its saddle.
- Camera-to-mesh clearance exceeds **90 mm** at every output frame. A 150 mm neighborhood is checked around the lens; values reported as 150 mm are lower bounds, not exact distant clearances.
- The complete vehicle fits in the establishing and final compositions. Evaluated mesh ray casts confirm the hub, leaf pack, shock body, shock shaft, and rear axle are visible at both rear-right extremes. The undercarriage sweep exposes the engine sump, transmission, transfer case, differentials, shafts, frame rails, fuel tank, exhaust, muffler, rack, and front suspension.
- Solid viewport inspection checked the full vehicle and representative underside, rear suspension, and ending views. This uses the ordinary viewport, not image rendering.

Verification distinguishes modeled geometry and evaluated movement from final image quality. Lighting, glass appearance, and temporal image quality remain **unverified by rendering**, as requested.

## Deliberate simplifications

This is a visually credible kinematic demonstration, not an engineering simulation. The road-contact solver uses a rolling-circle terrain envelope. Tires remain rigid: evaluated tread surfaces penetrate by approximately **0.3–3.2 mm**, primarily from tread corners and rear-axle camber. There is no deforming contact patch, tire slip model, or dynamic friction simulation. Wheel spin follows longitudinal distance rather than integrating the small extra distance over each bump.

The wishbones accommodate at most about **1.5%** length variation over the supplied motion instead of solving an exact four-bar linkage. Leaf packs use smooth vertex flex with fixed spring eyes; shackle motion and interleaf friction are simplified. Driveshafts aim correctly but do not simulate internal joint bearings, shaft spin, or a detailed sliding spline. Hose deformation is simplified. Steering is provided as a posing control and stays straight in the verified animation. The engine and transmission are recognizable exterior assemblies without internal moving parts.

Some components naturally occlude one another. The driveshaft is inspected during the underside pass, then sits behind the differential in the rear-right close-up. No parts disappear or become transparent to manufacture visibility.

## Reproducing the scene

Run from this project directory. Rebuilding intentionally replaces this project's generated `pickup_truck.blend`; save any manual edits under another filename first.

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python scripts/build_truck.py
/Applications/Blender.app/Contents/MacOS/Blender --background pickup_truck.blend --python-exit-code 1 --python scripts/verify_scene.py
/Applications/Blender.app/Contents/MacOS/Blender --background pickup_truck.blend --python-exit-code 1 --python scripts/finalize_scene.py
```

`-- --rig-only` after the build command constructs the simple prototype and checks its contact behavior before fine detail. The original prototype verification is preserved in `reports/rig_prototype.json`. `scripts/viewport_inspect.py` is an optional GUI-only solid-viewport inspection utility; its temporary screenshots go to `/tmp`, and it does not invoke rendering. All normal construction and verification commands above run independently of any other open Blender document.

Construction and verification process durations are recorded in the JSON reports. The measured work interval is recorded in `reports/session_timing.json`.
