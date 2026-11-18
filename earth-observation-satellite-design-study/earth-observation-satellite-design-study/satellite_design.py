"""Earth-Observation Satellite Design & Interactive Visualisation.

Preliminary sizing study using illustrative, unvalidated assumptions.
Run with: py satellite_design.py
Only Python's standard library is required. Outputs are saved beside this file.
Orbit timing is prescribed, not calculated from altitude. Design life is metadata;
battery/array end-of-life factors are prescribed, not derived from life.
No imaging performance, hardware selection, thermal analysis, transient power,
attitude-dependent generation or battery power capability is validated here.
"""

import csv
import json
import math
from pathlib import Path

# STUDY INPUTS: masses in kg, powers in W, times in minutes.
# Inactive loads are zero. Imaging/downlink occur only in sunlight.
# Thermal duty cycles are schedule assumptions, not a thermal-model result.
# Battery specific energy is pack-level; panels include backing structure.
# Avoid counting the same structure/deployment hardware in two mass entries.
MISSION_NAME = "Earth-Observation Satellite Design Study"

TARGET_MASS_KG = 150.0

ORBIT_ALTITUDE_KM = 550.0

DESIGN_LIFE_YEARS = 3

subsystem_masses_kg = {
    "Payload": 20.0,
    "Structure and mechanisms": 25.0,
    "Attitude determination and control": 12.0,
    "Electrical power system": 22.0,
    "Communications": 8.0,
    "On-board computer": 5.0,
    "Thermal control": 7.0,
    "Propulsion hardware": 10.0,
    "Harness": 6.0,
}

MASS_CONTINGENCY_FRACTION = 0.20

PROPELLANT_MASS_KG = 8.0

subsystem_power = {
    "Payload": (80.0, 0.20),
    "Attitude determination and control": (25.0, 1.00),
    "Communications": (60.0, 0.15),
    "On-board computer": (15.0, 1.00),
    "Thermal control": (30.0, 0.40),
    "Power-system housekeeping": (5.0, 1.00),
}

POWER_CONTINGENCY_FRACTION = 0.20

# Phase durations for the 550 km circular orbit at zero solar beta angle.
SUNLIGHT_MIN = 60.03839

ECLIPSE_MIN = 35.61149

DISCHARGE_PATH_EFFICIENCY = 0.90

MAX_DEPTH_OF_DISCHARGE = 0.30

END_OF_LIFE_CAPACITY_FRACTION = 0.80

CHARGE_PATH_EFFICIENCY = 0.90

ARRAY_TO_BUS_EFFICIENCY = 0.90

SOLAR_IRRADIANCE_W_M2 = 1361.0

CELL_EFFICIENCY = 0.30

CELL_COVERAGE_FRACTION = 0.90

TEMPERATURE_FACTOR = 0.90

ARRAY_END_OF_LIFE_FACTOR = 0.80

SUN_INCIDENCE_ANGLE_DEG = 25.0

BATTERY_PACK_SPECIFIC_ENERGY_WH_KG = 100.0

PANEL_AREAL_MASS_KG_M2 = 5.0

OTHER_EPS_MASS_KG = 6.0

payload_options = {
    "A: Baseline camera": {"mass_kg": 20.0, "power_w": 80.0},
    "B: Higher-demand camera": {"mass_kg": 35.0, "power_w": 140.0},
    "C: Reduced-mass camera": {"mass_kg": 32.0, "power_w": 140.0},
}

def operating_schedule():
    """Convert orbit-wide duties into sunlight/eclipse phase duties."""
    orbit_min = SUNLIGHT_MIN + ECLIPSE_MIN
    if SUNLIGHT_MIN <= 0 or ECLIPSE_MIN <= 0:
        raise ValueError('Sunlight and eclipse durations must be positive.')
    sun = {name: duty for name, (_, duty) in subsystem_power.items()}
    eclipse = sun.copy()
    for name in ('Payload', 'Communications'):
        sun[name] = subsystem_power[name][1] * orbit_min / SUNLIGHT_MIN
        eclipse[name] = 0.0
    sun['Thermal control'] = 0.05
    eclipse['Thermal control'] = (
        subsystem_power['Thermal control'][1] * orbit_min
        - sun['Thermal control'] * SUNLIGHT_MIN
    ) / ECLIPSE_MIN
    for phase in (sun, eclipse):
        for name, duty in phase.items():
            if not math.isfinite(duty) or not 0 <= duty <= 1:
                raise ValueError(f'Infeasible phase duty for {name}: {duty}')
    return sun, eclipse


