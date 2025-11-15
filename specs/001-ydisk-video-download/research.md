# Research: Yandex Disk Video Downloader

**Date**: 2025-01-27  
**Feature**: 001-ydisk-video-download

## Research Questions

### 1. Web Scraping Library Choice

**Question**: Should we use requests/BeautifulSoup or Selenium/Playwright for parsing public Yandex Disk folder?

**Decision**: Use **Playwright** for browser automation - web scraping required for public folders with streaming videos.

**Rationale**: 
- User experience: FetchTV (Chrome extension) works through browser, suggesting browser-based approach needed
- Public folders with streaming videos may require JavaScript execution to load content
- Yandex Disk web interface uses dynamic content loading (not static HTML)
- API for public resources may not provide direct download links for streaming videos
- Playwright is lighter and faster than Selenium, still minimal for the use case

**Alternatives considered**:
- `requests` + API: May not work for streaming videos in public folders (needs verification)
- BeautifulSoup: Not sufficient - requires JavaScript execution for dynamic content
- Selenium: Heavier than Playwright, slower startup time

**Approach**: Use Playwright to:
1. Navigate to public folder URL
2. Wait for page to load and JavaScript to execute
3. Extract video file links and folder links from DOM
4. Recursively traverse all subfolders to find all videos
5. Download videos using extracted links, preserving folder structure

---

### 2. Yandex Disk API Client Library

**Question**: Should we use a dedicated Yandex Disk Python library (like `yadisk`) or use `requests` directly?

**Decision**: Use `requests` library directly for uploads - no dedicated client library.

**Rationale**:
- Minimal dependencies (only `requests` + `playwright`)
- Simple API calls for uploads don't require abstraction layer
- Full control over requests/responses
- Aligns with minimalism principle (minimal viable dependencies)

**Alternatives considered**:
- `yadisk` library: Adds unnecessary abstraction for simple use case
- Other Yandex Disk clients: Same reason - unnecessary complexity

**API Endpoints (for uploads only)**:
- Get upload URL: `GET https://cloud-api.yandex.net/v1/disk/resources/upload?path={dest_path}` (with OAuth header)
- Upload file: `PUT {upload_url}` (from step above)

**Note**: For reading public folder, use Playwright web scraping instead of API.

---

### 3. OAuth Authentication for Upload

**Question**: How to authenticate with OAuth token for uploading to user's Yandex Disk?

**Decision**: Use OAuth token in `Authorization` header: `Authorization: OAuth {token}`

**Rationale**:
- Standard OAuth 2.0 Bearer token pattern
- User already has token, client ID, and secret
- Simple header-based authentication
- No need for token refresh flow (user provides token)

**API Pattern**:
```python
headers = {'Authorization': f'OAuth {oauth_token}'}
response = requests.get('https://cloud-api.yandex.net/v1/disk/resources/upload', 
                        params={'path': dest_path}, 
                        headers=headers)
```

**Alternatives considered**:
- OAuth flow with client ID/secret: Unnecessary - user already has token
- Session-based auth: Not applicable for API

---

### 4. Streaming Video Downloads

**Question**: How to handle streaming video format downloads efficiently?

**Decision**: Use `requests.get(url, stream=True)` with chunked writing.

**Rationale**:
- Prevents loading entire video into memory
- Handles large files efficiently
- Standard Python pattern for file downloads
- Simple implementation

**Implementation**:
```python
with requests.get(download_url, stream=True) as r:
    r.raise_for_status()
    with open(local_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
```

**Alternatives considered**:
- Download entire file to memory: Not suitable for large videos
- Specialized streaming libraries: Unnecessary complexity

---

## Technical Stack Summary

**Dependencies**:
- `playwright` - Browser automation for parsing public folder and extracting video links recursively
- `requests` - HTTP library for file downloads/uploads and Yandex Disk API calls
- `python-dotenv` - Loading configuration from .env file

**Why these dependencies**:
- Playwright: Required for JavaScript execution and dynamic content in public folders, recursive navigation
- Requests: Simple HTTP operations for downloads and uploads
- python-dotenv: Simple configuration management, minimal dependency

**No additional dependencies needed**:
- No Yandex Disk client libraries (simple API calls for uploads)
- No OAuth libraries (direct header usage)
- No streaming libraries (requests handles it)

**API Endpoints (for uploads only)**:
1. **Get upload URL**: `GET https://cloud-api.yandex.net/v1/disk/resources/upload?path={dest_path}` (with OAuth header)
2. **Upload file**: `PUT {upload_url}` (from step 1)

---

## Implementation Approach

1. **Recursively parse public folder** using Playwright:
   - Navigate to public folder URL
   - Wait for page load and JavaScript execution
   - Extract video file links and folder links from DOM
   - For each folder found, recursively navigate and extract videos
   - Track relative paths for each video (preserve folder hierarchy)
   - Filter video files by extension
2. **Download videos** using `requests` with streaming (chunked), maintaining relative paths
3. **Create folder structure** on user's Yandex Disk using API (create folders as needed)
4. **Upload to user's Yandex Disk** using OAuth token via API, preserving folder structure
5. **Preserve file names, folder structure, and order**

**Workflow**:
```
Public URL → Playwright (recursive parse) → Extract All Videos with Paths → 
Download (stream) → Create Folder Structure → Upload (OAuth API) → User's Disk
```

**Recursive Traversal Strategy**:
- Use depth-first traversal: process folder, then recursively process subfolders
- Track relative path from root folder for each video
- Build destination path by combining destination root + relative path
- Create folders on destination before uploading videos

**Fallback approach** (if API works for public folders):
- Try API first: `GET https://cloud-api.yandex.net/v1/disk/public/resources?public_key={url}`
- If API doesn't work or doesn't provide streaming video links, fall back to Playwright recursive navigation

