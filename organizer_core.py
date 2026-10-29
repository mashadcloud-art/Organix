"""
organizer_core.py
-----------------
Core engine for the Desktop File Organizer.

Pure standard-library Python: scanning, planning, moving and undoing.
No GUI here so the logic can be unit-tested headlessly.

Files are moved into  <destination_root>/<Category>/  — for example
    C:\\Users\\You\\Desktop\\Sorted Files\\Images\\holiday.jpg
"""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

UNDO_FILE_NAME = ".file_organizer_undo.json"

# Name of the single "segregation" folder created inside the source folder.
DEFAULT_DEST_NAME = "Sorted Files"

# Sub-folder that existing folders on the Desktop are gathered into.
FOLDER_CATEGORY = "Folders"

# Directories we never touch
SYSTEM_DIR_NAMES = {"$recycle.bin", "system volume information", "recovery",
                    "config.msi", "$windows.~bt", "$windows.~ws", "program files",
                    "program files (x86)", "windows", "appdata"}

# ---------------------------------------------------------------------------
# Default category rules:  category name -> list of extensions (lowercase, no dot)
# Edit rules.json next to the app to customise, or use the "Edit Rules" button.
# ---------------------------------------------------------------------------
DEFAULT_RULES: dict[str, list[str]] = {
    "Images": ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tif", "tiff", "svg",
               "heic", "heif", "raw", "cr2", "nef", "arw", "dng", "ico"],
    "PDF": ["pdf"],
    "Documents": ["doc", "docx", "rtf", "txt", "odt", "md", "pages", "tex", "log"],
    "Spreadsheets": ["xls", "xlsx", "xlsm", "csv", "tsv", "ods", "numbers"],
    "Presentations": ["ppt", "pptx", "pps", "ppsx", "odp", "key"],
    "Videos": ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v",
               "mpg", "mpeg", "3gp", "ts", "vob"],
    "Audio": ["mp3", "wav", "flac", "aac", "m4a", "ogg", "wma", "opus", "aiff", "mid"],
    "Archives": ["zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "xz", "iso", "cab"],
    "Installers": ["exe", "msi", "msix", "appx", "apk", "dmg", "deb", "rpm", "pkg"],
    "Code": ["py", "js", "ts", "jsx", "tsx", "java", "c", "cpp", "h", "cs", "html",
             "htm", "css", "scss", "json", "xml", "yml", "yaml", "sh", "bat", "ps1",
             "go", "rs", "rb", "php", "sql", "ipynb", "kt", "swift"],
    "Fonts": ["ttf", "otf", "woff", "woff2", "eot", "fon"],
    "Ebooks": ["epub", "mobi", "azw", "azw3", "fb2", "djvu"],
    "Shortcuts": ["lnk", "url", "desktop"],
    "Other": [],  # catch-all for anything unmatched
}

# Files we never touch (Windows housekeeping / our own artefacts)
SKIP_NAMES = {UNDO_FILE_NAME, "desktop.ini", "thumbs.db", ".ds_store",
              # keep the app's own Desktop shortcut from being swept up
              "desktop file organizer.lnk", "organix.lnk", "organix.exe", "desktop file organizer pro.exe"}


# ---------------------------------------------------------------------------
# Rules handling
# ---------------------------------------------------------------------------
def build_extension_map(rules: dict[str, list[str]]) -> dict[str, str]:
    """extension -> category (first matching rule wins)."""
    ext_map: dict[str, str] = {}
    for category, extensions in rules.items():
        for ext in extensions:
            ext = ext.lower().lstrip(".")
            if ext and ext not in ext_map:
                ext_map[ext] = category
    return ext_map


