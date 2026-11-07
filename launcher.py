"""Create a terminal shortcut for the current checkout location."""
from pathlib import Path
base = Path(__file__).resolve().parent
# Desktop Exec quoting differs from shell quoting.
def quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'
path = base / 'UnlockAbz.desktop'
path.write_text('[Desktop Entry]\nType=Application\nName=UnlockAbz\nComment=Terminalda parol tiklash\nExec=' + quote(base / 'unlockabz') + '\nTerminal=true\nIcon=utilities-terminal\nCategories=Utility;\n')
path.chmod(0o755)
