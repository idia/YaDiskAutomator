#!/bin/bash
# Заливка из папки 2upload на Яндекс.Диск и перенос в uploaded/ (через Python в venv).
#
# Вариант A — файл лежит внутри YaDiskAutomator (рядом с upload_2upload_to_yandex.py):
#   REPO="$(cd "$(dirname "$0")" && pwd)"
#
# Вариант B — .command на Рабочем столе: ниже в else подставьте путь к YaDiskAutomator.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/upload_2upload_to_yandex.py" ]]; then
  REPO="$SCRIPT_DIR"
else
  REPO="/Users/tatiyanalobanova/YaDiskAutomator"
fi

YANDEX_PATH="/Videos/Downloaded"

cd "$REPO"
PY="$REPO/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

exec "$PY" "$REPO/upload_2upload_to_yandex.py" -p "$YANDEX_PATH" --move --verbose
