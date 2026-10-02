#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
python ydisk_video_downloader.py --verbose https://disk.yandex.ru/d/HqNb3UrUTxHO0Q
