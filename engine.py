#!/usr/bin/env python3
"""Hashcat recovery engine for the local terminal tool."""
import base64
import json
import time
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
LOCK = threading.Lock()
NUMBERS_SMALL = BASE / 'numbers-1-9999.txt'

OFFICE = {'.docx', '.xlsx', '.pptx'}
CAPTURE = {'.cap', '.pcap', '.pcapng'}
WPA = CAPTURE | {'.hc22000'}
SUPPORTED = OFFICE | WPA
LISTS = {
    'numbers1to9999': ('1–9999', 9999),
    'numbers8': ('8 xonali sonlar', 90000000),
}

def environment():
    cache = BASE / '.local' / 'hashcat'
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = os.environ.copy()
    env.update(HOME=str(cache), XDG_DATA_HOME=str(cache / 'data'))
    return env

def attack_arguments(choice):
    if choice == 'numbers1to9999':
        if not NUMBERS_SMALL.is_file():
            raise ValueError(f'Ro‘yxat topilmadi: {NUMBERS_SMALL}')
        return ['-a', '0', str(NUMBERS_SMALL)]
    if choice == 'numbers8':
        return ['-a', '3', '-1', '123456789', '?1?d?d?d?d?d?d?d']
    raise ValueError('Noma’lum parollar ro‘yxati.')

