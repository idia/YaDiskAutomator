# CLI Interface Contract

**Date**: 2025-01-27  
**Feature**: 001-ydisk-video-download

## Command Line Interface

### Script Invocation

```bash
python ydisk_video_downloader.py <public_folder_url> <destination_path> [options]
```

### Arguments

**Positional Arguments**:
- `public_folder_url` (required): Public Yandex Disk folder URL
  - Format: `https://disk.yandex.ru/d/{folder_id}` or `https://yadi.sk/d/{folder_id}`
  - Example: `https://disk.yandex.ru/d/abc123xyz`

- `destination_path` (required): Destination folder path on user's Yandex Disk
  - Format: Absolute path starting with `/`
  - Example: `/Videos/Downloaded`

### Options

- `--oauth-token TOKEN`: OAuth token for Yandex Disk (required if not in env/config)
- `--client-id ID`: OAuth client ID (optional, for future token refresh)
- `--client-secret SECRET`: OAuth client secret (optional, for future token refresh)
- `--verbose`: Enable verbose output (progress details)
- `--dry-run`: List videos without downloading/uploading

### Environment Variables

- `YANDEX_OAUTH_TOKEN`: OAuth token (alternative to `--oauth-token`)
- `YANDEX_CLIENT_ID`: Client ID (alternative to `--client-id`)
- `YANDEX_CLIENT_SECRET`: Client secret (alternative to `--client-secret`)

### Configuration File (Future)

Optional `~/.ydisk_config` or `config.json`:
```json
{
  "oauth_token": "...",
  "client_id": "...",
  "client_secret": "..."
}
```

---

## Function Signatures (Internal)

### Main Functions

def parse_public_folder(public_url: str, base_path: str = "") -> List[Dict]:
    """
    Recursively parse public Yandex Disk folder using Playwright and return list of video items.
    
    Args:
        public_url: Public folder URL (can be root or subfolder)
        base_path: Relative path from root folder (for recursive calls)
        
    Returns:
        List of video file items with name, download_url, order, relative_path
        
    Raises:
        playwright.sync_api.Error: On browser automation errors
        ValueError: On invalid URL format
        TimeoutError: On page load timeout
    """

def filter_video_files(items: List[Dict]) -> List[Dict]:
    """
    Filter items to only video files.
    
    Args:
        items: List of folder items from API
        
    Returns:
        List of video file items
    """

def download_video(download_url: str, local_path: str) -> None:
    """
    Download video file using streaming.
    
    Args:
        download_url: Direct download URL
        local_path: Local file path to save
        
    Raises:
        requests.RequestException: On download errors
        IOError: On file write errors
    """

def create_folder_structure(dest_path: str, oauth_token: str) -> None:
    """
    Create folder structure on user's Yandex Disk if it doesn't exist.
    
    Args:
        dest_path: Destination folder path on Yandex Disk
        oauth_token: OAuth token for authentication
        
    Raises:
        requests.RequestException: On API errors
    """

def upload_to_yandex_disk(local_path: str, dest_path: str, oauth_token: str) -> None:
    """
    Upload file to user's Yandex Disk, creating folder structure if needed.
    
    Args:
        local_path: Local file path
        dest_path: Full destination path on Yandex Disk (including folder structure)
        oauth_token: OAuth token for authentication
        
    Raises:
        requests.RequestException: On API/upload errors
        IOError: On file read errors
    """

def get_upload_url(dest_path: str, oauth_token: str) -> str:
    """
    Get upload URL from Yandex Disk API.
    
    Args:
        dest_path: Destination path on Yandex Disk
        oauth_token: OAuth token
        
    Returns:
        Upload URL for PUT request
        
    Raises:
        requests.RequestException: On API errors
    """
```

---

## Error Handling

### Error Codes/Messages

- `INVALID_URL`: Public folder URL format is invalid
- `API_ERROR`: Yandex Disk API returned error
- `DOWNLOAD_FAILED`: Video download failed
- `UPLOAD_FAILED`: Upload to Yandex Disk failed
- `AUTH_ERROR`: OAuth token invalid or expired
- `NO_VIDEOS`: No video files found in folder
- `NETWORK_ERROR`: Network connection error

### Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Authentication error
- `4`: API error

---

## Output Format

### Success Output

```
Found 5 video files in folder
Downloading: video1.mp4 (1/5)...
Uploading: video1.mp4 (1/5)...
Completed: video1.mp4
...
All videos downloaded and uploaded successfully.
```

### Error Output

```
Error: Failed to download video2.mp4
Error: OAuth token expired
```

### Verbose Output

```
Parsing public folder: https://disk.yandex.ru/d/abc123
Found 5 items, 3 are video files
Downloading video1.mp4 (1024 MB)...
  Progress: 50% (512 MB / 1024 MB)
Uploading video1.mp4 to /Videos/Downloaded/...
  Progress: 100%
Completed video1.mp4
```

