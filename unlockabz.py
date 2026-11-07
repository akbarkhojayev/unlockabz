#!/usr/bin/env python3
"""UnlockAbz: local terminal interface for authorized password recovery."""
import argparse
from contextlib import contextmanager
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid

import engine
from terminal_ui import (TTY, paint, clear_screen, banner, item, ask, pause,
                         intro_animation, progress_text)

BASE = Path(__file__).resolve().parent
VERSION = '2.0.0'
STATES = {
    'preparing': 'Tayyorlanmoqda', 'running': 'Tekshirilmoqda',
    'found': 'PAROL TOPILDI', 'partial': 'AYRIM PAROLLAR TOPILDI',
    'exhausted': 'Ro‘yxatda topilmadi', 'cancelled': 'To‘xtatildi', 'error': 'Xato',
}

@contextmanager
def exclusive():
    """Serialize recovery, device probing and cleanup across app instances."""
    root = BASE / '.local'
    root.mkdir(exist_ok=True, mode=0o700)
    with (root / 'unlockabz.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Boshqa UnlockAbz tekshiruvi ishlayapti. Avval uni tugating yoki to‘xtating.') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def cleanup_job(directory):
    if directory.is_symlink():
        return
    for path in directory.iterdir():
        disposable = (path.name in ('data', '.cache', '.local', 'input.hash', 'recovered.raw')
                      or path.name.startswith('upload.'))
        if disposable:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)


def cleanup_all():
    with exclusive():
        count = 0
        root = BASE / 'jobs'
        if root.is_dir() and not root.is_symlink():
            for directory in root.iterdir():
                if directory.is_dir() and not directory.is_symlink():
                    cleanup_job(directory)
                    count += 1
        print(paint(f'  [+] {count} ta tekshiruvning vaqtinchalik fayllari tozalandi.', '32'))
        print('  Parollar, ochilgan hujjatlar va hisobotlar saqlandi.')


def doctor():
    print('  Muhit       : ' + sys.platform + ' / Python ' + sys.version.split()[0])
    missing = []
    for name, description in [('hashcat', 'Tekshirish'), ('7z', 'Office hash olish'),
                              ('hcxpcapngtool', 'CAP/PCAP konvertatsiya')]:
        found = shutil.which(name)
        print(paint(f'  [{"+" if found else "!"}] {name:<16} {description}: {found or "topilmadi"}', '32' if found else '33'))
        if not found:
            missing.append(name)
    office = importlib.util.find_spec('msoffcrypto') is not None
    print(f'  [{"+" if office else "!"}] Office ochish     : {"tayyor" if office else "msoffcrypto-tool kerak"}')
    print(f'  [{"+" if engine.NUMBERS_SMALL.is_file() else "!"}] 1–9999 ro‘yxati   : {engine.NUMBERS_SMALL}')
    print('  [+] 8 xonali sonlar   : Hashcat mask, arxivni ochish shart emas')
    if missing or not office:
        print('\n  Kerakli paketlarni o‘rnatish: ./install.sh')
    print('  GPU/CPU ro‘yxati: ./unlockabz --devices')
    return 1 if not shutil.which('hashcat') else 0


def devices():
    if not shutil.which('hashcat'):
        raise ValueError('Hashcat topilmadi. ./install.sh ishga tushiring.')
    with exclusive():
        return subprocess.run(['hashcat', '-I'], env=engine.environment(), check=False).returncode


def normalize_path(text):
    text = text.strip()
    # Preserve ordinary unquoted paths containing spaces; decode shell drag/drop escaping.
    if Path(text).expanduser().is_file():
        return Path(text).expanduser().resolve()
    try:
        parts = shlex.split(text)
        if len(parts) == 1:
            text = parts[0]
    except ValueError:
        pass
    return Path(text).expanduser().resolve()


def stop(job, sig=signal.SIGTERM):
    with engine.LOCK:
        job['cancel'].set()
        proc = job.get('process')
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                pass


