#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
umask 077
export PYTHONDONTWRITEBYTECODE=1
check_only=false
if [[ "${1:-}" == --check ]]; then
  check_only=true
elif [[ $# -gt 0 ]]; then
  echo 'Foydalanish: ./install.sh [--check]' >&2
  exit 2
fi
packages=()
command -v python3 >/dev/null || packages+=(python3)
command -v hashcat >/dev/null || packages+=(hashcat)
command -v 7z >/dev/null || packages+=(7zip)
command -v hcxpcapngtool >/dev/null || packages+=(hcxtools)
# An existing GPU ICD also satisfies this check; do not replace it with CPU-only setup.
shopt -s nullglob
icds=(/etc/OpenCL/vendors/*.icd)
[[ ${#icds[@]} -gt 0 ]] || packages+=(pocl-opencl-icd)
venv_ready=false
if [[ -x .venv/bin/python ]] && .venv/bin/python -c 'import sys; assert sys.version_info >= (3,10)' 2>/dev/null; then
  venv_ready=true
fi
if ! "$venv_ready"; then
  if ! command -v python3 >/dev/null || ! python3 -c 'import venv, ensurepip' 2>/dev/null; then
    packages+=(python3-venv)
  fi
fi
library_ready=false
if "$venv_ready" && .venv/bin/python -c 'import msoffcrypto; from importlib.metadata import version; v=tuple(int(x) for x in version("msoffcrypto-tool").split(".")[:2]); assert (5,4) <= v < (6,0)' 2>/dev/null; then
  library_ready=true
fi
if "$check_only"; then
  [[ ${#packages[@]} -eq 0 ]] && "$venv_ready" && "$library_ready"
  exit $?
fi
trap 'echo "[UnlockAbz] O‘rnatish tugamadi. Internet, paket menejeri va yuqoridagi xatoni tekshirib, ./start.sh ni qayta ishga tushiring." >&2' ERR
if [[ ${#packages[@]} -gt 0 ]]; then
  if ! command -v apt-get >/dev/null; then
    echo '[UnlockAbz] Avtomatik o‘rnatish Ubuntu/Kali/Debian uchun.' >&2
    echo "Yetishmagan paketlar: ${packages[*]}" >&2
    exit 1
  fi
  if [[ "$(id -u)" -eq 0 ]]; then
    package_cmd=(apt-get)
  else
    if ! command -v sudo >/dev/null; then
      echo '[UnlockAbz] Tizim paketlari uchun sudo yoki administrator kerak.' >&2
      exit 1
    fi
    package_cmd=(sudo apt-get)
  fi
  echo "[UnlockAbz] Yetishmagan paketlar: ${packages[*]}"
  "${package_cmd[@]}" update
  "${package_cmd[@]}" install -y "${packages[@]}"
fi
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ kerak"'
if ! "$venv_ready"; then
  echo '[UnlockAbz] Python muhiti tayyorlanmoqda...'
  python3 -m venv .venv
fi
if ! "$library_ready"; then
  echo '[UnlockAbz] Office kutubxonasi o‘rnatilmoqda...'
  .venv/bin/python -m pip install -r requirements.txt
fi
.venv/bin/python launcher.py
if ! ./install.sh --check; then
  echo '[UnlockAbz] Ayrim komponentlar hali tayyor emas. ./unlockabz --doctor orqali tekshiring.' >&2
  exit 1
fi
echo '[UnlockAbz] Barcha komponentlar tayyor.'
