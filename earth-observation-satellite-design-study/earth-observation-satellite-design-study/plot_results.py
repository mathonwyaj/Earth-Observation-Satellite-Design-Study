"""Plot exported spacecraft configuration results.

Place beside satellite_design.py. Run: py plot_results.py
Requires matplotlib. Reads JSON only; does not rerun or change the model.
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


def main():
    output_dir = Path(__file__).resolve().parent / 'outputs'
    source = output_dir / 'satellite_design_results.json'
    if not source.exists():
        raise SystemExit('Results not found. Run: py satellite_design.py first.')
    document = json.loads(source.read_text(encoding='utf-8'))
    results = document['configurations']
    if not results:
        raise SystemExit('The results file contains no configurations.')
    target = document['assumptions']['TARGET_MASS_KG']
    names = [item['name'].replace(': ', ':\n', 1) for item in results]
    colors = ['#187A70' if item['mass_target_pass'] else '#C45C38'
              for item in results]
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'figure.facecolor': 'white'})
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    metrics = [
        ('wet_mass_kg', 'Budgeted spacecraft wet mass', 'Mass (kg)', 2),
        ('array_output_w', 'Required solar-array output', 'Power (W)', 2),
        ('panel_area_m2', 'Required total solar-panel area', 'Area (m²)', 3),
        ('simultaneous_load_w', 'Simultaneous load including contingency', 'Power (W)', 1),
    ]
    for ax, (key, title, unit, digits) in zip(axes.flat, metrics):
        values = [item[key] for item in results]
        bars = ax.bar(names, values, color=colors, width=0.57)
        ax.bar_label(bars, labels=[f'{v:.{digits}f}' for v in values], padding=5)
        ax.set_title(title, loc='left', fontweight='bold', pad=12)
        ax.set_ylabel(unit)
        upper = max(values + ([target] if key == 'wet_mass_kg' else []))
        ax.set_ylim(0, max(upper * 1.22, 1))
        ax.set_axisbelow(True)
        ax.grid(axis='y', alpha=0.18)
        if key == 'wet_mass_kg':
            ax.axhline(target, color='#3E4754', linestyle='--', linewidth=1.4)
            ax.text(0.02, 0.94, f'Dashed line: {target:g} kg target',
                    ha='left', va='top', transform=ax.transAxes, fontsize=9)
    fig.suptitle('Earth-observation satellite: payload configuration comparison',
                 fontsize=16, fontweight='bold', y=0.98)
    fig.legend(handles=[Patch(color='#187A70', label='Meets mass target'),
                        Patch(color='#C45C38', label='Exceeds mass target')],
               loc='upper center', bbox_to_anchor=(0.5, 0.943), ncol=2, frameon=False)
    fig.text(0.5, 0.025,
             'Illustrative preliminary sizing • Colours indicate mass compliance only.\n'
             'Power capability, imaging performance and hardware feasibility remain unvalidated.',
             ha='center', fontsize=9, color='#555555')
    fig.tight_layout(rect=(0.02, 0.075, 0.98, 0.90), h_pad=2.2)
    for extension in ('png', 'pdf'):
        destination = output_dir / f'configuration_comparison.{extension}'
        fig.savefig(destination, dpi=200, facecolor='white')
        print(f'Saved: {destination}')
    print('Close the chart window to return to the terminal.')
    plt.show()


if __name__ == '__main__':
    main()
