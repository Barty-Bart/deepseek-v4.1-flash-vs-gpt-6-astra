"""Procedural material set - no external texture files are required."""
from . import util as U

def build():
    m = {}
    m['paint'] = U.material('Paint_ForestGreen', (0.055, 0.115, 0.070), rough=0.40,
                            metal=0.15, coat=0.35, coat_rough=0.18, spec=0.55)
    U.noise_bump(m['paint'], scale=170.0, strength=0.06, detail=2.0, rough_var=0.02)
    m['paint_dark'] = U.material('Trim_SatinBlack', (0.026, 0.028, 0.030), rough=0.55,
                                 metal=0.0, coat=0.12)
    m['plastic'] = U.material('Plastic_Black', (0.030, 0.031, 0.033), rough=0.62)
    m['plastic_rough'] = U.material('Plastic_Grained', (0.035, 0.036, 0.038), rough=0.78)
    m['glass'] = U.material('Glass_Tinted', (0.115, 0.145, 0.150), rough=0.026,
                            metal=0.0, ior=1.52, alpha=0.55, transmission=0.72, spec=0.62)
    if hasattr(m['glass'], 'use_raytrace_refraction'):
        m['glass'].use_raytrace_refraction = True
    if hasattr(m['glass'], 'surface_render_method'):
        m['glass'].surface_render_method = 'BLENDED'
    m['chrome'] = U.material('Metal_Brushed', (0.62, 0.615, 0.60), rough=0.30, metal=1.0)
    m['aluminium'] = U.material('Metal_Aluminium', (0.72, 0.73, 0.75), rough=0.38, metal=1.0)
    m['steel'] = U.material('Metal_Steel', (0.42, 0.43, 0.45), rough=0.45, metal=1.0)
    m['alloy'] = U.material('Wheel_Alloy', (0.47, 0.48, 0.50), rough=0.32, metal=1.0)
    m['brake_steel'] = U.material('Brake_Rotor', (0.34, 0.33, 0.32), rough=0.42, metal=1.0)
    m['brake_steel2'] = m['brake_steel']
    m['caliper'] = U.material('Brake_Caliper', (0.30, 0.055, 0.045), rough=0.44,
                              metal=0.25)
    m['rubber'] = U.material('Rubber_Tyre', (0.026, 0.026, 0.028), rough=0.86)
    m['hose'] = U.material('Rubber_Hose', (0.030, 0.030, 0.032), rough=0.80)
    m['boot'] = U.material('Rubber_CV_Boot', (0.038, 0.038, 0.040), rough=0.78)
    m['lamp_warm'] = U.material('Lamp_LED_Warm', (0.85, 0.86, 0.88), rough=0.12,
                                emission=(1.0, 0.86, 0.62), emission_strength=5.0)
    m['lamp_white'] = U.material('Lamp_Daytime', (0.85, 0.86, 0.88), rough=0.12,
                                 emission=(1.0, 0.95, 0.86), emission_strength=7.0)
    m['lamp_tail'] = U.material('Lamp_Tail', (0.32, 0.03, 0.03), rough=0.14,
                                emission=(0.95, 0.10, 0.05), emission_strength=2.4)
    m['lens'] = U.material('Lamp_Lens', (0.55, 0.56, 0.58), rough=0.06, alpha=0.35,
                           transmission=0.7)
    m['interior'] = U.material('Interior_Trim', (0.055, 0.056, 0.060), rough=0.72)
    m['seat'] = U.material('Interior_Seat', (0.075, 0.076, 0.082), rough=0.90, sheen=0.3)
    m['frame'] = U.material('Chassis_Frame', (0.048, 0.048, 0.051), rough=0.66)
    m['underbody'] = U.material('Underbody_Sealer', (0.058, 0.054, 0.048), rough=0.88)
    U.noise_bump(m['underbody'], scale=60.0, strength=0.30, detail=3.0)
    m['exhaust'] = U.material('Exhaust_Steel', (0.50, 0.49, 0.47), rough=0.44, metal=0.95)
    m['heatshield'] = U.material('Heat_Shield', (0.66, 0.66, 0.67), rough=0.48, metal=1.0)
    m['tank'] = U.material('Fuel_Tank', (0.045, 0.046, 0.048), rough=0.70)
    m['bedliner'] = U.material('Bed_Liner', (0.040, 0.041, 0.044), rough=0.94)
    U.noise_bump(m['bedliner'], scale=120.0, strength=0.35, detail=4.0)
    m['asphalt'] = U.material('Road_Asphalt', (0.108, 0.109, 0.114), rough=0.93)
    U.noise_bump(m['asphalt'], scale=260.0, strength=0.10, detail=5.0, rough_var=0.04)
    m['gravel'] = U.material('Road_Shoulder', (0.235, 0.229, 0.216), rough=0.95)
    U.noise_bump(m['gravel'], scale=180.0, strength=0.15, detail=5.0)
    m['channel'] = U.material('Road_InspectionChannel', (0.055, 0.056, 0.060), rough=0.90)
    m['channel_detail'] = U.material('Road_ChannelDetail', (0.13, 0.13, 0.14),
                                     rough=0.55, metal=0.7)
    m['concrete'] = U.material('Concrete', (0.245, 0.240, 0.228), rough=0.92)
    m['structure'] = U.material('Structure_Far', (0.105, 0.108, 0.112), rough=0.95)
    m['berm'] = U.material('Earth_Berm', (0.145, 0.138, 0.120), rough=0.97)
    m['marking'] = U.material('Road_Marking', (0.72, 0.70, 0.66), rough=0.85)
    return m