def recover(source, choice, workload=2):
    source = normalize_path(str(source))
    if not source.is_file():
        raise ValueError(f'Fayl topilmadi: {source}')
    if source.suffix.lower() not in engine.SUPPORTED:
        raise ValueError('Qo‘llanadigan formatlar: DOCX/XLSX/PPTX, HC22000, CAP/PCAP/PCAPNG.')
    if choice not in engine.LISTS:
        raise ValueError('Noma’lum parollar ro‘yxati.')
    if choice == 'numbers1to9999' and source.suffix.lower() in engine.WPA:
        raise ValueError('WPA paroli kamida 8 belgi. 8 xonali sonlar (--list numbers8) tanlang.')
    engine.attack_arguments(choice)
    if not shutil.which('hashcat'):
        raise ValueError('Hashcat topilmadi. ./install.sh ishga tushiring.')
    with exclusive():
        jid = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
        directory = BASE / 'jobs' / jid
        directory.mkdir(parents=True, mode=0o700)
        job = dict(id=jid, name=source.name, input_path=str(source), list=choice,
                   workload=workload, state='preparing', progress=[0, 0], speed=0,
                   log=[], passwords=[], directory=directory, source=source,
                   cancel=threading.Event())
        label, count = engine.LISTS[choice]
        print(f'  Fayl     : {source.name}\n  Ro‘yxat  : {label} ({count:,} variant)')
        print(f'  Yuklama  : {workload}\n  Natijalar: {directory}')
        print('\n  Ctrl+C — to‘xtatish. Qayta tekshiruv boshidan boshlanadi.\n')
        thread = threading.Thread(target=engine.worker, args=(job,), daemon=True)
        thread.start()
        last_report = 0
        try:
            while thread.is_alive():
                status = progress_text(job, STATES.get(job['state'], job['state']))
                if TTY:
                    width = max(15, shutil.get_terminal_size().columns - 3)
                    print('\r\033[2K  ' + paint(status[:width]), end='', flush=True)
                elif time.monotonic() - last_report > 10:
                    print('  ' + status, flush=True)
                    last_report = time.monotonic()
                thread.join(.25)
        except KeyboardInterrupt:
            print('\n  To‘xtatilmoqda...')
            stop(job)
            try:
                thread.join(10)
                if thread.is_alive():
                    stop(job, signal.SIGKILL)
                    thread.join(55)
            except KeyboardInterrupt:
                stop(job, signal.SIGKILL)
                thread.join(55)
        if thread.is_alive():
            raise ValueError('Jarayon hali tugamadi. Natijalar va vaqtinchalik fayllar saqlandi.')
        print('\n')
        color = '1;32' if job['state'] in ('found', 'partial') else '1;31' if job['state'] == 'error' else '1;33'
        print('  ' + paint(STATES.get(job['state'], job['state']), color))
        if job.get('error'):
            print('  [-] ' + job['error'])
            for line in job['log'][-12:]:
                print('  ' + line)
        for password in job['passwords']:
            print(paint(f'  [+] Parol: {password}', '1;32'))
        if job.get('unlocked'):
            print('  Ochilgan fayl: ' + str(directory / job['unlocked']))
        if job.get('warning'):
            print(paint('  [!] ' + job['warning'], '33'))
        if job['state'] == 'exhausted':
            print('  Parol shu ro‘yxatda topilmadi. Boshqa parol bo‘lishi mumkin.')
        if job.get('estimated') and job['state'] == 'cancelled':
            print('  Hisoblangan taxminiy muddat bekor qilindi.')
        cleanup_job(directory)
        print(f'  Hisobot: {directory / "result.json"}\n')
        return 130 if job['state'] == 'cancelled' else 1 if job['state'] == 'error' else 0