def save_report(job):
    target = job['directory'] / 'result.json'
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(public(job), ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(target)


def command(args, directory, timeout=60):
    return subprocess.check_output(args, cwd=directory, stderr=subprocess.STDOUT, timeout=timeout)

def extract_hash(source, directory):
    suffix = source.suffix.lower()
    target = directory / 'input.hash'
    if suffix == '.hc22000':
        lines = []
        with source.open(encoding='ascii') as handle:
            for line in handle:
                if len(line) > 8192:
                    raise ValueError('HC22000 yozuvi haddan tashqari uzun.')
                if line.strip():
                    lines.append(line.strip())
                if len(lines) > 100:
                    raise ValueError('HC22000 faylda ko‘pi bilan 100 yozuv bo‘lsin.')
        if not lines or len(lines) > 100:
            raise ValueError('HC22000 faylda 1–100 yozuv bo‘lishi kerak.')
        def hex_field(value, length=None):
            return bool(re.fullmatch(r'[0-9a-fA-F]+', value)) and len(value) % 2 == 0 and (length is None or len(value) == length)
        for line in lines:
            fields = line.split('*')
            if len(fields) != 9 or fields[0] != 'WPA' or fields[1] not in ('01', '02'):
                raise ValueError('HC22000 yozuvining tuzilishi noto‘g‘ri.')
            if not all(hex_field(fields[i], size) for i, size in ((2, 32), (3, 12), (4, 12))):
                raise ValueError('HC22000 MIC/PMKID yoki MAC maydoni noto‘g‘ri.')
            if fields[5] and (not hex_field(fields[5]) or len(fields[5]) > 64):
                raise ValueError('HC22000 tarmoq nomi (ESSID) noto‘g‘ri.')
            if fields[1] == '02' and not (hex_field(fields[6], 64) and hex_field(fields[7]) and hex_field(fields[8], 2)):
                raise ValueError('HC22000 EAPOL ma’lumotlari noto‘g‘ri.')
        target.write_text('\n'.join(lines) + '\n')
        return target, '22000'
    if suffix in ('.cap', '.pcap', '.pcapng'):
        tool = shutil.which('hcxpcapngtool')
        if not tool:
            raise ValueError('Konvertor o‘rnatilmagan: sudo apt-get install hcxtools. Yoki .hc22000 yuklang.')
        command([tool, '-o', str(target), str(source)], directory)
        if not target.exists() or not target.stat().st_size:
            raise ValueError('Capture ichidan tekshiriladigan WPA handshake topilmadi.')
        return target, '22000'
    if suffix not in ('.docx', '.xlsx', '.pptx'):
        raise ValueError('Qo‘llanadigan formatlar: DOCX/XLSX/PPTX (Office Agile), HC22000, CAP/PCAP/PCAPNG.')
    try:
        data = command(['7z', 'e', '-so', str(source), 'EncryptionInfo'], directory)
    except subprocess.CalledProcessError:
        raise ValueError('Office shifrlash ma’lumoti o‘qilmadi. Fayl ochiq, buzilgan yoki qo‘llanmaydigan formatda bo‘lishi mumkin.') from None
    if data[:4] != b'\x04\x00\x04\x00':
        raise ValueError('Office Agile shifrlangan fayl kerak. Bu shifrlash turi qo‘llanmaydi.')
    key = ET.fromstring(data[8:]).find('.//{http://schemas.microsoft.com/office/2006/keyEncryptor/password}encryptedKey')
    if key is None:
        raise ValueError('Office parol ma’lumoti topilmadi.')
    k = key.attrib
    config = (k['hashAlgorithm'].upper(), k['keyBits'], k['cipherAlgorithm'], k['cipherChaining'])
    if config == ('SHA512', '256', 'AES', 'ChainingModeCBC'):
        year, mode = '2013', '9600'
    elif config == ('SHA1', '128', 'AES', 'ChainingModeCBC'):
        year, mode = '2010', '9500'
    else:
        raise ValueError('Bu Office shifrlash parametrlari qo‘llanmaydi.')
    dec = lambda name: base64.b64decode(k[name], validate=True)
    salt = dec('saltValue')
    if len(salt) != 16 or len(dec('encryptedVerifierHashInput')) != 16 or len(dec('encryptedVerifierHashValue')) < 32 or not 0 < int(k['spinCount']) <= 10000000:
        raise ValueError('Office shifrlash ma’lumotlari yaroqsiz.')
    target.write_text(f"$office$*{year}*{k['spinCount']}*{k['keyBits']}*{len(salt)}*{salt.hex()}*{dec('encryptedVerifierHashInput').hex()}*{dec('encryptedVerifierHashValue')[:32].hex()}\n")
    return target, mode

def public(job):
    return {k: v for k, v in job.items() if k not in ('process', 'directory', 'source', 'cancel')}

def worker(job):
    directory = job['directory']
    job['started'] = time.strftime('%Y-%m-%d %H:%M:%S')
    try:
        if not shutil.which('hashcat'):
            raise ValueError('Hashcat o‘rnatilmagan. ./install.sh ishga tushiring.')
        if job['source'].suffix.lower() in OFFICE and not shutil.which('7z'):
            raise ValueError('7zip topilmadi. ./install.sh ishga tushiring.')
        if job['cancel'].is_set():
            job['state'] = 'cancelled'
            return
        hashfile, mode = extract_hash(job['source'], directory)
        job['mode'] = mode
        env = environment()
        common = ['hashcat', '-m', mode, str(hashfile), '--potfile-path', str(directory / 'passwords.pot')]
        args = common + attack_arguments(job['list']) + [
            '-w', str(job.get('workload', 2)), '--status', '--status-json',
            '--status-timer', '2', '--quiet', '--restore-disable',
            '--outfile', str(directory / 'recovered.raw'), '--outfile-format', '2']
        with LOCK:
            if job['cancel'].is_set():
                job['state'] = 'cancelled'
                return
            job['state'] = 'running'
            proc = subprocess.Popen(args, cwd=directory, env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, errors='replace', start_new_session=True)
            job['process'] = proc
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                info = json.loads(line)
                if isinstance(info, dict) and 'progress' in info:
                    job['progress'] = info['progress']
                    job['speed'] = sum(d.get('speed', 0) for d in info.get('devices', []))
                    job['estimated'] = info.get('estimated_stop')
                    job['recovered'] = info.get('recovered_hashes', [0, 1])
                    continue
            except (ValueError, TypeError):
                pass
            job['log'] = (job['log'] + [line])[-80:]
        code = proc.wait()
        job['exit_code'] = code
        result = subprocess.check_output(common + ['--show', '--outfile-format', '2'],
                                         cwd=directory, env=env, timeout=30)
        passwords = []
        for raw in result.splitlines():
            if raw.startswith(b'$HEX[') and raw.endswith(b']'):
                raw = bytes.fromhex(raw[5:-1].decode('ascii'))
            passwords.append(raw.decode('utf-8', errors='replace'))
        job['passwords'] = list(dict.fromkeys(passwords))
        if passwords:
            (directory / 'passwords.txt').write_text('\n'.join(job['passwords']) + '\n', encoding='utf-8')
        if job['cancel'].is_set():
            job['state'] = 'cancelled'
        elif code not in (0, 1):
            raise ValueError(f'Hashcat xatosi (kod {code}). Qurilma va quyidagi jurnalni tekshiring.')
        elif passwords:
            job['state'] = 'found' if code == 0 else 'partial'
        else:
            job['state'] = 'exhausted'
        if passwords and mode != '22000':
            target = directory / ('unlocked' + job['source'].suffix.lower())
            temp = target.with_suffix('.tmp')
            try:
                import msoffcrypto
                with job['source'].open('rb') as inp, temp.open('wb') as dest:
                    doc = msoffcrypto.OfficeFile(inp)
                    doc.load_key(password=passwords[0], verify_password=True)
                    doc.decrypt(dest)
                temp.replace(target)
                job['unlocked'] = target.name
            except Exception as exc:
                job['warning'] = 'Parol topildi, ochiq nusxa yaratilmadi: ' + str(exc)
            finally:
                temp.unlink(missing_ok=True)
    except subprocess.TimeoutExpired:
        job['error'], job['state'] = 'Tayyorlash yoki natijani o‘qish vaqti tugadi.', 'error'
    except Exception as exc:
        job['error'], job['state'] = str(exc), 'error'
    finally:
        job.pop('process', None)
        job['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            save_report(job)
        except OSError as exc:
            job['error'] = 'Hisobot yozilmadi: ' + str(exc)
            job['state'] = 'error'