def calculate_configuration(name, payload_mass_kg, payload_power_w):
    """Use one sizing method for every payload configuration."""
    if any(not math.isfinite(v) or v < 0
           for v in (payload_mass_kg, payload_power_w)):
        raise ValueError('Payload mass and power must be finite and non-negative.')
    for value in (DISCHARGE_PATH_EFFICIENCY, MAX_DEPTH_OF_DISCHARGE,
                  END_OF_LIFE_CAPACITY_FRACTION, CHARGE_PATH_EFFICIENCY,
                  ARRAY_TO_BUS_EFFICIENCY, CELL_EFFICIENCY,
                  CELL_COVERAGE_FRACTION, TEMPERATURE_FACTOR,
                  ARRAY_END_OF_LIFE_FACTOR):
        if not 0 < value <= 1:
            raise ValueError('Efficiencies and usable fractions must be in (0, 1].')
    if not 0 <= SUN_INCIDENCE_ANGLE_DEG < 90:
        raise ValueError('Sun incidence angle must be in [0, 90) degrees.')
    if BATTERY_PACK_SPECIFIC_ENERGY_WH_KG <= 0:
        raise ValueError('Battery specific energy must be positive.')

    sun_duty, eclipse_duty = operating_schedule()
    powers = {key: value[0] for key, value in subsystem_power.items()}
    powers['Payload'] = payload_power_w
    sun_w = sum(powers[key] * duty for key, duty in sun_duty.items())
    eclipse_w = sum(powers[key] * duty for key, duty in eclipse_duty.items())
    sun_h, eclipse_h = SUNLIGHT_MIN / 60, ECLIPSE_MIN / 60
    contingency = 1 + POWER_CONTINGENCY_FRACTION
    eclipse_wh = eclipse_w * eclipse_h
    battery_wh = eclipse_wh * contingency / (
        DISCHARGE_PATH_EFFICIENCY * MAX_DEPTH_OF_DISCHARGE
        * END_OF_LIFE_CAPACITY_FRACTION
    )
    recharge_wh = eclipse_wh * contingency / (
        DISCHARGE_PATH_EFFICIENCY * CHARGE_PATH_EFFICIENCY
    )
    array_w = (sun_w * contingency + recharge_wh / sun_h) / ARRAY_TO_BUS_EFFICIENCY
    density = (SOLAR_IRRADIANCE_W_M2 * CELL_EFFICIENCY * CELL_COVERAGE_FRACTION
               * TEMPERATURE_FACTOR * ARRAY_END_OF_LIFE_FACTOR
               * math.cos(math.radians(SUN_INCIDENCE_ANGLE_DEG)))
    area = array_w / density
    battery_mass = battery_wh / BATTERY_PACK_SPECIFIC_ENERGY_WH_KG
    panel_mass = area * PANEL_AREAL_MASS_KG_M2
    eps_mass = battery_mass + panel_mass + OTHER_EPS_MASS_KG
    masses = subsystem_masses_kg.copy()
    masses['Payload'] = payload_mass_kg
    masses['Electrical power system'] = eps_mass
    dry_mass = sum(masses.values())
    wet_mass = dry_mass * (1 + MASS_CONTINGENCY_FRACTION) + PROPELLANT_MASS_KG
    headroom = TARGET_MASS_KG - wet_mass
    return {
        'name': name,
        'payload_mass_kg': payload_mass_kg,
        'payload_power_w': payload_power_w,
        'sunlight_average_w': sun_w,
        'eclipse_average_w': eclipse_w,
        'orbit_average_w': (sun_w * sun_h + eclipse_w * eclipse_h) / (sun_h + eclipse_h),
        'eclipse_energy_wh': eclipse_wh,
        'battery_capacity_wh': battery_wh,
        'battery_recharge_energy_wh': recharge_wh,
        'array_output_w': array_w,
        'panel_area_m2': area,
        'battery_mass_kg': battery_mass,
        'panel_mass_kg': panel_mass,
        'eps_mass_kg': eps_mass,
        'estimated_dry_mass_kg': dry_mass,
        'mass_contingency_kg': dry_mass * MASS_CONTINGENCY_FRACTION,
        'wet_mass_kg': wet_mass,
        'mass_headroom_kg': headroom,
        'simultaneous_load_w': sum(powers.values()) * contingency,
        'mass_target_pass': headroom >= -1e-9,
        'subsystem_masses_kg': masses,
    }


