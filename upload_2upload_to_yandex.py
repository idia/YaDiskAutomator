#!/usr/bin/env python3
"""
Upload files from 2upload/ to Yandex Disk, then move them to uploaded/.
Reuses ydisk_video_downloader upload helpers (same OAuth and API as the main script).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

EXIT_SUCCESS = 0
EXIT_ERROR = 2

try:
    from ydisk_video_downloader import (
        VIDEO_EXTENSIONS,
        create_folder_structure,
        get_oauth_token,
        load_env_file,
        upload_to_yandex_disk,
    )
except ModuleNotFoundError as exc:
    _repo = Path(__file__).resolve().parent
    _venv_py = _repo / ".venv" / "bin" / "python"
    print(
        "Missing dependency (import ydisk_video_downloader failed).\n"
        f"  Activate the project venv:  source {_repo / '.venv' / 'bin' / 'activate'}\n"
        f"  Or run explicitly:  {_venv_py} {_repo / 'upload_2upload_to_yandex.py'} ...\n"
        f"  Original error: {exc}",
        file=sys.stderr,
    )
    raise SystemExit(EXIT_ERROR) from exc


def _is_video(name: str) -> bool:
    lower = name.lower()
    return any(lower.endswith(ext) for ext in VIDEO_EXTENSIONS)


def _collect_files(upload_dir: Path, recursive: bool, any_file: bool) -> list[Path]:
    out: list[Path] = []
    if recursive:
        for p in sorted(upload_dir.rglob("*")):
            if p.is_file() and not p.name.startswith("."):
                if any_file or _is_video(p.name):
                    out.append(p)
    else:
        for p in sorted(upload_dir.iterdir()):
            if p.is_file() and not p.name.startswith("."):
                if any_file or _is_video(p.name):
                    out.append(p)
    return out


def _disk_destination(base: str, rel: Path) -> str:
    base = base.rstrip("/")
    rel_s = rel.as_posix().lstrip("/")
    if not rel_s:
        raise ValueError("empty relative path")
    return f"{base}/{rel_s}" if base else f"/{rel_s}"


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    default_in = script_dir / "2upload"
    default_done = script_dir / "uploaded"

    parser = argparse.ArgumentParser(
        description="Upload from 2upload/ to Yandex Disk; optional move to uploaded/",
    )
    parser.add_argument(
        "-p",
        "--destination",
        dest="dest",
        help="Path on Yandex Disk (must start with /). Default: YANDEX_DESTINATION_PATH from .env",
    )
    parser.add_argument(
        "-d",
        "--upload-dir",
        type=Path,
        default=default_in,
        help=f"Local folder to read (default: {default_in})",
    )
    parser.add_argument(
        "--uploaded-dir",
        type=Path,
        default=default_done,
        help=f"Move uploaded files here when using --move (default: {default_done})",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Include subfolders (paths preserved on Disk and in uploaded/)",
    )
    parser.add_argument(
        "-a",
        "--any",
        action="store_true",
        help="Upload any file, not only video extensions",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="After successful upload, move file to uploaded/",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    load_env_file()
    dest = args.dest or os.getenv("YANDEX_DESTINATION_PATH")
    if not dest:
        print(
            "Error: set --destination /path/on/disk or YANDEX_DESTINATION_PATH in .env",
            file=sys.stderr,
        )
        return EXIT_ERROR
    if not dest.startswith("/"):
        print("Error: destination must start with /", file=sys.stderr)
        return EXIT_ERROR

    try:
        token = get_oauth_token()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_ERROR

    upload_dir = args.upload_dir.resolve()
    uploaded_dir = args.uploaded_dir.resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    uploaded_dir.mkdir(parents=True, exist_ok=True)

    files = _collect_files(upload_dir, args.recursive, args.any)
    if not files:
        print(
            f"No files to upload in {upload_dir}"
            + ("" if args.any else " (use --any for non-video files)"),
            file=sys.stderr,
        )
        return EXIT_ERROR

    base_dest = dest.rstrip("/")
    count = 0
    for local_path in files:
        try:
            rel = local_path.relative_to(upload_dir)
        except ValueError:
            print(f"Skip (outside upload dir): {local_path}", file=sys.stderr)
            continue

        full_destination = _disk_destination(base_dest, rel)
        path_parts = rel.parts
        if len(path_parts) > 1:
            folder_path = "/".join(path_parts[:-1]).lstrip("/")
            create_folder_structure(base_dest, folder_path, token, args.verbose)

        if args.verbose:
            print(f"Upload {local_path} -> {full_destination}")

        ok = upload_to_yandex_disk(
            str(local_path),
            full_destination,
            token,
            args.verbose,
            use_web_interface=False,
            page=None,
        )
        if not ok:
            print(f"ERROR: upload failed: {local_path}", file=sys.stderr)
            return EXIT_ERROR
        print(f"OK {local_path} -> {full_destination}")
        count += 1

        if args.move:
            dest_local = uploaded_dir / rel
            dest_local.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(local_path), str(dest_local))
            if args.verbose:
                print(f"  moved to {dest_local}")

    print(f"Done. Uploaded {count} file(s).")
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