def load_rules(rules_path: Path | None) -> dict[str, list[str]]:
    """Load rules.json if present, otherwise fall back to defaults."""
    if rules_path and Path(rules_path).is_file():
        try:
            data = json.loads(Path(rules_path).read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                cleaned: dict[str, list[str]] = {}
                for cat, exts in data.items():
                    if isinstance(exts, list):
                        cleaned[str(cat)] = [str(e).lower().lstrip(".") for e in exts]
                if cleaned:
                    cleaned.setdefault("Other", [])
                    return cleaned
        except (json.JSONDecodeError, OSError):
            pass
    return {k: list(v) for k, v in DEFAULT_RULES.items()}


def save_rules(rules: dict[str, list[str]], rules_path: Path) -> None:
    Path(rules_path).write_text(
        json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def category_for(path: Path, ext_map: dict[str, str]) -> str:
    ext = path.suffix.lower().lstrip(".")
    if not ext:
        return "Other"
    return ext_map.get(ext, "Other")


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------
def is_hidden(path: Path) -> bool:
    try:
        attrs = path.stat().st_file_attributes  # Windows only
        return bool(attrs & 0x2)  # FILE_ATTRIBUTE_HIDDEN
    except (AttributeError, OSError):
        return path.name.startswith(".")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _iter_files(folder: Path, include_subfolders: bool, category_names: set[str]):
    """Yield candidate files that are not already inside a category folder."""
    walker = folder.rglob("*") if include_subfolders else folder.glob("*")
    for entry in walker:
        try:
            if not entry.is_file():
                continue
        except OSError:
            continue
        if entry.name.lower() in SKIP_NAMES:
            continue
        if is_hidden(entry):
            continue
        # Skip anything already sitting inside one of our category folders
        if any(part in category_names for part in entry.relative_to(folder).parts[:-1]):
            continue
        yield entry


def scan(folder: str | Path, rules: dict[str, list[str]],
         include_subfolders: bool = False,
         exclude_dirs: list[str] | None = None) -> list[dict]:
    """Return a list of {path, category, size, mtime} for candidate files.

    ``exclude_dirs`` lets the caller hide the destination root (e.g. the
    "Sorted Files" folder) so its contents are never re-scanned.
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder}")
    ext_map = build_extension_map(rules)
    category_names = set(rules.keys()) | {FOLDER_CATEGORY}
    excluded = [Path(p).resolve() for p in (exclude_dirs or []) if p]

    results: list[dict] = []
    for entry in _iter_files(folder, include_subfolders, category_names):
        if excluded:
            try:
                resolved = entry.parent.resolve()
            except OSError:
                resolved = entry.parent
            if any(_is_within(resolved, ex) for ex in excluded):
                continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        results.append({
            "path": str(entry),
            "category": category_for(entry, ext_map),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        })
    return results


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------
def _unique_destination(dest: Path, reserved: set[str]) -> Path:
    """Avoid overwriting: name (1).ext, name (2).ext ..."""
    candidate = dest
    counter = 1
    while candidate.exists() or str(candidate).lower() in reserved:
        stem, suffix = dest.stem, dest.suffix
        candidate = dest.with_name(f"{stem} ({counter}){suffix}")
        counter += 1
    reserved.add(str(candidate).lower())
    return candidate


def build_plan(entries: list[dict], destination_root: str | Path,
               group_by_date: bool = False) -> list[dict]:
    """Turn scan entries into concrete move operations into <dest>/<Category>/."""
    dest_root = Path(destination_root)
    reserved: set[str] = set()
    plan: list[dict] = []
    for item in entries:
        src = Path(item["path"])
        dest_dir = dest_root / item["category"]
        if group_by_date:
            try:
                stamp = datetime.fromtimestamp(item["mtime"]).strftime("%Y-%m")
            except (OSError, OverflowError, ValueError):
                stamp = "unknown"
            dest_dir = dest_dir / stamp
        dest = _unique_destination(dest_dir / src.name, reserved)
        plan.append({
            "src": str(src),
            "dest": str(dest),
            "category": item["category"],
            "size": item["size"],
        })
    return plan


def summarize(plan: list[dict]) -> dict[str, dict]:
    """category -> {count, bytes} for preview tables."""
    out: dict[str, dict] = {}
    for op in plan:
        bucket = out.setdefault(op["category"], {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += op["size"]
    return dict(sorted(out.items(), key=lambda kv: (-kv[1]["count"], kv[0])))


# ---------------------------------------------------------------------------
# Scanning existing FOLDERS (not files)
# ---------------------------------------------------------------------------
def _dir_size(path: Path, cap: int = 1_000) -> int:
    """Bounded recursive size so a huge folder can't hang the preview."""
    total = 0
    seen = 0
    try:
        for item in path.rglob("*"):
            try:
                if item.is_file():
                    total += item.stat().st_size
                    seen += 1
                    if seen >= cap:
                        break
            except OSError:
                continue
    except OSError:
        pass
    return total


def scan_directories(folder: str | Path, rules: dict[str, list[str]],
                     exclude_dirs: list[str] | None = None) -> list[dict]:
    """Return top-level folders that should be gathered into <dest>/Folders/.

    The destination root itself (e.g. "Sorted Files"), our category folders,
    hidden folders and Windows system folders are all skipped.
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder}")
    category_names = {c.lower() for c in rules.keys()} | {FOLDER_CATEGORY.lower()}
    skip_names = category_names | SYSTEM_DIR_NAMES
    excluded = [Path(p).resolve() for p in (exclude_dirs or []) if p]
    for ex in excluded:
        skip_names.add(ex.name.lower())

    out: list[dict] = []
    for entry in folder.glob("*"):
        try:
            if not entry.is_dir() or entry.is_symlink():
                continue
        except OSError:
            continue
        if entry.name.lower() in skip_names or is_hidden(entry):
            continue
        try:
            resolved = entry.resolve()
        except OSError:
            resolved = entry
        if any(resolved == ex or _is_within(resolved, ex) for ex in excluded):
            continue
        try:
            mtime = entry.stat().st_mtime
        except OSError:
            mtime = 0
        out.append({
            "path": str(entry),
            "category": FOLDER_CATEGORY,
            "size": _dir_size(entry),
            "mtime": mtime,
            "is_dir": True,
        })
    return out


def scan_subfolders_detail(folder: str | Path, rules: dict[str, list[str]],
                           exclude_dirs: list[str] | None = None) -> list[dict]:
    """Scan top-level subfolders with detailed file breakdowns for the Subfolders tab."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    ext_map = build_extension_map(rules)
    category_names = {c.lower() for c in rules.keys()} | {FOLDER_CATEGORY.lower()}
    skip_names = category_names | SYSTEM_DIR_NAMES
    excluded = [Path(p).resolve() for p in (exclude_dirs or []) if p]
    for ex in excluded:
        skip_names.add(ex.name.lower())

    out: list[dict] = []
    for entry in folder.glob("*"):
        try:
            if not entry.is_dir() or entry.is_symlink():
                continue
        except OSError:
            continue
        if entry.name.lower() in skip_names or is_hidden(entry):
            continue
        try:
            resolved = entry.resolve()
        except OSError:
            resolved = entry
        if any(resolved == ex or _is_within(resolved, ex) for ex in excluded):
            continue

        file_count = 0
        total_size = 0
        cat_counts: dict[str, int] = {}
        sample_files: list[dict] = []

        try:
            for item in entry.rglob("*"):
                try:
                    if item.is_file() and not is_hidden(item) and item.name.lower() not in SKIP_NAMES:
                        file_count += 1
                        sz = item.stat().st_size
                        total_size += sz
                        cat = category_for(item, ext_map)
                        cat_counts[cat] = cat_counts.get(cat, 0) + 1
                        if len(sample_files) < 6:
                            sample_files.append({
                                "name": item.name,
                                "category": cat,
                                "size": sz,
                                "size_human": human_size(sz)
                            })
                except OSError:
                    continue
        except OSError:
            pass

        try:
            mtime = entry.stat().st_mtime
            mod_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        except OSError:
            mtime = 0
            mod_str = "Unknown"

        out.append({
            "name": entry.name,
            "path": str(entry),
            "file_count": file_count,
            "size": total_size,
            "size_human": human_size(total_size),
            "mtime": mtime,
            "modified": mod_str,
            "category_counts": cat_counts,
            "sample_files": sample_files,
            "status": "intact",
        })

    out.sort(key=lambda x: (x["file_count"], x["size"]), reverse=True)
    return out


def plan_subfolder_assort(subfolder_path: str | Path, destination_root: str | Path,
                          rules: dict[str, list[str]], group_by_date: bool = False) -> list[dict]:
    """Create a plan to move all loose files from inside a subfolder into destination categories."""
    sub_path = Path(subfolder_path)
    if not sub_path.is_dir():
        return []
    ext_map = build_extension_map(rules)
    entries: list[dict] = []
    for item in sub_path.rglob("*"):
        try:
            if item.is_file() and not is_hidden(item) and item.name.lower() not in SKIP_NAMES:
                stat = item.stat()
                entries.append({
                    "path": str(item),
                    "category": category_for(item, ext_map),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                })
        except OSError:
            continue
    return build_plan(entries, destination_root, group_by_date=group_by_date)


# ---------------------------------------------------------------------------
# Destination folder tree
# ---------------------------------------------------------------------------
def create_destination_tree(destination_root: str | Path,
                            rules: dict[str, list[str]]) -> list[str]:
    """Create the segregation folder and one sub-folder per category."""
    root = Path(destination_root)
    root.mkdir(parents=True, exist_ok=True)
    created = [str(root)]
    for category in list(rules) + [FOLDER_CATEGORY]:
        if category == FOLDER_CATEGORY and FOLDER_CATEGORY in rules:
            continue
        sub = root / category
        sub.mkdir(parents=True, exist_ok=True)
        created.append(str(sub))
    return created


# ---------------------------------------------------------------------------
# Executing + undo
# ---------------------------------------------------------------------------
def execute(plan: list[dict], undo_dir: str | Path,
            write_undo: bool = True) -> dict:
    """Perform the moves. Returns {moved, errors, undo_path}."""
    undo_dir = Path(undo_dir)
    moved: list[dict] = []
    errors: list[dict] = []
    for op in plan:
        src = Path(op["src"])
        dest = Path(op["dest"])
        try:
            if not src.exists():
                errors.append({"src": str(src), "error": "source missing"})
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            moved.append({"src": str(src), "dest": str(dest),
                          "category": op["category"], "size": op["size"]})
        except (OSError, shutil.Error) as exc:
            errors.append({"src": str(src), "error": str(exc)})

    undo_path = None
    if write_undo and moved:
        try:
            undo_dir.mkdir(parents=True, exist_ok=True)
            undo_path = undo_dir / UNDO_FILE_NAME
            payload = {"created": time.time(), "moves": moved}
            undo_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
        except OSError:
            undo_path = None

    return {"moved": moved, "errors": errors,
            "undo_path": str(undo_path) if undo_path else None}


def cleanup_empty_dirs(folder: str | Path, keep: set[str] | None = None) -> None:
    """Remove empty directories under ``folder`` (never ``folder`` itself)."""
    folder = Path(folder)
    keep = {str(Path(k)) for k in (keep or set())}
    for path in sorted(folder.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and str(path) not in keep:
            try:
                if not any(path.iterdir()):
                    path.rmdir()
            except OSError:
                pass


def undo_last(undo_dir: str | Path) -> dict:
    """Restore the files moved by the previous run."""
    undo_dir = Path(undo_dir)
    undo_path = undo_dir / UNDO_FILE_NAME
    if not undo_path.is_file():
        return {"restored": [], "errors": [], "message": "No undo record found."}
    try:
        payload = json.loads(undo_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"restored": [], "errors": [], "message": f"Unreadable undo file: {exc}"}

    restored: list[dict] = []
    errors: list[dict] = []
    for move in reversed(payload.get("moves", [])):
        src = Path(move["src"])    # original location
        dest = Path(move["dest"])  # where we put it
        try:
            if not dest.exists():
                errors.append({"dest": str(dest), "error": "file no longer there"})
                continue
            src.parent.mkdir(parents=True, exist_ok=True)
            target = src if not src.exists() else _unique_destination(src, set())
            shutil.move(str(dest), str(target))
            restored.append({"dest": str(target)})
        except (OSError, shutil.Error) as exc:
            errors.append({"dest": str(dest), "error": str(exc)})

    if not errors:
        try:
            undo_path.unlink()
        except OSError:
            pass
    cleanup_empty_dirs(undo_dir)
    return {"restored": restored, "errors": errors,
            "message": f"Restored {len(restored)} file(s) to their original places."}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def human_size(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024:
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


def known_folder(name: str) -> Path:
    """Resolve a standard user folder (Desktop, Downloads, Documents…) to a Path.

    Handles the common OneDrive-redirected Desktop/Documents layouts as well.
    """
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    onedrive = os.environ.get("OneDrive", "")
    candidates: list[Path] = [home / name, home / "OneDrive" / name]
    if onedrive:
        candidates.insert(1, Path(onedrive) / name)
    for candidate in candidates:
        try:
            if candidate and candidate.is_dir():
                return candidate
        except OSError:
            continue
    return home / name


def default_desktop() -> Path:
    """Best-effort Desktop path on Windows, with fallbacks."""
    return known_folder("Desktop")
