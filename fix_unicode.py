import pathlib

replacements = {
    '\u2713': '[OK]',
    '\u2717': '[FAIL]',
    '\u26A0': '[WARN]',
    '\u2022': '*',
    '\u2014': '--',
    '\u2013': '-',
    '\u2018': "'",
    '\u2019': "'",
    '\u201C': '"',
    '\u201D': '"',
    '\u2192': '->',
    '\u2190': '<-',
    '\u2194': '<->',
    '\u21D2': '=>',
    '\u21D4': '<=>',
    '\u2191': '^',
    '\u2193': 'v',
    '\u00D7': 'x',
    '\u2015': '-',
    '\u2500': '-',
    '\u2550': '=',
    '\u21E8': '>>',
    '\u21E6': '<<',
    '\u2764': '<3',
    '\u2605': '*',
    '\u25CF': '*',
    '\u25CB': 'o',
    '\u2588': '#',
    '\u25A0': '#',
    '\u2591': '.',
}

files = [
    'notebooks/01_eda.py',
    'notebooks/02_preprocessing.py',
]

for fp in files:
    p = pathlib.Path(fp)
    text = p.read_text(encoding='utf-8')
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Replace any remaining non-ASCII in print statements
    p.write_text(text, encoding='utf-8')
    print(f'Fixed {fp}')

print('Done')
