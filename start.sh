#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export PYTHONDONTWRITEBYTECODE=1
if ! ./install.sh --check; then
  echo '[UnlockAbz] Yetishmagan komponentlar avtomatik o‘rnatiladi.'
  ./install.sh
fi
exec .venv/bin/python unlockabz.py "$@"
