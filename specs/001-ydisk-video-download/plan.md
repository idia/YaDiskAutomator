# Implementation Plan: Yandex Disk Video Downloader

**Branch**: `001-ydisk-video-download` | **Date**: 2025-01-28 (Updated) | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ydisk-video-download/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Python script to automatically process videos from a public Yandex Disk folder URL (including nested subfolders) sequentially: for each video, download locally, mark status in tree.md, upload to user's Yandex Disk, mark as completed in tree.md, delete local file, then proceed to next video. Uses Playwright for browser automation to recursively parse folder structure and extract streaming video links, downloads videos using `yt-dlp` or `requests` library, and uploads to destination preserving folder hierarchy using OAuth token via Yandex Disk API. Single-file script with minimal dependencies (`playwright` + `requests` + `python-dotenv` + `yt-dlp`). Preserves file names, folder structure, and order. Processes videos one-by-one with immediate status updates in tree.md after each step.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `playwright` (browser automation for parsing public folders recursively), `requests` (HTTP library for downloads/uploads and API calls), `python-dotenv` (loading configuration from .env file), `yt-dlp` (streaming video download)  
**Storage**: N/A (temporary local storage during download, then upload to Yandex Disk, files deleted immediately after upload)  
**Testing**: pytest (optional, per constitution minimalism)  
**Target Platform**: macOS/Linux (command-line script)  
**Project Type**: single (CLI script)  
**Performance Goals**: Download and upload 50 videos (including nested subfolders) sequentially in reasonable time (no specific SLA for personal use)  
**Constraints**: Minimal dependencies (playwright + requests + python-dotenv + yt-dlp), simple code structure, handle streaming video downloads via browser parsing, recursive folder traversal, sequential processing with immediate status updates  
**Scale/Scope**: Personal use script, handles folders with 10-50 videos including nested subfolders up to 5 levels deep

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I: Minimalism (NON-NEGOTIABLE)**

✅ **PASS (Pre-Research)**: Script performs only necessary functions:
- Recursively parse public folder structure
- Download videos from all nested subfolders
- Upload to destination preserving folder hierarchy
- No unnecessary abstractions, patterns, or optimizations

✅ **PASS (Post-Design)**: Design confirms minimalism:
- Single Python script file (`ydisk_video_downloader.py`)
- Minimal dependencies: `playwright` (required for browser parsing) + `requests` (HTTP operations) + `python-dotenv` (configuration) + `yt-dlp` (streaming video download)
- Direct approach - no abstraction layers
- Simple function-based structure - no classes or patterns
- Recursive traversal implemented as simple recursive function - no complex tree structures
- Sequential processing implemented as simple loop with status updates - no complex state machines
- No unnecessary features or optimizations
- Playwright is necessary for parsing dynamic public folder content (user confirmed via FetchTV experience)
- yt-dlp is necessary for downloading streaming video formats (HLS, etc.)

**Compliance**: Single-file script with minimal viable dependencies. Playwright required for JavaScript execution in public folders. Recursive folder traversal is necessary requirement, implemented simply. Direct approach without frameworks or complex architecture. All design decisions align with minimalism principle.

## Project Structure

### Documentation (this feature)

```text
specs/001-ydisk-video-download/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
ydisk_video_downloader.py    # Main script (single file per minimalism)
requirements.txt              # Python dependencies (playwright, requests, python-dotenv)
README.md                     # Usage instructions
.env.example                  # Configuration template
```

**Structure Decision**: Single-file script following minimalism principle. No complex directory structure needed for personal use script. Recursive folder traversal logic implemented within the same file.

## Sequential Processing Algorithm

**Key Change (2025-01-28)**: Script now processes videos sequentially instead of batch processing. This ensures:
- Each video is fully processed (downloaded + uploaded) before moving to next
- Status in tree.md is updated immediately after each step
- Local disk space is freed immediately after successful upload
- Progress is accurately tracked even if script is interrupted

**Processing Flow for Each Video**:
1. Check if video already marked as [x] in tree.md → skip if yes
2. Check if video marked as [p] in tree.md:
   - If local file exists → proceed to upload
   - If local file missing → re-download first
3. Download video locally (if not already downloaded)
4. Mark as [p] in tree.md immediately after download
5. Upload to Yandex Disk
6. Mark as [x] in tree.md immediately after upload
7. Delete local file immediately after successful upload
8. Proceed to next video

**Error Handling**:
- If download fails → stop execution immediately, display error
- If upload fails → stop execution immediately, display error
- Status in tree.md reflects last successful step

**Benefits**:
- Accurate progress tracking (tree.md always up-to-date)
- Efficient disk space usage (files deleted immediately after upload)
- Resume capability (can restart from last processed video)
- Clear error reporting (stops on first error)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - recursive traversal is a necessary requirement and implemented simply. Sequential processing adds minimal complexity (simple loop with status updates) and provides significant benefits (accurate progress tracking, disk space efficiency).
