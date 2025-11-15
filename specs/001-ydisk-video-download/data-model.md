# Data Model: Yandex Disk Video Downloader

**Date**: 2025-01-27  
**Feature**: 001-ydisk-video-download

## Entities

### Source Video File

Represents a video file in the public Yandex Disk folder (including nested subfolders).

**Attributes**:
- `name` (string): Original file name
- `relative_path` (string): Relative path from root folder including parent folder structure (e.g., `Folder1/Subfolder/video.mp4`)
- `download_url` (string): Direct download URL (extracted from DOM)
- `size` (integer, optional): File size in bytes
- `order` (integer): Position in folder listing (for preserving order within folder)

**Source**: Parsed from Yandex Disk web interface using Playwright (recursive traversal)

**Validation**:
- Must have video file extension (`.mp4`, `.avi`, `.mkv`, `.mov`, `.webm`, etc.)
- Must have valid `download_url` from web scraping
- `name` must not be empty
- `relative_path` must preserve folder hierarchy from root

---

### Destination Folder

Represents the folder on user's Yandex Disk where videos will be saved, maintaining source folder structure.

**Attributes**:
- `root_path` (string): Root destination path on Yandex Disk (e.g., `/Videos/Downloaded`)
- `full_path` (string): Full path including folder structure for each video (e.g., `/Videos/Downloaded/Folder1/Subfolder/video.mp4`)

**Validation**:
- Root path must be valid Yandex Disk path format starting with `/`
- Path should not contain invalid characters
- Full path is constructed as: `root_path + relative_path_from_source`

---

### OAuth Credentials

Represents authentication credentials for user's Yandex Disk.

**Attributes**:
- `token` (string): OAuth access token
- `client_id` (string): OAuth client ID
- `client_secret` (string): OAuth client secret

**Usage**:
- Token used in `Authorization: OAuth {token}` header for API requests
- Client ID and secret available for token refresh if needed (not implemented in MVP)

**Security**:
- Should be stored securely (environment variables, config file with restricted permissions)
- Never committed to version control

---

## Data Flow

```
Public Folder URL
    ↓
Playwright: Navigate to root folder
    ↓
Extract items (files + folders)
    ↓
For each folder found:
    Recursively navigate and extract items
    Track relative path from root
    ↓
Filter: Video files only (preserve relative paths)
    ↓
For each video (with relative path):
    Get download URL from DOM
    Download to temp location (streaming)
    Create folder structure on destination (if needed)
    Upload to user's Yandex Disk preserving path (OAuth)
    Delete temp file
```

---

## State Transitions

### Folder Traversal Process

1. **Root Parsed**: Root folder structure parsed, folders and files identified
2. **Subfolder Discovered**: Nested subfolder found, queued for traversal
3. **Subfolder Parsed**: Subfolder structure parsed recursively
4. **All Folders Traversed**: All nested folders processed, all videos found

### Video Download Process

1. **Discovered**: Video found in folder (root or nested), relative path tracked
2. **Folder Structure Created**: Destination folder structure created on Yandex Disk (if needed)
3. **Downloading**: Currently downloading from public folder
4. **Downloaded**: File saved to temporary location
5. **Uploading**: Currently uploading to user's Yandex Disk at correct path
6. **Completed**: File successfully uploaded preserving folder structure, temp file deleted
7. **Failed**: Error occurred (download or upload), error logged, continue with next video

---

## File Extensions

**Video file extensions recognized**:
- `.mp4`, `.avi`, `.mkv`, `.mov`, `.webm`, `.flv`, `.wmv`, `.m4v`, `.3gp`, `.ogv`

**Filtering logic**: Case-insensitive extension matching

