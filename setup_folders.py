#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re

# Read tree.md
with open('tree.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract folders
folders_pattern = r'- `([^`]+)/`'
folders = re.findall(folders_pattern, content)

videos_dir = 'videos'
os.makedirs(videos_dir, exist_ok=True)

result = []
for folder in folders:
    folder_path = os.path.join(videos_dir, folder)
    os.makedirs(folder_path, exist_ok=True)
    result.append(folder_path)

# Save result
with open('folders_result.txt', 'w', encoding='utf-8') as f:
    f.write(f'Created {len(result)} folders:\n')
    for path in result:
        f.write(f'{path}\n')

print('Done')