def results():
    root = BASE / 'jobs'
    reports = sorted(root.glob('*/result.json'), reverse=True) if root.exists() else []
    print(f'  Papka: {root}\n')
    if not reports:
        print('  Hali tekshiruv natijalari yo‘q.')
    for report in reports[:15]:
        try:
            record = json.loads(report.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        state = STATES.get(record.get('state'), 'Noma’lum')
        print(paint('  ' + record.get('name', '?'), '1;37'))
        print(f'    {record.get("finished", "")} · {state}')
        print(f'    {report.parent}')
    print('\n  Parollar: passwords.txt. Ochilgan hujjat: unlocked.*.')
    print('  Asl fayllar o‘zgarmaydi. Batafsil qo‘llanma: README.md.')


def interactive(args):
    if not args.no_animation:
        intro_animation()
    while True:
        clear_screen()
        banner()
        item('1', 'Fayl / handshake tekshirish', '32')
        item('2', 'Qurilmalar va tizim holati')
        item('3', 'Vaqtinchalik fayllarni tozalash', '33')
        item('4', 'Oldingi natijalar va yordam')
        item('0', 'Chiqish', '37')
        action = ask()
        if action == '0':
            clear_screen()
            print('  UnlockAbz yopildi.')
            return 0
        if action not in ('1', '2', '3', '4'):
            continue
        clear_screen()
        try:
            if action == '2':
                banner('QURILMALAR VA TIZIM')
                doctor()
                print()
                devices()
            elif action == '3':
                banner('TOZALASH')
                cleanup_all()
            elif action == '4':
                banner('NATIJALAR VA YORDAM')
                results()
            else:
                banner('YANGI TEKSHIRUV')
                print('  Office: DOCX / XLSX / PPTX. WPA: HC22000 / CAP / PCAP / PCAPNG.')
                print('  Faylni terminalga sudrang yoki yo‘lini kiriting.')
                print('  Faqat ruxsat berilgan fayl va tarmoqlarni tekshiring.\n')
                source = ask('Fayl yo‘li (0 — orqaga)')
                if source == '0':
                    continue
                path = normalize_path(source)
                if not path.is_file():
                    raise ValueError(f'Fayl topilmadi: {path}')
                is_wpa = path.suffix.lower() in engine.WPA
                print()
                item('1', '1–9999          · 9 999 variant' + (' · WPA uchun mos emas' if is_wpa else ''), '90' if is_wpa else '32')
                item('2', '8 xonali sonlar · 90 000 000 variant', '32' if is_wpa else '36')
                item('0', 'Orqaga', '37')
                default = '2' if is_wpa else '1'
                choice = ask(f'Ro‘yxat [{default}]') or default
                if choice == '0':
                    continue
                if choice not in ('1', '2'):
                    raise ValueError('1 yoki 2 ni tanlang.')
                clear_screen()
                banner('TEKSHIRUV')
                recover(path, 'numbers1to9999' if choice == '1' else 'numbers8', args.workload)
        except KeyboardInterrupt:
            print('\n  Menyuga qaytildi.')
        except (ValueError, OSError) as exc:
            print(paint(f'\n  [-] {exc}', '31'))
        pause()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description='UnlockAbz — Office va WPA parollarini terminalda tiklash')
    parser.add_argument('file', nargs='?', help='Office fayli yoki handshake yo‘li')
    parser.add_argument('--list', choices=list(engine.LISTS), default=None)
    parser.add_argument('--workload', type=int, choices=(1, 2, 3), default=2,
                        help='1 — yengil, 2 — odatiy, 3 — kuchli yuklama')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--devices', action='store_true', help='Hashcat qurilmalari')
    actions.add_argument('--doctor', action='store_true', help='Kerakli paketlar holati')
    actions.add_argument('--results', action='store_true', help='Oldingi tekshiruvlar')
    actions.add_argument('--clean', action='store_true', help='Faqat vaqtinchalik fayllarni tozalash')
    parser.add_argument('--no-animation', action='store_true')
    parser.add_argument('--version', action='version', version='UnlockAbz ' + VERSION)
    args = parser.parse_args()
    if args.file and any((args.devices, args.doctor, args.results, args.clean)):
        parser.error('Fayl bilan --devices/--doctor/--results/--clean birga ishlatilmaydi.')
    if args.list and not args.file:
        parser.error('--list uchun fayl yo‘lini ham kiriting.')
    if args.devices:
        return devices()
    if args.doctor:
        return doctor()
    if args.results:
        results()
        return 0
    if args.clean:
        cleanup_all()
        return 0
    if args.file:
        banner('TEKSHIRUV')
        choice = args.list or ('numbers8' if normalize_path(args.file).suffix.lower() in engine.WPA else 'numbers1to9999')
        return recover(args.file, choice, args.workload)
    return interactive(args)

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print('\n  Chiqildi.')
        sys.exit(130)
    except (ValueError, OSError) as exc:
        print(paint(f'  [-] {exc}', '31'), file=sys.stderr)
        sys.exit(1)
