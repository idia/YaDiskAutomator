# Feature Specification: Yandex Disk Video Downloader

**Feature Branch**: `001-ydisk-video-download`  
**Created**: 2025-01-27  
**Status**: Draft  
**Input**: User description: "мы хотим написать простейший Питоновый скрипт для личных нужд. Нужно будет скачать видео из папки на Яндекс диске (через веб), где видео в потоковом формате. Я использовал вручную аддон для Chrome который называется FetchTV. Он делает работу, но видео в папке много и нужно сделать это все автоматически за один раз. Скрипт должен будет скачивать все видео из папки по адресу, который я укажу и сохранить их в таком же порядке и с такими же названиями, как они там есть в отдельной папке на моем Яндекс Диске."

## Clarifications

### Session 2025-01-27

- Q: Should the script handle videos in nested subfolders recursively? → A: Yes, script MUST recursively traverse all subfolders at any depth and preserve the complete folder structure when uploading videos to destination.
- Q: How should the script handle Cyrillic characters in folder and file names? → A: Preserve Cyrillic characters as-is (no transliteration). System MUST support Unicode characters including Cyrillic in folder and file names.

### Session 2025-01-28

- Q: What should happen if video download fails during sequential processing? → A: Script MUST stop execution immediately and display error message. Sequential processing means each video must be fully downloaded and uploaded before proceeding to the next.
- Q: What should happen to local file after successful upload to Yandex Disk? → A: System MUST delete local file immediately after successful upload to free up disk space.
- Q: What should happen to videos already marked as fully uploaded ([x] or ✓) in tree.md? → A: System MUST skip such videos and proceed to the next unprocessed video.
- Q: What should happen to videos marked as partially downloaded ([p] in tree.md - downloaded locally but not uploaded to Yandex Disk)? → A: System MUST upload to Yandex Disk if local file exists, otherwise re-download first, then upload.
- Q: When should tree.md be updated during video processing? → A: System MUST update tree.md after each step: mark as [p] after local download, mark as [x] after successful upload to Yandex Disk.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sequential Video Processing from Public Yandex Disk Folder (Priority: P1)

User wants to automatically process videos from a publicly accessible Yandex Disk folder URL sequentially: for each video, download locally, mark status in tree.md, upload to their Yandex Disk, mark as completed in tree.md, delete local file, then proceed to next video. This ensures each video is fully processed before moving to the next one.

**Why this priority**: This is the core functionality that solves the user's problem of manually downloading many videos. Sequential processing ensures progress is tracked accurately and disk space is managed efficiently.

**Independent Test**: Can be fully tested by providing a public Yandex Disk folder URL containing videos and verifying videos are processed one-by-one with status updates in tree.md after each step.

**Acceptance Scenarios**:

1. **Given** a public Yandex Disk folder URL containing multiple video files, **When** user runs the script, **Then** videos are processed sequentially: first video downloaded → marked [p] in tree.md → uploaded → marked [x] in tree.md → local file deleted → second video processed, etc.
2. **Given** a public Yandex Disk folder URL with videos in a specific order, **When** user runs the script, **Then** videos are processed in the same order as displayed in the source folder
3. **Given** a public Yandex Disk folder URL with no videos, **When** user runs the script, **Then** script completes without errors and reports no videos found
4. **Given** a public Yandex Disk folder URL with mixed content (videos and non-video files), **When** user runs the script, **Then** only video files are processed, non-video files are skipped
5. **Given** a public Yandex Disk folder URL with videos in nested subfolders, **When** user runs the script, **Then** all videos are found recursively and processed preserving the folder structure (e.g., `/Folder1/Subfolder/video.mp4` → `/Destination/Folder1/Subfolder/video.mp4`)
6. **Given** a public Yandex Disk folder URL with empty folders (no videos), **When** user runs the script, **Then** script completes without errors and reports no videos found (empty folders are not created)
7. **Given** a video already marked as [x] in tree.md, **When** user runs the script, **Then** that video is skipped and script proceeds to next unprocessed video
8. **Given** a video marked as [p] in tree.md with local file existing, **When** user runs the script, **Then** script uploads existing local file to Yandex Disk and marks as [x]
9. **Given** a video marked as [p] in tree.md but local file missing, **When** user runs the script, **Then** script re-downloads the video, then uploads it, then marks as [x]
10. **Given** a video download fails during processing, **When** error occurs, **Then** script stops execution immediately and displays error message
11. **Given** a video upload to Yandex Disk fails, **When** error occurs, **Then** script stops execution immediately and displays error message
12. **Given** a video is successfully uploaded to Yandex Disk, **When** upload completes, **Then** local file is immediately deleted and tree.md is updated to [x]

### Edge Cases

