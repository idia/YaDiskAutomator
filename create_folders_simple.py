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

created = []
for folder in folders:
    folder_path = os.path.join(videos_dir, folder)
    os.makedirs(folder_path, exist_ok=True)
    created.append(folder_path)

# Write result to file
with open('folders_created.txt', 'w', encoding='utf-8') as f:
    f.write(f'Created {len(created)} folders:\n')
    for path in created:
        f.write(f'{path}\n')

print(f'Created {len(created)} folders in videos/')

