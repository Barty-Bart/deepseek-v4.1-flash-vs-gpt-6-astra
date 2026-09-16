# Kestrel 4×4 — engine bay and extended suspension inspection

Open **pickup_truck_v2.blend** for the revised editable scene and animation. The sequence runs **498 frames at 24 fps, or 20.75 seconds**. It starts in the open engine bay, pans out, closes the hood, and joins the original driving sequence. A second rear-axle view holds for **2.5 seconds while the truck continues driving**, before the original final pullaway.

**No images, video or frame sequences have been rendered.** Only ordinary solid viewport inspection was used. The accepted `pickup_truck.blend`, original scripts and original reports remain unchanged. Everything is authored locally; the scene needs no external assets, paid tools or runtime Python handlers.

## Opening and playback

Use Blender 5.2.1 LTS. The file opens at frame 1 in a full-vehicle three-quarter viewport with its hood open. Press Numpad 0 for the active camera, `CAM_ANIMATION_V2 | engine and dual rear inspection`, then Space to play or scrub the timeline. Viewport playback speed depends on the machine.

The original scale and collection organization are preserved: meters, +X forward, +Z up and −Y vehicle right; 3.2 m wheelbase, 1.66 m track, 0.405 m rolling radius and approximately 5.3 × 1.9 × 1.85 m body. Components, meshes, materials, constraints, drivers and leaf shape keys remain editable.

## Timeline

| Frames | Action |
| --- | --- |
| 1–48 | Open-hood engine inspection with moving accessory drive and cooling fan. Truck parked. |
| 49–84 | Pan out to show the whole truck and raised hood. |
| 85–108 | Hood closes from 68° to its latched position; gas struts telescope. |
| 109–132 | Smooth acceleration and camera handoff to the accepted shot. |
| 133–324 | Original frames 1–192: side profile, front arc, underside and rear-right suspension. |
| 325–360 | Camera travels through the inspection channel toward the additional rear view. |
| **361–420** | **60-frame / 2.5-second hold** ahead of and below the rear axle. Truck travels at 3 m/s over two bumps. Both leaves, dampers, hubs, axle, differential, shackles and driveshaft are exposed. |
| 421–450 | Camera exits the inspection channel. |
| 451–498 | Original frames 193–240: rear three-quarter pullaway, relocated along the longer drive. |

The retained sections preserve the original truck-relative camera samples. Added transitions use eased paths and quaternion interpolation, baked into native keys. The camera stays fixed relative to the truck during the new hold; vehicle and mechanical animation continue throughout it. Timeline markers identify each segment and the new road-bump cycles.

The original four `INSPECT_01` through `INSPECT_04` cameras remain available. Two additional cameras follow the truck: `INSPECT_05_ENGINE_BAY` and `INSPECT_06_REAR_AXLE_AND_DRIVESHAFT`. After inspecting with another camera, restore the active v2 animation camera for eventual output.

## Added detail and controls

The engine bay includes wheelhouses, battery and cables, airbox and intake, fluid reservoirs, coolant hoses, ignition coils and wiring, fuel rail, service caps, accessory pulleys, a continuous tangent belt and a cooling fan with shroud. The hood has insulation, reinforcement ribs, hinge hardware, latch and two telescoping support struts. The engine top end and service components fit beneath the closed hood.

Both rear shackles pivot, and the leaf ends follow their moving eyes while the leaf centers remain attached to the axle saddles. The rear driveshaft has rotating witness bands, articulated universal-yoke detail, flanges and a slip sleeve. Rear bump stops and inspection fill lighting are added. Wheel spin, axle motion and shock travel remain linked to vehicle travel and the road profile.

Select controls in the RIG collection and expand Custom Properties in Object Properties. Enable viewport overlays to display helpers.

| Control | Behavior |
| --- | --- |
| `CTRL_HOOD_OPEN` → `open_deg` | 0° is closed; opening animation holds at 68° and closes during frames 85–108. |
| `CTRL_ENGINE_ACCESSORIES` → `demonstration_rpm`, `fan_rpm` | Crank-pulley demonstration speed is 60 rpm; the other pulleys follow their radius ratios. Fan speed is 90 rpm, deliberately slowed for readability at 24 fps. Belt-marker travel is baked at the supplied accessory speed. When changing the speed, update `belt_speed` in the build script too, then rebuild to keep belt and pulleys synchronized. |
| `CTRL_VEHICLE_TRAVEL` | `travel_m`, `steering_deg`, `body_heave_m`, `body_pitch_deg`, `body_roll_deg` and `wheel_rotation_offset_deg` retain their original roles. |
| `CTRL_SUSPENSION_FL`, `FR`, `RL`, `RR` → `travel_m` | Per-wheel travel in meters relative to body heave. Positive values compress the suspension. |
| `CTRL_BODY_HEAVE_PITCH_ROLL`, `CTRL_WHEEL_ROTATION_*`, `RIG_REAR_SOLID_AXLE` | Native driven body, wheel and solid-axle transforms. |
| `RIG_REAR_SHACKLE_RL`, `RR`, `Rear moving leaf eye RL/RR` | Driven shackle pivots and leaf attachment targets. |
| `RIG_REAR_PROPSHAFT_ROTATION` | Shaft witness rotation follows wheel travel at a fixed 3.73 ratio. |

