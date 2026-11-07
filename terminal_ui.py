"""UnlockAbz terminal styling, inspired by WlanAbz. Standard library only."""
import os
import shutil
import sys
import time

TTY = sys.stdout.isatty()
COLOR = TTY and 'NO_COLOR' not in os.environ
LOGO = r'''
 _   _       _            _        _    _
| | | |_ __ | | ___   ___| | __   / \  | |__  ____
| | | | '_ \| |/ _ \ / __| |/ /  / _ \ | '_ \|_  /
| |_| | | | | | (_) | (__|   <  / ___ \| |_) |/ /
 \___/|_| |_|_|\___/ \___|_|\_\/_/   \_\_.__//___|
'''.strip('\n').splitlines()
SUBTITLE = 'Password Recovery Tool by Abz'

def paint(text, code='36'):
    return f'\033[{code}m{text}\033[0m' if COLOR else text

def clear_screen():
    if TTY:
        print('\033[2J\033[H', end='', flush=True)

def logo_lines():
    return LOGO if shutil.get_terminal_size().columns >= max(map(len, LOGO)) + 4 else ['UnlockAbz']

def banner(title='BOSH MENYU'):
    width = max(16, min(57, shutil.get_terminal_size().columns - 4))
    print()
    for line in logo_lines():
        print('  ' + paint(line, '1;96'))
    print(paint('  ' + '=' * width, '1;32'))
    print(paint('  ' + SUBTITLE, '1;32'))
    print(paint('  ' + '=' * width, '1;32'))
    print('\n  ' + paint(title, '1;37'))
    print(paint('  ' + '─' * width, '90') + '\n')

def item(number, text, code='36'):
    print('  ' + paint(number, '1;' + code) + '   ' + text)

def ask(prompt='Tanlov'):
    return input(paint(f'\n  {prompt}: ', '1;36')).strip()

def pause():
    input(paint('\n  Davom etish uchun Enter... ', '90'))

def intro_animation():
    if not TTY or not COLOR:
        return
    lines = logo_lines()
    width, height = shutil.get_terminal_size()
    left = max(0, (width - max(map(len, lines))) // 2)
    top = max(0, (height - len(lines) - 3) // 2)
    try:
        print('\033[?25l', end='', flush=True)
        for step in range(1, len(lines) + 1):
            clear_screen()
            print('\n' * top, end='')
            for line in lines[:step]:
                print(' ' * left + paint(line, '1;96'))
            time.sleep(.08)
        print('\n' + ' ' * max(0, (width - len(SUBTITLE)) // 2) + paint(SUBTITLE, '1;32'))
        time.sleep(.4)
    finally:
        print('\033[?25h', end='', flush=True)
    clear_screen()

def progress_text(job, label):
    done, total = job.get('progress', [0, 0])
    if not total:
        return f'{"⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[int(time.monotonic()*4)%10]} {label}'
    fraction = max(0, min(1, done / total))
    size = 18 if shutil.get_terminal_size().columns >= 70 else 8
    filled = int(size * fraction)
    bar = '━' * filled + '─' * (size - filled)
    text = f'[{bar}] {fraction*100:6.2f}%  |  {job.get("speed",0):,.0f} taxmin/s'
    if job.get('estimated'):
        seconds = max(0, int(job['estimated'] - time.time()))
        days, rest = divmod(seconds, 86400)
        hours, rest = divmod(rest, 3600)
        minutes = rest // 60
        text += f'  |  ~{days}k {hours}s {minutes}m' if days else f'  |  ~{hours}s {minutes}m'
    return text
