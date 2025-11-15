# Yandex Disk Video Downloader

Python script to automatically download all videos from a public Yandex Disk folder URL and upload them to your Yandex Disk folder.

## Features

- Downloads all videos from a public Yandex Disk folder (including nested subfolders)
- **Recursively traverses all subfolders** at any depth to find videos
- **Preserves folder structure** when uploading (e.g., `/Source/Folder1/Subfolder/video.mp4` → `/Destination/Folder1/Subfolder/video.mp4`)
- Preserves original file names and order
- Uploads videos to your Yandex Disk using OAuth authentication
- Handles streaming video downloads
- Continues with remaining videos on errors
- Progress indication for downloads and uploads

## Prerequisites

- Python 3.11 or higher
- OAuth token for Yandex Disk (with write permissions)
- Public Yandex Disk folder URL containing videos

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

**Note**: The script uses `yt-dlp` for downloading streaming videos. Make sure it's installed along with `ffmpeg` (required by yt-dlp for some formats):
```bash
# On macOS
brew install ffmpeg

# On Ubuntu/Debian
sudo apt-get install ffmpeg

# On Windows
# Download from https://ffmpeg.org/download.html
```

2. Configure OAuth token:
```bash
cp .env.example .env
# Edit .env and add your YANDEX_OAUTH_TOKEN
```

**Note**: Playwright requires browser binaries. Run `playwright install chromium` after installing the package.

## Configuration

### Option 1: .env File (Recommended)

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` and add your configuration:

```bash
YANDEX_OAUTH_TOKEN=your_oauth_token_here
YANDEX_PUBLIC_FOLDER_URL=https://disk.yandex.ru/d/your_folder_id
YANDEX_DESTINATION_PATH=/Videos/Downloaded
```

All three values can be set in `.env`, or you can provide them via command line arguments.

### Option 2: Environment Variables

```bash
export YANDEX_OAUTH_TOKEN="your_oauth_token_here"
```

### Option 3: Command Line Arguments

Pass token via `--oauth-token` flag (see Usage below).

**Priority order**: Command line arguments > .env file > Environment variables

If all values are set in `.env`, you can run the script without any arguments.

## Usage

### Basic Usage (with .env file)

If you have configured `.env` file with all required values, you can run:

```bash
python ydisk_video_downloader.py
```

Or provide values via command line (overrides .env):

```bash
python ydisk_video_downloader.py \
  "https://disk.yandex.ru/d/public_folder_id" \
  "/Videos/Downloaded"
```

### With Command Line Token

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
  --dry-run
```

### Verbose Output

```bash
python ydisk_video_downloader.py \
  "https://disk.yandex.ru/d/public_folder_id" \
  "/Videos/Downloaded" \
  --verbose
```

### Test Mode (Process Only First Video)

Test the functionality by processing only the first video:

```bash
python ydisk_video_downloader.py \
  "https://disk.yandex.ru/d/public_folder_id" \
  "/Videos/Downloaded" \
  --test
```

This is useful for verifying that the script works correctly before processing all videos.

## Getting OAuth Token

1. Go to [Yandex OAuth](https://oauth.yandex.ru/)
2. Create new application
3. Get OAuth token with `cloud_api:disk.app_folder` scope
4. Use token in script

## Troubleshooting

### "OAuth token expired" Error

- Get a new OAuth token from Yandex OAuth settings
- Update token in environment variable or command line

### "No videos found" Message

- Verify public folder URL is correct
- Check that folder contains video files (including in nested subfolders)
- Ensure folder is publicly accessible
- Script searches recursively in all subfolders at any depth

### "Upload failed" Error

- Verify OAuth token has write permissions
- Check destination path exists or is valid
- Ensure sufficient space on Yandex Disk

### Network Errors

- Check internet connection
- Verify public folder URL is accessible
- Retry the script (it continues with remaining videos on error)

## Example Output

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

## Notes

- Videos are temporarily downloaded to local disk, then uploaded to Yandex Disk
- Temporary files are deleted after successful upload
- Script preserves file names, **folder structure**, and order from source folder
- Script **recursively processes all nested subfolders** at any depth
- Folder structure is preserved when uploading (e.g., `/Source/Folder1/Subfolder/video.mp4` → `/Destination/Folder1/Subfolder/video.mp4`)
- Only video files are processed (non-video files are skipped, but folder structure is preserved for videos in subfolders)
- Script handles special characters in both file and folder names