Keyed properties restore their animation values when scrubbing. Mute or remove the relevant keys for manual posing. To change the road, driving profile or shot, edit `scripts/build_truck_v2.py` and rebuild from the preserved original. Keep the road geometry and contact keys synchronized.

## Verification and limits

All **19 checks pass** in `reports/v2/verification.json`, using a separate background process to reopen the saved scene. `evaluated_frames.json` records all 498 poses, camera-clearance samples and camera angular steps. `camera_samples.json` and `original_camera_snapshot.json` preserve the revised and accepted camera data.

- Wheel-center contact-envelope error is below **0.028 mm**, and wheel spin error below **0.000004 radians**, across all 498 output frames.
- Suspension remains within approximately **−22.2 to +66.9 mm**, inside the requested ±80 mm limit.
- During the new hold, rear-right travel spans **−17.6 to +59.8 mm**. Its shock length changes by **37.8 mm** and shackle angle spans approximately **5.29–17.67°**. Rear-left shock and shackle motion also continue. Frames **378** and **386** are the new hold's rear-right rebound and compression extremes.
- Link endpoints remain within **0.001 mm**, leaf centers within **0.012 mm** of their saddles, and moving leaf eyes within **0.008 mm** of their targets. Shackle spans remain rigid.
- The sampled camera point stays at least **89 mm** from visible mesh geometry. The nearest point is the hitch tongue during the retained pullaway. The clearance scan covers a 150 mm neighborhood at each output frame; 150 mm results are lower bounds. This is a camera-point check, not a full frustum or subframe collision proof.
- Evaluated triangle intersections find no closed-hood contact with engine components, and no hood contact with the cowl, windshield, wheelhouses or fender hardware at six opening/closing checkpoints. Solid viewport views confirm the opening, wide hood positions, rear suspension extrema, late hold and final composition.
- Mesh ray casts confirm the required engine groups and new rear mechanical groups are visible across the inspection samples. Components can naturally occlude one another; they are not all fully visible from every position. Whole-vehicle framing passes at the wide-shot checkpoints.
- Native object and shape-key drivers are valid. The original `.blend` SHA256 remains `077f035f0202dffc63b8c8433709b1fabbf69f36698949d46cf4ae2929a68ffd`.

This is a kinematic visual demonstration. It does not simulate combustion, internal differential gears, physical shackle equilibrium, interleaf friction, tire deformation or exact universal-joint bearing motion. The original wishbone length accommodation and simplified hoses remain. Tire contact uses a rolling-circle envelope; rigid tread corners can slightly enter the road. The original report measured about 0.3–3.2 mm tread penetration at its sampled poses; v2 checks the contact envelope throughout the extended drive rather than claiming a new full tire-surface test. Wheel spin uses longitudinal distance, and shaft rotation uses a constant ratio. The engine accessory speeds are demonstration values.

The accepted camera choreography is retained, including its largest measured angular step of about **23° at revised frame 260**. Added transitions use eased interpolation. Lighting, glass, motion appearance and final image quality remain unverified by rendering.

## Prepared output and reproduction

Eevee, 1920 × 1080 at 100%, 24 fps, frames 1–498, AgX; original 64 output samples and 32 viewport samples retained. Motion blur and depth of field remain disabled for inspection readability. PNG output is configured at `//renders/kestrel_v2_` for later use. No output sequence has been created.

Run these commands from this project directory. Rebuilding replaces only generated **v2**; save manual v2 edits under another name first. Keep the original `.blend` and original helper scripts alongside these files. The finalizer embeds this README, the passing report, and the v2 scripts in the Blender file; inherited v1 documentation is labeled as historical.

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python scripts/build_truck_v2.py
/Applications/Blender.app/Contents/MacOS/Blender --background pickup_truck_v2.blend --python-exit-code 1 --python scripts/verify_truck_v2.py
/Applications/Blender.app/Contents/MacOS/Blender --background pickup_truck_v2.blend --python-exit-code 1 --python scripts/finalize_truck_v2.py
```

The optional `scripts/viewport_inspect_v2.py` runs in a separate GUI Blender process and captures ordinary solid viewports to `/tmp`. It does not render or save the scene. Build and verification process timings are in their JSON reports; measured revision wall time is recorded in `reports/v2/session_timing.json`.
