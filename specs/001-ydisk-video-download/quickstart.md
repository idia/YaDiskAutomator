# Quickstart: Yandex Disk Video Downloader

**Date**: 2025-01-27  
**Feature**: 001-ydisk-video-download

## Prerequisites

- Python 3.11 or higher
- OAuth token for Yandex Disk (with write permissions)
- Public Yandex Disk folder URL containing videos

## Installation

1. **Install dependencies**:
```bash
pip install playwright requests
playwright install chromium
```

Or create `requirements.txt`:
```text
playwright>=1.40.0
requests>=2.31.0
```

Then:
```bash
pip install -r requirements.txt
playwright install chromium
```

**Note**: Playwright requires browser binaries. Run `playwright install chromium` after installing the package.

## Configuration

### Option 1: Environment Variables

```bash
export YANDEX_OAUTH_TOKEN="your_oauth_token_here"
```

### Option 2: Command Line Arguments

Pass token via `--oauth-token` flag (see Usage below).

## Usage

### Basic Usage

```bash
python ydisk_video_downloader.py \
  "https://disk.yandex.ru/d/public_folder_id" \
  "/Videos/Downloaded" \
  --oauth-token "your_token"
```

### With Environment Variable

```bash
export YANDEX_OAUTH_TOKEN="your_token"
python ydisk_video_downloader.py \
  "https://disk.yandex.ru/d/public_folder_id" \
  "/Videos/Downloaded"
```

### Dry Run (List Videos Only)

```bash
python ydisk_video_downloader.py \
  "https://disk.yandex.ru/d/public_folder_id" \
  "/Videos/Downloaded" \
  --oauth-token "your_token" \
  --dry-run
```

### Verbose Output

```bash
python ydisk_video_downloader.py \
  "https://disk.yandex.ru/d/public_folder_id" \
  "/Videos/Downloaded" \
  --oauth-token "your_token" \
  --verbose
```

## Example Workflow

1. **Get public folder URL**:
   - Open Yandex Disk in browser
   - Share folder publicly
   - Copy public link (e.g., `https://disk.yandex.ru/d/abc123xyz`)

2. **Set destination path**:
   - Choose folder on your Yandex Disk (e.g., `/Videos/Downloaded`)
   - Path must start with `/`

3. **Run script**:
```bash
python ydisk_video_downloader.py \
  "https://disk.yandex.ru/d/abc123xyz" \
  "/Videos/Downloaded" \
  --oauth-token "your_oauth_token"
```

4. **Monitor progress**:
   - Script shows progress for each video
   - Videos are downloaded and uploaded in order
   - Original file names and folder structure are preserved
   - Script recursively processes all nested subfolders

## Expected Output

```
Parsing public folder...
Found 5 video file(s) in folder (including nested subfolders)
Downloading: video1.mp4 (1/5)...
Uploading: video1.mp4 (1/5)...
Completed: video1.mp4
Downloading: Folder1/video2.mp4 (2/5)...
Uploading: Folder1/video2.mp4 (2/5)...
Completed: Folder1/video2.mp4
Downloading: Folder1/Subfolder/video3.mp4 (3/5)...
Uploading: Folder1/Subfolder/video3.mp4 (3/5)...
Completed: Folder1/Subfolder/video3.mp4
...
Completed: 5 video(s) downloaded and uploaded successfully.
```

## Troubleshooting

### "OAuth token expired" Error

- Get a new OAuth token from Yandex OAuth settings
- Update token in environment variable or command line

### "No videos found" Message

- Verify public folder URL is correct
- Check that folder contains video files (including in nested subfolders)
- Ensure folder is publicly accessible
- Script searches recursively in all subfolders

### "Upload failed" Error

- Verify OAuth token has write permissions
- Check destination path exists or is valid
- Ensure sufficient space on Yandex Disk

### Network Errors

- Check internet connection
- Verify public folder URL is accessible
- Retry the script (it continues with remaining videos on error)

## Getting OAuth Token

1. Go to [Yandex OAuth](https://oauth.yandex.ru/)
2. Create new application
3. Get OAuth token with `cloud_api:disk.app_folder` scope
4. Use token in script

## Notes

- Videos are temporarily downloaded to local disk, then uploaded to Yandex Disk
- Temporary files are deleted after successful upload
- Script preserves file names, folder structure, and order from source folder
- Script recursively processes all nested subfolders at any depth
- Folder structure is preserved when uploading (e.g., `/Source/Folder1/Subfolder/video.mp4` → `/Destination/Folder1/Subfolder/video.mp4`)
- Only video files are processed (non-video files are skipped, but folder structure is preserved for videos in subfolders)

