"""Run with: py sensitivity_analysis.py
Place beside satellite_design.py. Requires matplotlib.
Angles are exploratory scenarios, not an established mission operating envelope.
"""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import satellite_design as model


def main():
    rows = []
    original_angle = model.SUN_INCIDENCE_ANGLE_DEG
    # Explicit options make this study independent of edits to payload_options.
    options = [('A', 20.0, 80.0), ('B', 35.0, 140.0), ('C', 32.0, 140.0)]
    try:
        for angle in range(0, 61):
            model.SUN_INCIDENCE_ANGLE_DEG = float(angle)
            for name, mass, power in options:
                result = model.calculate_configuration(name, mass, power)
                rows.append({'configuration': name, 'sun_angle_deg': angle,
                             'panel_area_m2': result['panel_area_m2'],
                             'wet_mass_kg': result['wet_mass_kg'],
                             'mass_headroom_kg': result['mass_headroom_kg']})
    finally:
        model.SUN_INCIDENCE_ANGLE_DEG = original_angle

    destination = Path(__file__).resolve().parent / 'outputs'
    destination.mkdir(exist_ok=True)
    with (destination / 'sun_angle_sensitivity.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print('EXPLORATORY SUN-ANGLE SENSITIVITY')
    print('Angle is measured from panel normal; all other assumptions stay fixed.')
    print('Arrays are resized for each angle; these are alternative designs.')
    print('\nConfig | Angle | Panel area | Wet mass | Headroom')
    for row in rows:
        if row['sun_angle_deg'] in (0, 25, 45, 60):
            print(f"{row['configuration']:>6} | {row['sun_angle_deg']:>3} deg | "
                  f"{row['panel_area_m2']:.3f} m2 | {row['wet_mass_kg']:.2f} kg | "
                  f"{row['mass_headroom_kg']:.2f} kg")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for name, _, _ in options:
        subset = [row for row in rows if row['configuration'] == name]
        angles = [row['sun_angle_deg'] for row in subset]
        axes[0].plot(angles, [row['wet_mass_kg'] for row in subset], label=name)
        axes[1].plot(angles, [row['panel_area_m2'] for row in subset], label=name)
    axes[0].axhline(model.TARGET_MASS_KG, color='black', linestyle='--', label='Mass target')
    axes[0].set_ylabel('Budgeted wet mass (kg)')
    axes[1].set_ylabel('Required total panel area (m²)')
    for ax in axes:
        ax.set_xlabel('Sun angle from panel normal (degrees)')
        ax.axvline(25, color='gray', linestyle=':', label='Baseline angle')
        ax.grid(alpha=0.2)
        ax.legend()
    fig.suptitle('Sun-angle sensitivity: panels resized for each design case')
    fig.text(0.5, 0.02, 'Illustrative assumptions; B and C have identical panel-area curves.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 0.93))
    for extension in ('png', 'pdf'):
        fig.savefig(destination / f'sun_angle_sensitivity.{extension}', dpi=200)
    print('\nSaved CSV, PNG and PDF in outputs. Close the plot to return to the terminal.')
    plt.show()


if __name__ == '__main__':
    main()
