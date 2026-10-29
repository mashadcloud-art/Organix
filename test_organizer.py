"""
Headless self-test for organizer_core.py
Run:  python test_organizer.py
Creates a throwaway "desktop" with files of every kind plus some loose
folders, organizes everything into a "Sorted Files" segregation folder,
verifies, then undoes and verifies again.
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import organizer_core as core  # noqa: E402

SAMPLES = {
    "holiday.jpg": "Images",
    "logo.png": "Images",
    "report.pdf": "PDF",
    "notes.docx": "Documents",
    "readme.txt": "Documents",
    "budget.xlsx": "Spreadsheets",
    "pitch.pptx": "Presentations",
    "clip.mp4": "Videos",
    "song.mp3": "Audio",
    "backup.zip": "Archives",
    "setup.exe": "Installers",
    "app.apk": "Installers",
    "script.py": "Code",
    "index.html": "Code",
    "font.ttf": "Fonts",
    "novel.epub": "Ebooks",
    "Chrome.lnk": "Shortcuts",
    "mystery.xyz": "Other",
    "no_extension": "Other",
}

LOOSE_FOLDERS = ["MyProject", "Old Stuff", "random folder"]


def build_fixture(root: Path) -> None:
    for name in SAMPLES:
        (root / name).write_text("x" * 10, encoding="utf-8")
    for name in LOOSE_FOLDERS:
        (root / name).mkdir()
        (root / name / "inside.txt").write_text("hi", encoding="utf-8")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="organizer_test_"))
    try:
        build_fixture(tmp)
        rules = core.load_rules(None)
        dest = tmp / core.DEFAULT_DEST_NAME  # "Sorted Files"

        # 1) scan files
        entries = core.scan(tmp, rules, exclude_dirs=[str(dest)])
        assert len(entries) == len(SAMPLES), f"scan found {len(entries)}, expected {len(SAMPLES)}"
        print(f"[ok] scan found {len(entries)} files")

        # 2) scan folders
        dirs = core.scan_directories(tmp, rules, exclude_dirs=[str(dest)])
        got_dirs = sorted(Path(d["path"]).name for d in dirs)
        assert got_dirs == sorted(LOOSE_FOLDERS), f"folders found: {got_dirs}"
        assert all(d["category"] == core.FOLDER_CATEGORY for d in dirs)
        print(f"[ok] scan found {len(dirs)} loose folders -> '{core.FOLDER_CATEGORY}'")

        # 3) routing
        plan = core.build_plan(entries, dest)
        by_cat = {}
        for op in plan:
            by_cat.setdefault(op["category"], []).append(Path(op["src"]).name)
        for name, expected in SAMPLES.items():
            assert name in by_cat.get(expected, []), \
                f"{name} -> expected {expected}, got {[k for k, v in by_cat.items() if name in v]}"
        print("[ok] every file routed to the expected category")

        # 4) destination tree
        created = core.create_destination_tree(dest, rules)
        assert dest.is_dir()
        for cat in list(rules) + [core.FOLDER_CATEGORY]:
            assert (dest / cat).is_dir(), f"missing category folder {cat}"
        print(f"[ok] created segregation folder + {len(created) - 1} sub-folders")

        # 5) execute (files + folders)
        result = core.execute(plan, dest)
        assert not result["errors"], f"errors: {result['errors']}"
        assert len(result["moved"]) == len(SAMPLES)
        for name, expected in SAMPLES.items():
            assert (dest / expected / name).is_file(), f"{expected}/{name} missing"
        assert not [p for p in tmp.iterdir() if p.is_file()], "loose files left behind"
        print(f"[ok] moved {len(result['moved'])} files into {dest.name}/<category>/")

        dir_result = core.execute(core.build_plan(dirs, dest), dest)
        assert not dir_result["errors"], f"folder errors: {dir_result['errors']}"
        for name in LOOSE_FOLDERS:
            assert (dest / core.FOLDER_CATEGORY / name / "inside.txt").is_file(), \
                f"{name} not gathered"
        print(f"[ok] gathered {len(dir_result['moved'])} folders into {core.FOLDER_CATEGORY}/")

        # 6) re-scan must ignore the destination and be empty
        rescan = core.scan(tmp, rules, include_subfolders=True, exclude_dirs=[str(dest)])
        rescan += core.scan_directories(tmp, rules, exclude_dirs=[str(dest)])
        assert rescan == [], f"re-scan should be empty, got {len(rescan)}"
        print("[ok] re-scan ignores everything inside the segregation folder")

        # 7) undo everything (two runs -> undo twice)
        undo2 = core.undo_last(dest)
        assert not undo2["errors"], f"undo2 errors: {undo2['errors']}"
        for name in LOOSE_FOLDERS:
            assert (tmp / name / "inside.txt").is_file(), f"{name} not restored"
        print(f"[ok] undo restored {len(undo2['restored'])} folders to the desktop")

        # 8) collision safety
        (dest / "Images").mkdir(parents=True, exist_ok=True)
        (dest / "Images" / "holiday.jpg").write_text("existing", encoding="utf-8")
        (tmp / "holiday.jpg").write_text("new", encoding="utf-8")
        plan2 = core.build_plan(core.scan(tmp, rules, exclude_dirs=[str(dest)]), dest)
        core.execute(plan2, dest)
        assert (dest / "Images" / "holiday (1).jpg").is_file(), "collision rename failed"
        assert (dest / "Images" / "holiday.jpg").read_text(encoding="utf-8") == "existing"
        print("[ok] name collisions are renamed, not overwritten")

        # 9) known folders helper
        for name in ("Desktop", "Downloads", "Documents"):
            assert core.known_folder(name).name == name
        print("[ok] known-folder helper resolves presets")

        print("\nALL TESTS PASSED")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
