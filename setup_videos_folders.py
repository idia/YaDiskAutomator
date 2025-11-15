#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

folders = [
    'Замещающий ребенок',
    'Курс "Вашу мать: исследование материнского интроекта"',
    'Отец',
    'Привязанность',
    'Секреты',
    'Сепарационная тревога',
    'Тень',
    'Трансгенерационное',
    'Фин сценарии'
]

videos_dir = 'videos'
os.makedirs(videos_dir, exist_ok=True)

for folder in folders:
    folder_path = os.path.join(videos_dir, folder)
    os.makedirs(folder_path, exist_ok=True)

# Проверка
existing = [d for d in os.listdir(videos_dir) if os.path.isdir(os.path.join(videos_dir, d))]
print(f"Created {len(existing)} folders in videos/")