- What happens when the public Yandex Disk folder URL is invalid or inaccessible?
- What happens when a video file already exists in the destination folder on user's Yandex Disk?
- How does the system handle network interruptions during download? (Script stops on error per FR-018)
- What happens when user's Yandex Disk has insufficient space for uploading videos? (Script stops on error per FR-019)
- What happens if tree.md file is locked or cannot be written during status update?
- What happens if local file deletion fails after successful upload?
- How does the system handle videos with special characters in their names?
- How does the system handle folder names with special characters?
- How does the system handle Cyrillic and other Unicode characters in folder and file names?
- What happens when the destination folder doesn't exist on user's Yandex Disk?
- How does the system handle OAuth token expiration or invalidity for writing to user's Yandex Disk?
- What happens when the public folder structure cannot be parsed from the web page?
- What happens when there are deeply nested folders (e.g., 10+ levels deep)?
- What happens when a subfolder contains only non-video files (should the folder structure still be preserved for videos in other subfolders)?
- What happens when folder names conflict with existing folders on destination Yandex Disk?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a public Yandex Disk folder URL as input (no authentication required for source folder)
- **FR-002**: System MUST accept a destination folder path on user's Yandex Disk as input
- **FR-003**: System MUST parse the public folder structure by accessing the folder URL through browser/web scraping
- **FR-004**: System MUST recursively traverse all subfolders in the source folder to find video files
- **FR-005**: System MUST identify all video files in the source folder and all nested subfolders from the parsed structure
- **FR-006**: System MUST download all video files from the specified public Yandex Disk folder and all nested subfolders
- **FR-007**: System MUST preserve original video file names during download and upload, including Unicode characters (Cyrillic, etc.)
- **FR-008**: System MUST preserve folder structure when uploading videos (e.g., `/Source/Folder1/Subfolder/video.mp4` → `/Destination/Folder1/Subfolder/video.mp4`), including Unicode characters in folder names
- **FR-017**: System MUST support Unicode characters (including Cyrillic) in folder and file names without transliteration or character replacement
- **FR-009**: System MUST create destination folder structure on user's Yandex Disk to match source folder structure
- **FR-010**: System MUST download and save videos in the same order as they appear in the source Yandex Disk folder structure
- **FR-011**: System MUST upload downloaded videos to the specified destination folder on user's Yandex Disk maintaining folder hierarchy
- **FR-012**: System MUST use OAuth token (with client ID and secret) for authentication when writing to user's Yandex Disk
- **FR-013**: System MUST skip non-video files in the source folder (but preserve folder structure for videos in subfolders)
- **FR-014**: System MUST handle streaming video format downloads
- **FR-015**: System MUST provide basic progress indication during download and upload
- **FR-016**: System MUST process videos sequentially: for each video, download locally → mark as [p] in tree.md → upload to Yandex Disk → mark as [x] in tree.md → delete local file → proceed to next video
- **FR-023**: System MUST update tree.md immediately after each processing step (after download mark as [p], after upload mark as [x]) to maintain accurate status
- **FR-018**: System MUST stop execution immediately if video download fails during sequential processing and display error message
- **FR-019**: System MUST stop execution immediately if video upload to Yandex Disk fails and display error message
- **FR-020**: System MUST delete local video file immediately after successful upload to Yandex Disk to free up disk space
- **FR-021**: System MUST skip videos already marked as fully uploaded ([x] or ✓) in tree.md and proceed to next unprocessed video
- **FR-022**: System MUST handle partially downloaded videos ([p] in tree.md): if local file exists, upload to Yandex Disk; if local file missing, re-download then upload

### Key Entities *(include if feature involves data)*

- **Source Video File**: Represents a video file in the public Yandex Disk folder with attributes: name, download URL, size, order in folder, relative path (including parent folder structure)
- **Source Folder Structure**: Represents the folder hierarchy in the public Yandex Disk folder, including nested subfolders at any depth
- **Destination Folder**: Represents the folder on user's Yandex Disk where videos will be saved, maintaining the same folder structure as source
- **OAuth Credentials**: Represents authentication credentials for user's Yandex Disk (OAuth token, client ID, client secret)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can download and save all videos from a public folder containing 50 videos (including videos in nested subfolders) to their Yandex Disk in a single script execution
- **SC-002**: All saved videos have identical names to their source files in the public Yandex Disk folder (including Unicode characters)
- **SC-003**: Videos are saved preserving the exact folder structure from source (e.g., `/Source/Folder1/Subfolder/video.mp4` → `/Destination/Folder1/Subfolder/video.mp4`), including Unicode characters in folder names
- **SC-009**: Script successfully processes folders and files with Cyrillic characters in names (e.g., "Замещающий ребёнок") without errors or character loss
- **SC-004**: Videos are saved in the correct order matching the source Yandex Disk folder listing
- **SC-005**: Script completes successfully for folders containing at least 10 videos (including nested subfolders) without manual intervention
- **SC-006**: Script handles at least one network interruption during download and continues with remaining videos
- **SC-007**: Script successfully parses folder structure from public Yandex Disk URL without authentication, including nested subfolders
- **SC-008**: Script successfully processes folders with up to 5 levels of nesting