def maximum_payload_mass(payload_power_w):
    """Solve the mass constraint at a fixed payload operating power."""
    zero_payload = calculate_configuration('Mass-limit calculation', 0, payload_power_w)
    return ((TARGET_MASS_KG - PROPELLANT_MASS_KG)
            / (1 + MASS_CONTINGENCY_FRACTION)
            - zero_payload['estimated_dry_mass_kg'])


def check_results(results):
    """Check schedule/energy closure and the payload mass-limit solution."""
    for result in results:
        expected_average = sum(
            (result['payload_power_w'] if key == 'Payload' else power) * duty
            for key, (power, duty) in subsystem_power.items()
        )
        if not math.isclose(result['orbit_average_w'], expected_average, abs_tol=1e-9):
            raise RuntimeError('Orbit-average demand is inconsistent with duty cycles.')
        available_wh = (result['array_output_w'] * ARRAY_TO_BUS_EFFICIENCY
                        * SUNLIGHT_MIN / 60)
        required_wh = (result['sunlight_average_w'] * (1 + POWER_CONTINGENCY_FRACTION)
                       * SUNLIGHT_MIN / 60 + result['battery_recharge_energy_wh'])
        if not math.isclose(available_wh, required_wh, abs_tol=1e-9):
            raise RuntimeError('Sunlight energy balance does not close.')
    limit = maximum_payload_mass(140.0)
    boundary = calculate_configuration('Boundary', limit, 140.0)
    if not math.isclose(boundary['wet_mass_kg'], TARGET_MASS_KG, abs_tol=1e-9):
        raise RuntimeError('Payload mass-limit solution does not close.')


def export_results(results):
    """Write CSV for tables and JSON for later visualisation integration."""
    output_dir = Path(__file__).resolve().parent / 'outputs'
    output_dir.mkdir(exist_ok=True)
    csv_path = output_dir / 'configuration_comparison.csv'
    fields = [key for key in results[0] if key != 'subsystem_masses_kg']
    with csv_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    assumptions = {key: value for key, value in globals().items()
                   if key.isupper() and isinstance(value, (str, float, int))}
    assumptions['subsystem_masses_kg'] = subsystem_masses_kg
    assumptions['subsystem_power_w_and_orbit_duty'] = subsystem_power
    assumptions['sunlight_duty_cycles'], assumptions['eclipse_duty_cycles'] = operating_schedule()
    json_path = output_dir / 'satellite_design_results.json'
    document = {
        'schema_version': 1,
        'model_status': 'Illustrative preliminary sizing; hardware assumptions unvalidated',
        'assumptions': assumptions,
        'configurations': results,
        'maximum_payload_mass_at_140_w_kg': maximum_payload_mass(140),
    }
    json_path.write_text(json.dumps(document, indent=2, allow_nan=False), encoding='utf-8')
    return csv_path, json_path


def main():
    print(MISSION_NAME)
    print(f'Target mass: {TARGET_MASS_KG:.1f} kg | Orbit: {ORBIT_ALTITUDE_KM:.0f} km')
    print('Preliminary sizing using illustrative assumptions.\n')
    results = [calculate_configuration(name, item['mass_kg'], item['power_w'])
               for name, item in payload_options.items()]
    check_results(results)
    for result in results:
        print(result['name'])
        for label, key, unit, precision in (
            ('Orbit-average demand', 'orbit_average_w', 'W', 2),
            ('Battery capacity', 'battery_capacity_wh', 'Wh', 2),
            ('Required array output', 'array_output_w', 'W', 2),
            ('Panel area', 'panel_area_m2', 'm2', 3),
            ('EPS mass', 'eps_mass_kg', 'kg', 2),
            ('Budgeted wet mass', 'wet_mass_kg', 'kg', 2),
            ('Mass headroom', 'mass_headroom_kg', 'kg', 2),
            ('Simultaneous load with contingency', 'simultaneous_load_w', 'W', 1),
        ):
            print(f"  {label}: {result[key]:.{precision}f} {unit}")
        print('  Mass target: ' + ('PASS' if result['mass_target_pass'] else 'FAIL'))
        print()
    print(f'Maximum payload mass at 140 W: {maximum_payload_mass(140):.2f} kg')
    print('All internal consistency checks passed.')
    for path in export_results(results):
        print(f'Saved: {path}')


if __name__ == '__main__':
    main()
