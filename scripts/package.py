#!/usr/bin/env python3
"""Export only public source files; never collect user inputs or results."""
from pathlib import Path
import zipfile

BASE = Path(__file__).resolve().parents[1]
FILES = [
    '.gitignore', '.gitattributes', '.editorconfig', 'README.md',
    'CONTRIBUTING.md', 'requirements.txt', 'start.sh', 'install.sh',
    'unlockabz', 'unlockabz.py', 'engine.py', 'terminal_ui.py',
    'launcher.py', 'numbers-1-9999.txt', 'tests/test_unlockabz.py',
    'scripts/package.py',
]

def main():
    for name in FILES:
        path = BASE / name
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f'Missing or symlinked source file: {name}')
    output = BASE / 'dist' / 'UnlockAbz-github.zip'
    output.parent.mkdir(exist_ok=True)
    temp = output.with_suffix('.tmp')
    with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(BASE / name, 'UnlockAbz/' + name)
    temp.replace(output)
    print(f'{output} ({output.stat().st_size:,} bytes)')

if __name__ == '__main__':
    main()
