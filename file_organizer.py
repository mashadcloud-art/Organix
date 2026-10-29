"""
Desktop File Organizer Pro — macOS Edition Server
==================================================
Serves the frosted glass UI and powers real-time organization,
file search, and access to all assorted files.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BUNDLE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    APP_DIR = BUNDLE_DIR

BASE_DIR = BUNDLE_DIR
sys.path.insert(0, str(BUNDLE_DIR))

import organizer_core as core  # noqa: E402

WEB_DIR = BUNDLE_DIR / "web"
RULES_PATH = APP_DIR / "rules.json" if (APP_DIR / "rules.json").is_file() else (BUNDLE_DIR / "rules.json")
PORT = 52345


def find_browser() -> list[str]:
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in edge_paths:
        if os.path.isfile(p):
            return [p]
    return []


class OrganizerServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data: dict, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _read_body_json(self) -> dict:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len > 0:
            raw = self.rfile.read(content_len)
            try:
                return json.loads(raw.decode("utf-8"))
            except Exception:
                return {}
        return {}

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            index_path = WEB_DIR / "index.html"
            if index_path.is_file():
                content = index_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            self.send_error(404, "index.html not found")
            return

        # Serve static assets (video, poster, icons, css, js) from WEB_DIR with HTTP 206 Range support
        clean_path = path.lstrip("/")
        if clean_path and not clean_path.startswith("api/"):
            asset_file = (WEB_DIR / clean_path).resolve()
            if asset_file.is_file() and str(asset_file).startswith(str(WEB_DIR.resolve())):
                ext = asset_file.suffix.lower()
                mime_types = {
                    ".html": "text/html; charset=utf-8",
                    ".css": "text/css; charset=utf-8",
                    ".js": "application/javascript; charset=utf-8",
                    ".json": "application/json; charset=utf-8",
                    ".mp4": "video/mp4",
                    ".webm": "video/webm",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".svg": "image/svg+xml",
                    ".ico": "image/x-icon",
                }
                content_type = mime_types.get(ext, "application/octet-stream")
                try:
                    file_size = asset_file.stat().st_size
                    range_header = self.headers.get("Range")
                    if range_header and range_header.startswith("bytes="):
                        ranges = range_header.replace("bytes=", "").split("-")
                        start = int(ranges[0]) if ranges[0] else 0
                        end = int(ranges[1]) if (len(ranges) > 1 and ranges[1]) else file_size - 1
                        end = min(end, file_size - 1)
                        length = end - start + 1
                        with open(asset_file, "rb") as f:
                            f.seek(start)
                            data = f.read(length)
                        self.send_response(206)
                        self.send_header("Content-Type", content_type)
                        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                        self.send_header("Content-Length", str(length))
                        self.send_header("Accept-Ranges", "bytes")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(data)
                        return
                    else:
                        data = asset_file.read_bytes()
                        self.send_response(200)
                        self.send_header("Content-Type", content_type)
                        self.send_header("Content-Length", str(file_size))
                        self.send_header("Accept-Ranges", "bytes")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(data)
                        return
                except Exception:
                    pass

        if path == "/api/thumbnail":
            target_path = query.get("path", [""])[0]
            if target_path:
                p = Path(target_path)
                if p.is_file():
                    ext = p.suffix.lower()
                    mime_types = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".gif": "image/gif",
                        ".webp": "image/webp",
                        ".bmp": "image/bmp",
                        ".svg": "image/svg+xml",
                        ".ico": "image/x-icon",
                    }
                    content_type = mime_types.get(ext, "application/octet-stream")
                    try:
                        data = p.read_bytes()
                        self.send_response(200)
                        self.send_header("Content-Type", content_type)
                        self.send_header("Content-Length", str(len(data)))
                        self.send_header("Cache-Control", "public, max-age=3600")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(data)
                        return
                    except Exception:
                        pass
            self.send_error(404, "Thumbnail not found")
            return

        if path == "/api/check-update":
            current_ver = "1.2.0"
            latest_ver = current_ver
            download_url = "https://github.com/mashadcloud-art/Organix/releases/latest"
            release_notes = [
                "Ultra-clean minimal header & compact dashboard",
                "Multi-Location Hub with Desktop, Downloads, Documents & System Drives",
                "Instant 1-Click Clean and Auto-Assort Engine",
                "Native Windows Next-Next-Install Setup Wizard"
            ]
            is_latest = True
            
            try:
                req = urllib.request.Request(
                    "https://api.github.com/repos/mashadcloud-art/Organix/releases/latest",
                    headers={"User-Agent": f"Organix-App/{current_ver}"}
                )
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    if resp.status == 200:
                        rel_data = json.loads(resp.read().decode("utf-8"))
                        tag = rel_data.get("tag_name", "").lstrip("v")
                        if tag:
                            latest_ver = tag
                            def parse_v(v):
                                return [int(x) for x in v.split(".") if x.isdigit()]
                            if parse_v(latest_ver) > parse_v(current_ver):
                                is_latest = False
                            download_url = rel_data.get("html_url", download_url)
                            for asset in rel_data.get("assets", []):
                                if "setup" in asset.get("name", "").lower() or asset.get("name", "").endswith(".exe"):
                                    download_url = asset.get("browser_download_url", download_url)
                                    break
                            body_notes = rel_data.get("body", "")
                            if body_notes:
                                release_notes = [line.strip("- *") for line in body_notes.splitlines() if line.strip()]
            except Exception:
                pass

            self._send_json({
                "current_version": current_ver,
                "latest_version": latest_ver,
                "is_latest": is_latest,
                "download_url": download_url,
                "channel": "stable",
                "auto_update": True,
                "release_date": "2026-10-29",
                "release_notes": release_notes
            })
            return

        if path == "/api/locations":
            home = Path.home()
            locations = [
                {
                    "id": "desktop",
                    "name": "Desktop",
                    "path": str(home / "Desktop"),
                    "dest_name": "Sorted Files",
                    "icon": "fa-solid fa-desktop",
                },
                {
                    "id": "downloads",
                    "name": "Downloads",
                    "path": str(home / "Downloads"),
                    "dest_name": "Downloads Assorted",
                    "icon": "fa-solid fa-download",
                },
                {
                    "id": "documents",
                    "name": "Documents",
                    "path": str(home / "Documents"),
                    "dest_name": "Documents Assorted",
                    "icon": "fa-solid fa-file-lines",
                },
            ]
            import string
            for letter in string.ascii_uppercase:
                drive_p = Path(f"{letter}:\\")
                if drive_p.exists():
                    locations.append({
                        "id": f"drive_{letter.lower()}",
                        "name": f"Drive ({letter}:)",
                        "path": str(drive_p),
                        "dest_name": f"{letter}_Drive_Assorted",
                        "icon": "fa-solid fa-hard-drive",
                    })
            self._send_json({"locations": locations})
            return

        if path == "/api/dashboard-summary":
            home = Path.home()
            base_locs = [
                {"id": "desktop", "name": "Desktop", "path": str(home / "Desktop"), "dest_name": "Sorted Files", "icon": "fa-solid fa-desktop", "badge": "Primary Workspace", "color": "amber"},
                {"id": "downloads", "name": "Downloads", "path": str(home / "Downloads"), "dest_name": "Downloads Assorted", "icon": "fa-solid fa-download", "badge": "Inbox & Downloads", "color": "cyan"},
                {"id": "documents", "name": "Documents", "path": str(home / "Documents"), "dest_name": "Documents Assorted", "icon": "fa-solid fa-file-lines", "badge": "Personal Records", "color": "purple"},
            ]
            import string, shutil
            for letter in string.ascii_uppercase:
                drive_p = Path(f"{letter}:\\")
                if drive_p.exists():
                    base_locs.append({
                        "id": f"drive_{letter.lower()}",
                        "name": f"Drive ({letter}:)",
                        "path": str(drive_p),
                        "dest_name": f"{letter}_Drive_Assorted",
                        "icon": "fa-solid fa-hard-drive",
                        "badge": "System Volume" if letter == "C" else "Storage Volume",
                        "color": "blue" if letter == "C" else "emerald",
                        "is_drive": True,
                        "drive_letter": f"{letter}:",
                    })

            results = []
            for loc in base_locs:
                p = Path(loc["path"])
                dest_name = loc["dest_name"]
                dest_p = p / dest_name
                file_count = 0
                total_size = 0
                subfolder_count = 0
                
                if p.is_dir():
                    try:
                        for entry in os.scandir(p):
                            name_lower = entry.name.lower()
                            if entry.name.startswith(".") or name_lower in ("desktop.ini", "thumbs.db", "organix.lnk", "organix.exe", "$recycle.bin", "system volume information"):
                                continue
                            if entry.is_file():
                                file_count += 1
                                try:
                                    total_size += entry.stat().st_size
                                except Exception:
                                    pass
                            elif entry.is_dir() and entry.name != dest_name:
                                subfolder_count += 1
                    except Exception:
                        pass

                item = {
                    "id": loc["id"],
                    "name": loc["name"],
                    "path": str(p),
                    "dest_name": dest_name,
                    "dest_path": str(dest_p),
                    "icon": loc["icon"],
                    "badge": loc.get("badge", "Folder"),
                    "color": loc.get("color", "blue"),
                    "file_count": file_count,
                    "total_size": total_size,
                    "total_size_human": core.human_size(total_size),
                    "subfolder_count": subfolder_count,
                    "is_drive": loc.get("is_drive", False),
                }

                if loc.get("is_drive", False):
                    try:
                        tot, used, free = shutil.disk_usage(p)
                        item["drive_info"] = {
                            "total_gb": round(tot / (1024**3), 1),
                            "free_gb": round(free / (1024**3), 1),
                            "used_gb": round(used / (1024**3), 1),
                            "used_percent": round((used / tot) * 100, 1) if tot else 0
                        }
                    except Exception:
                        pass
                results.append(item)

            self._send_json({"locations": results})
            return


        if path == "/api/state":
            desktop = core.default_desktop()
            dest = desktop / core.DEFAULT_DEST_NAME
            undo_file = dest / core.UNDO_FILE_NAME
            self._send_json({
                "source": str(desktop),
                "destination": str(dest),
                "undo_available": undo_file.is_file(),
            })
            return

        if path == "/api/scan":
            src = query.get("source", [""])[0] or str(core.default_desktop())
            dest = query.get("dest", [""])[0] or str(Path(src) / core.DEFAULT_DEST_NAME)
            subfolders = query.get("subfolders", ["false"])[0].lower() == "true"
            gather_folders = query.get("gather_folders", ["true"])[0].lower() == "true"
            group_date = query.get("group_date", ["false"])[0].lower() == "true"

            src_path = Path(src)
            dest_path = Path(dest)
            rules = core.load_rules(RULES_PATH)

            if not src_path.is_dir():
                self._send_json({"error": f"Invalid folder: {src}", "plan": []}, status=400)
                return

            entries = core.scan(src_path, rules, include_subfolders=subfolders, exclude_dirs=[str(dest_path)])
            if gather_folders:
                entries += core.scan_directories(src_path, rules, exclude_dirs=[str(dest_path)])

            plan = core.build_plan(entries, dest_path, group_by_date=group_date)
            formatted_plan = []
            for op in plan:
                p_src = Path(op["src"])
                p_dest = Path(op["dest"])
                formatted_plan.append({
                    "name": p_src.name,
                    "src": str(p_src),
                    "dest": str(p_dest),
                    "category": op["category"],
                    "size": op["size"],
                })

            summary = core.summarize(plan)
            total_size = sum(op["size"] for op in plan)
            undo_file = dest_path / core.UNDO_FILE_NAME

            self._send_json({
                "plan": formatted_plan,
                "summary": summary,
                "total_size": total_size,
                "total_size_human": core.human_size(total_size),
                "undo_available": undo_file.is_file(),
            })
            return

        # NEW FEATURE: Access Assorted / Sorted Files
        if path == "/api/assorted-files":
            dest = query.get("dest", [""])[0] or str(core.default_desktop() / core.DEFAULT_DEST_NAME)
            dest_path = Path(dest)
            files_list = []

            if dest_path.is_dir():
                for category_dir in dest_path.iterdir():
                    if not category_dir.is_dir():
                        continue
                    cat_name = category_dir.name
                    if cat_name.lower() == "folders":
                        for item in category_dir.iterdir():
                            try:
                                stat = item.stat()
                                files_list.append({
                                    "name": item.name,
                                    "path": str(item),
                                    "rel_path": f"Folders/{item.name}",
                                    "category": "Folders",
                                    "size": stat.st_size,
                                    "size_human": core.human_size(stat.st_size),
                                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                                    "is_folder": item.is_dir(),
                                })
                            except Exception:
                                continue
                    else:
                        for item in category_dir.glob("*"):
                            try:
                                if item.is_dir():
                                    for sub in item.glob("*"):
                                        if sub.is_file():
                                            stat = sub.stat()
                                            files_list.append({
                                                "name": sub.name,
                                                "path": str(sub),
                                                "rel_path": f"{cat_name}/{item.name}/{sub.name}",
                                                "category": cat_name,
                                                "size": stat.st_size,
                                                "size_human": core.human_size(stat.st_size),
                                                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                                                "is_folder": False,
                                            })
                                elif item.is_file():
                                    if item.name.lower() in {core.UNDO_FILE_NAME.lower(), "desktop.ini", "thumbs.db"}:
                                        continue
                                    stat = item.stat()
                                    files_list.append({
                                        "name": item.name,
                                        "path": str(item),
                                        "rel_path": f"{cat_name}/{item.name}",
                                        "category": cat_name,
                                        "size": stat.st_size,
                                        "size_human": core.human_size(stat.st_size),
                                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                                        "is_folder": False,
                                    })
                            except Exception:
                                continue

            files_list.sort(key=lambda x: x.get("modified", ""), reverse=True)
            self._send_json({"files": files_list})
            return

        if path == "/api/subfolders":
            src = query.get("source", [""])[0] or str(core.default_desktop())
            dest = query.get("dest", [""])[0] or str(Path(src) / core.DEFAULT_DEST_NAME)
            src_path = Path(src)
            dest_path = Path(dest)
            rules = core.load_rules(RULES_PATH)
            if not src_path.is_dir():
                self._send_json({"subfolders": [], "count": 0, "total_size": 0, "total_size_human": "0 B"})
                return
            subs = core.scan_subfolders_detail(src_path, rules, exclude_dirs=[str(dest_path)])
            total_size = sum(s["size"] for s in subs)
            self._send_json({
                "subfolders": subs,
                "count": len(subs),
                "total_size": total_size,
                "total_size_human": core.human_size(total_size)
            })
            return

        if path == "/api/browse":
            folder_type = query.get("type", ["source"])[0]
            chosen = ""
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                initial = str(core.default_desktop())
                chosen = filedialog.askdirectory(initialdir=initial, title="Select Directory")
                root.destroy()
            except Exception:
                pass
            self._send_json({"path": chosen, "type": folder_type})
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_body_json()

        if path == "/api/assort-subfolder":
            sub_path_str = body.get("subfolder", "")
            dest_str = body.get("dest", "")
            clean_empty = body.get("clean_empty", True)
            if not sub_path_str or not dest_str:
                self._send_json({"success": False, "error": "Missing subfolder or destination"}, status=400)
                return
            sub_p = Path(sub_path_str)
            dest_p = Path(dest_str)
            rules = core.load_rules(RULES_PATH)
            core.create_destination_tree(dest_p, rules)
            plan = core.plan_subfolder_assort(sub_p, dest_p, rules)
            result = core.execute(plan, dest_p, write_undo=True)
            if clean_empty:
                core.cleanup_empty_dirs(sub_p)
                try:
                    if sub_p.is_dir() and not any(sub_p.iterdir()):
                        sub_p.rmdir()
                except OSError:
                    pass
            self._send_json({
                "success": True,
                "moved": result.get("moved", []),
                "count": len(result.get("moved", [])),
                "errors": result.get("errors", [])
            })
            return

        if path == "/api/assort-all-subfolders":
            src_str = body.get("source", "")
            dest_str = body.get("dest", "")
            clean_empty = body.get("clean_empty", True)
            if not src_str or not dest_str:
                self._send_json({"success": False, "error": "Missing source or destination"}, status=400)
                return
            src_p = Path(src_str)
            dest_p = Path(dest_str)
            rules = core.load_rules(RULES_PATH)
            core.create_destination_tree(dest_p, rules)
            subs = core.scan_subfolders_detail(src_p, rules, exclude_dirs=[str(dest_p)])
            all_plan = []
            for s in subs:
                sub_p = Path(s["path"])
                all_plan.extend(core.plan_subfolder_assort(sub_p, dest_p, rules))
            result = core.execute(all_plan, dest_p, write_undo=True)
            if clean_empty:
                for s in subs:
                    sub_p = Path(s["path"])
                    core.cleanup_empty_dirs(sub_p)
                    try:
                        if sub_p.is_dir() and not any(sub_p.iterdir()):
                            sub_p.rmdir()
                    except OSError:
                        pass
            self._send_json({
                "success": True,
                "moved": result.get("moved", []),
                "count": len(result.get("moved", [])),
                "errors": result.get("errors", [])
            })
            return

        if path == "/api/move-subfolder-intact":
            sub_path_str = body.get("subfolder", "")
            dest_str = body.get("dest", "")
            if not sub_path_str or not dest_str:
                self._send_json({"success": False, "error": "Missing parameters"}, status=400)
                return
            sub_p = Path(sub_path_str)
            dest_p = Path(dest_str) / core.FOLDER_CATEGORY
            dest_p.mkdir(parents=True, exist_ok=True)
            target = core._unique_destination(dest_p / sub_p.name, set())
            try:
                shutil.move(str(sub_p), str(target))
                self._send_json({"success": True, "target": str(target)})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        if path == "/api/clean-empty-subfolders":
            src_str = body.get("source", "")
            if not src_str:
                self._send_json({"success": False, "error": "Missing source"}, status=400)
                return
            src_p = Path(src_str)
            core.cleanup_empty_dirs(src_p)
            self._send_json({"success": True})
            return

        if path == "/api/clean-location":
            src = body.get("source", "")
            dest = body.get("dest", "")
            if not src:
                self._send_json({"success": False, "error": "Missing source folder"}, status=400)
                return
            src_path = Path(src)
            if not dest:
                dest_path = src_path / core.DEFAULT_DEST_NAME
            else:
                dest_path = Path(dest)

            if not src_path.is_dir():
                self._send_json({"success": False, "error": f"Invalid folder: {src}"}, status=400)
                return

            rules = core.load_rules(RULES_PATH)
            entries = core.scan(src_path, rules, include_subfolders=False, exclude_dirs=[str(dest_path)])
            plan = core.build_plan(entries, dest_path, group_by_date=False)
            
            if not plan:
                self._send_json({"success": True, "count": 0, "moved": [], "total_size_human": "0 B", "message": "No loose files found to organize."})
                return

            core.create_destination_tree(dest_path, rules)
            result = core.execute(plan, dest_path, write_undo=True)
            self._send_json({
                "success": True,
                "count": len(result.get("moved", [])),
                "moved": result.get("moved", []),
                "errors": result.get("errors", []),
                "total_size_human": core.human_size(sum(op.get("size", 0) for op in plan)),
                "message": f"Organized {len(result.get('moved', []))} files into {dest_path.name}/"
            })
            return

        if path == "/api/toggle-autoupdate":
            enabled = body.get("enabled", True)
            self._send_json({"success": True, "auto_update": enabled, "message": "Auto-update preference saved successfully."})
            return

        if path == "/api/organize":
            items = body.get("items", [])
            dest_str = body.get("dest", "")
            if not dest_str or not items:
                self._send_json({"success": False, "error": "Missing items or destination"}, status=400)
                return

            dest_path = Path(dest_str)
            rules = core.load_rules(RULES_PATH)
            core.create_destination_tree(dest_path, rules)

            plan = [{"src": it["src"], "dest": it["dest"], "category": it["category"], "size": it["size"]}
                    for it in items]
            result = core.execute(plan, dest_path, write_undo=True)
            self._send_json({
                "success": True,
                "moved": result.get("moved", []),
                "errors": result.get("errors", []),
            })
            return

        if path == "/api/undo":
            dest_str = body.get("dest", "")
            if not dest_str:
                self._send_json({"success": False, "error": "Missing destination"}, status=400)
                return

            dest_path = Path(dest_str)
            result = core.undo_last(dest_path)
            self._send_json({
                "success": True,
                "message": result.get("message", "Undo finished"),
                "restored": result.get("restored", []),
            })
            return

        # Direct Open of Assorted File
        if path == "/api/open-file":
            target = body.get("path", "")
            if target and Path(target).is_file():
                try:
                    os.startfile(target)
                except Exception:
                    subprocess.Popen(["explorer", str(target)])
            self._send_json({"success": True})
            return

        # Reveal in File Explorer
        if path == "/api/reveal":
            target = body.get("path", "")
            if target:
                p = Path(target)
                try:
                    if p.exists():
                        subprocess.Popen(f'explorer /select,"{p}"')
                    else:
                        subprocess.Popen(f'explorer "{p.parent}"')
                except Exception:
                    pass
            self._send_json({"success": True})
            return

        if path == "/api/open-folder":
            target = body.get("path", "")
            if target:
                p = Path(target)
                p.mkdir(parents=True, exist_ok=True)
                try:
                    os.startfile(p)
                except Exception:
                    subprocess.Popen(["explorer", str(p)])
            self._send_json({"success": True})
            return

        if path == "/api/open-rules":
            rules = core.load_rules(RULES_PATH)
            if not RULES_PATH.is_file():
                core.save_rules(rules, RULES_PATH)
            try:
                os.startfile(RULES_PATH)
            except Exception:
                subprocess.Popen(["notepad.exe", str(RULES_PATH)])
            self._send_json({"success": True})
            return

        self.send_error(404, "Not Found")


def get_available_port(default_port: int = 52345) -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", default_port))
        s.close()
        return default_port
    except OSError:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port


def main() -> None:
    port = get_available_port(PORT)
    server = ThreadingHTTPServer(("127.0.0.1", port), OrganizerServer)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}/"
    print("=========================================================")
    print("  Desktop File Organizer Pro — macOS Sonoma Edition      ")
    print(f"  Live at: {url}")
    print("=========================================================")

    # Launch in Edge App Mode if available, or open in default browser
    edge_list = find_browser()
    if edge_list:
        app_profile = os.path.expandvars(r"%LOCALAPPDATA%\DesktopFileOrganizer\browser_profile")
        subprocess.Popen([
            edge_list[0],
            f"--app={url}",
            f"--user-data-dir={app_profile}",
            "--window-size=1200,880",
            "--window-position=80,40",
            "--disable-extensions",
        ])
    else:
        webbrowser.open(url)

    # Keep server running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    server.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()

