#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re

# Read tree.md
script_dir = os.path.dirname(os.path.abspath(__file__))
tree_file = os.path.join(script_dir, 'tree.md')

with open(tree_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract folders from "Папки" section
folders_pattern = r'- `([^`]+)/`'
folders = re.findall(folders_pattern, content)

videos_dir = os.path.join(script_dir, 'videos')
os.makedirs(videos_dir, exist_ok=True)

created = []
for folder in folders:
    folder_path = os.path.join(videos_dir, folder)
    os.makedirs(folder_path, exist_ok=True)
    if os.path.isdir(folder_path):
        created.append(folder)

# Save result to file
result_file = os.path.join(script_dir, 'folders_created_result.txt')
with open(result_file, 'w', encoding='utf-8') as f:
    f.write(f'Created {len(created)} folders in {videos_dir}:\n\n')
    for folder in created:
        f.write(f'  {folder}\n')
    f.write(f'\nTotal: {len(created)} folders\n')

print(f'Created {len(created)} folders. Result saved to folders_created_result.txt')

