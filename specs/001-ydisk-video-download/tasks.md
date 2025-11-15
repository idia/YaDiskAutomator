# Tasks: Yandex Disk Video Downloader

**Input**: Design documents from `/specs/001-ydisk-video-download/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL and not requested in the feature specification. No test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: Single-file script at repository root (`ydisk_video_downloader.py`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create requirements.txt with playwright, requests, and python-dotenv dependencies in requirements.txt
- [x] T002 Create README.md with installation and usage instructions in README.md
- [x] T003 Create ydisk_video_downloader.py with basic script structure and imports in ydisk_video_downloader.py
- [x] T026 Create .env.example file with configuration template in .env.example

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [US1] Implement CLI argument parsing (argparse) for public_folder_url and destination_path (optional, can be in .env) in ydisk_video_downloader.py
- [x] T005 [US1] Implement OAuth token loading from .env file, environment variables, or command line arguments in ydisk_video_downloader.py
- [x] T006 [US1] Implement basic error handling and exit codes in ydisk_video_downloader.py
- [x] T007 [US1] Implement video file extension filtering function (filter_video_files) in ydisk_video_downloader.py
- [x] T027 [US1] Implement load_env_file function to load configuration from .env file in ydisk_video_downloader.py
- [x] T028 [US1] Implement get_public_folder_url function to get URL from args or .env in ydisk_video_downloader.py
- [x] T029 [US1] Implement get_destination_path function to get path from args or .env in ydisk_video_downloader.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Download All Videos from Public Yandex Disk Folder (Priority: P1) 🎯 MVP

**Goal**: Automatically download all videos from a publicly accessible Yandex Disk folder URL (including nested subfolders) and save them to a folder on user's Yandex Disk, preserving file names, folder structure, and order.

**Independent Test**: Can be fully tested by providing a public Yandex Disk folder URL containing videos (potentially in nested subfolders) and verifying all videos are downloaded and uploaded to the user's Yandex Disk with correct names, folder structure, and order.

### Implementation for User Story 1

- [x] T008 [US1] Implement parse_public_folder function using Playwright to navigate to URL and extract video links in ydisk_video_downloader.py
- [x] T009 [US1] Implement order preservation when extracting video links from DOM in ydisk_video_downloader.py
- [x] T030 [US1] Update parse_public_folder to recursively traverse subfolders and extract folder links from DOM in ydisk_video_downloader.py
- [x] T031 [US1] Implement recursive folder traversal logic to process all nested subfolders at any depth in ydisk_video_downloader.py
- [x] T032 [US1] Implement relative_path tracking for each video file (preserve folder hierarchy from root) in ydisk_video_downloader.py
- [x] T010 [US1] Implement download_video function with streaming download using requests in ydisk_video_downloader.py
- [x] T011 [US1] Implement get_upload_url function to get upload URL from Yandex Disk API in ydisk_video_downloader.py
- [x] T033 [US1] Implement create_folder_structure function to create folder hierarchy on Yandex Disk using API in ydisk_video_downloader.py
- [x] T012 [US1] Implement upload_to_yandex_disk function to upload file using OAuth token in ydisk_video_downloader.py
- [x] T034 [US1] Update upload_to_yandex_disk to create parent folder structure before uploading file in ydisk_video_downloader.py
- [x] T013 [US1] Implement main workflow: parse folder → filter videos → download → upload → cleanup temp files in ydisk_video_downloader.py
- [x] T035 [US1] Update main workflow to handle recursive folder traversal and preserve folder structure in ydisk_video_downloader.py
- [x] T014 [US1] Implement progress indication during download and upload operations in ydisk_video_downloader.py
- [x] T015 [US1] Implement error handling for network interruptions and continue with remaining videos in ydisk_video_downloader.py
- [x] T016 [US1] Implement handling of special characters in video file names in ydisk_video_downloader.py
- [x] T036 [US1] Implement handling of special characters in folder names when creating folder structure in ydisk_video_downloader.py
- [x] T017 [US1] Implement validation for invalid or inaccessible public folder URLs in ydisk_video_downloader.py
- [x] T018 [US1] Implement handling of OAuth token expiration or invalidity errors in ydisk_video_downloader.py
- [x] T019 [US1] Implement handling of destination folder existence check and creation if needed in ydisk_video_downloader.py
- [x] T020 [US1] Implement --verbose flag for detailed progress output in ydisk_video_downloader.py
- [x] T021 [US1] Implement --dry-run flag to list videos without downloading/uploading in ydisk_video_downloader.py
- [x] T037 [US1] Implement --test flag to process only first video for functionality testing in ydisk_video_downloader.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently with recursive folder traversal

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Improvements and final touches

- [x] T022 Add usage examples and troubleshooting section to README.md in README.md
- [x] T023 Add shebang line and make script executable (chmod +x) for ydisk_video_downloader.py
- [x] T038 Update README.md with information about recursive folder traversal and structure preservation in README.md
- [x] T024 Validate script against quickstart.md scenarios in quickstart.md
- [x] T025 Code cleanup and remove any debug print statements in ydisk_video_downloader.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3)**: Depends on Foundational phase completion
- **Polish (Phase 4)**: Depends on all desired user stories being complete
- **Sequential Processing (Phase 5)**: Depends on Phase 3 completion - refactors existing processing loop

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within User Story 1

- CLI argument parsing before any other functionality
- OAuth token loading before upload operations
- Parse folder (recursively) before filtering and downloading
- Track relative paths during recursive parsing
- Filter videos before downloading
- Create folder structure before uploading
- Download before upload
- Error handling throughout all operations

### Task Dependencies for Recursive Traversal

- T030 (recursive traversal) depends on T008 (basic parsing)
- T031 (recursive logic) depends on T030 (folder link extraction)
- T032 (relative_path tracking) depends on T031 (recursive traversal)
- T033 (create folder structure) depends on T011 (get upload URL)
- T034 (update upload) depends on T033 (create folders)
- T035 (update main workflow) depends on T032, T034 (relative paths and folder creation)
- T036 (folder name sanitization) depends on T033 (create folders)

### Task Dependencies for Sequential Processing (Phase 5)

- T039, T040 (error handling) can be done in parallel - both modify main loop
- T041, T042 (tree.md updates) depend on T039, T040 (error handling changes)
- T043 (file deletion) depends on T042 (upload completion)
- T044 (skip logic) can be done independently
- T045 (partial handling) can be done independently
- T046 (error messages) depends on T039, T040 (error handling)
- T047 (verification) depends on all previous tasks (T039-T046)

### Parallel Opportunities

- T001, T002, T003, T026 can run in parallel (different files)
- T004, T005, T006, T007, T027, T028, T029 can run in parallel (different functions in same file, but can be implemented independently)
- T030, T031 can be implemented together (related recursive parsing)
- T033, T036 can be implemented together (folder structure creation and sanitization)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (including recursive traversal)
4. **STOP and VALIDATE**: Test User Story 1 independently with a real public folder containing nested subfolders
5. Complete Phase 5: Sequential Processing Algorithm (refactor to sequential processing)
6. **STOP and VALIDATE**: Test sequential processing with multiple videos to verify status updates and error handling
7. Use script if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add basic parsing (single folder) → Test with one video
3. Add recursive traversal → Test with nested folders
4. Add folder structure creation → Test with nested folders
5. Add upload with structure preservation → Test end-to-end
6. Add error handling and edge cases → Test with multiple videos in nested folders
7. Add progress indication and polish → Final MVP
8. Refactor to sequential processing → Test sequential algorithm with status updates

### Development Flow

Since this is a single-file script:
1. Start with basic structure and imports
2. Implement functions one by one
3. Update parse_public_folder to support recursive traversal
4. Add relative_path tracking
5. Add folder structure creation
6. Update upload to preserve structure
7. Test each function as you go
8. Integrate functions in main workflow
9. Add error handling and edge cases
10. Polish and finalize
11. Refactor main processing loop to sequential algorithm (Phase 5)
12. Update error handling to stop on failure
13. Verify tree.md updates after each step
14. Test sequential processing with multiple videos

---

## Phase 5: Sequential Processing Algorithm (2025-01-28 Update)

**Purpose**: Refactor video processing to sequential algorithm per updated specification (FR-016, FR-018, FR-019, FR-020, FR-021, FR-022, FR-023)

**Goal**: Process videos one-by-one with immediate status updates in tree.md after each step, stop on errors, delete local files immediately after upload.

### Implementation for Sequential Processing

- [x] T039 [US1] Update main processing loop to stop execution immediately on download failure (replace `continue` with `sys.exit(EXIT_ERROR)`) in ydisk_video_downloader.py
- [x] T040 [US1] Update main processing loop to stop execution immediately on upload failure (replace `continue` with `sys.exit(EXIT_ERROR)`) in ydisk_video_downloader.py
- [x] T041 [US1] Verify tree.md is updated immediately after download (mark as [p]) in ydisk_video_downloader.py
- [x] T042 [US1] Verify tree.md is updated immediately after upload (mark as [x]) in ydisk_video_downloader.py
- [x] T043 [US1] Verify local file deletion happens immediately after successful upload (not deferred) in ydisk_video_downloader.py
- [x] T044 [US1] Update skip logic to properly skip videos marked as [x] or ✓ in tree.md (FR-021) in ydisk_video_downloader.py
- [x] T045 [US1] Update partial download handling: if [p] marked and local file exists, proceed to upload; if missing, re-download (FR-022) in ydisk_video_downloader.py
- [x] T046 [US1] Add error message display before stopping execution on download/upload failure in ydisk_video_downloader.py
- [x] T047 [US1] Verify sequential processing order: download → mark [p] → upload → mark [x] → delete → next video in ydisk_video_downloader.py

**Checkpoint**: Sequential processing algorithm fully implemented and tested. Each video is processed completely before moving to next. Status in tree.md is always up-to-date.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Story 1 is the complete MVP - no other stories needed
- All functions go in single file `ydisk_video_downloader.py` per minimalism principle
- Recursive traversal implemented as simple recursive function - no complex tree structures
- Sequential processing implemented as simple loop with status updates - no complex state machines
- Commit after each logical group of tasks
- Test with real public folder URL containing nested subfolders after Phase 3 completion
- Test sequential processing with multiple videos to verify status updates and error handling
- Avoid: complex abstractions, unnecessary patterns, premature optimizations
