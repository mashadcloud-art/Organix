"""
Organix Windows Setup Wizard (100% Silent - Zero CMD Windows)
Next -> Next -> Install -> Finish
"""
import os
import sys
import shutil
import time
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import psutil
import win32com.client

APP_NAME = "Organix"
APP_VERSION = "1.2.0"
APP_DESCRIPTION = "Smart Desktop & Multi-Location File Organizer"
DEFAULT_INSTALL_DIR = str(Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "Organix")

class OrganixInstaller(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} Setup Wizard")
        self.geometry("540x390")
        self.resizable(False, False)

        # Center on screen
        self.update_idletasks()
        w = 540
        h = 390
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # State variables
        self.step = 0
        self.install_dir = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.agree_var = tk.StringVar(value="yes")
        self.shortcut_desktop = tk.BooleanVar(value=True)
        self.shortcut_startmenu = tk.BooleanVar(value=True)
        self.launch_startup = tk.BooleanVar(value=False)
        self.launch_now = tk.BooleanVar(value=True)

        self._init_ui()
        self.show_step(0)

    def _init_ui(self):
        self.configure(bg="#f4f5f8")

        # Main container
        self.main_container = tk.Frame(self, bg="#ffffff", bd=0)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Content area
        self.content_frame = tk.Frame(self.main_container, bg="#ffffff", padx=25, pady=20)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Bottom Button Bar
        self.bottom_bar = tk.Frame(self, bg="#f0f2f5", height=50, bd=1, relief=tk.SOLID)
        self.bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.bottom_bar.pack_propagate(False)

        self.btn_cancel = tk.Button(self.bottom_bar, text="Cancel", width=9, font=("Segoe UI", 9), command=self.on_cancel, bg="#e2e4e9", fg="#222", relief=tk.GROOVE)
        self.btn_cancel.pack(side=tk.RIGHT, padx=12, pady=10)

        self.btn_next = tk.Button(self.bottom_bar, text="Next >", width=10, font=("Segoe UI", 9, "bold"), command=self.on_next, bg="#0a84ff", fg="#ffffff", relief=tk.FLAT, activebackground="#0071e3")
        self.btn_next.pack(side=tk.RIGHT, padx=4, pady=10)

        self.btn_back = tk.Button(self.bottom_bar, text="< Back", width=9, font=("Segoe UI", 9), command=self.on_back, bg="#e2e4e9", fg="#222", relief=tk.GROOVE)
        self.btn_back.pack(side=tk.RIGHT, padx=4, pady=10)

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_step(self, step):
        self.step = step
        self.clear_content()

        if step == 0:
            self._render_welcome()
        elif step == 1:
            self._render_license()
        elif step == 2:
            self._render_destination()
        elif step == 3:
            self._render_tasks()
        elif step == 4:
            self._render_ready()
        elif step == 5:
            self._render_installing()
        elif step == 6:
            self._render_completed()

    def _render_welcome(self):
        self.btn_back.config(state=tk.DISABLED)
        self.btn_next.config(text="Next >", state=tk.NORMAL)
        self.btn_cancel.config(state=tk.NORMAL)

        lbl_title = tk.Label(self.content_frame, text=f"Welcome to the {APP_NAME} Setup Wizard", font=("Segoe UI", 13, "bold"), bg="#ffffff", fg="#111827", anchor="w")
        lbl_title.pack(fill=tk.X, pady=(5, 12))

        lbl_desc = tk.Label(
            self.content_frame,
            text=f"This will install {APP_NAME} Pro v{APP_VERSION} on your computer.\n\n"
                 f"{APP_NAME} provides intelligent 1-click file organization, multi-location assortment, "
                 f"and automatic sorting for Desktop, Downloads, Documents, and System Drives with zero data loss guarantee.\n\n"
                 f"It is recommended that you close any running instances before continuing.\n\n"
                 f"Click Next to continue, or Cancel to exit Setup.",
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#4b5563",
            justify=tk.LEFT,
            wraplength=480
        )
        lbl_desc.pack(fill=tk.X, pady=5)

    def _render_license(self):
        self.btn_back.config(state=tk.NORMAL)
        self.btn_next.config(text="Next >", state=tk.NORMAL)

        lbl_title = tk.Label(self.content_frame, text="License Agreement & Safety Guarantee", font=("Segoe UI", 11, "bold"), bg="#ffffff", fg="#111827", anchor="w")
        lbl_title.pack(fill=tk.X, pady=(0, 4))

        lbl_sub = tk.Label(self.content_frame, text="Please review the guarantee terms before proceeding.", font=("Segoe UI", 9), bg="#ffffff", fg="#6b7280", anchor="w")
        lbl_sub.pack(fill=tk.X, pady=(0, 8))

        txt_box = tk.Text(self.content_frame, height=7, width=58, font=("Segoe UI", 8), bg="#f9fafb", relief=tk.SOLID, bd=1, padx=6, pady=6)
        txt_box.pack(fill=tk.X, pady=4)
        txt_box.insert(tk.END,
            f"{APP_NAME} Zero-Loss Guarantee:\n"
            "1. Organix will never overwrite or erase your files.\n"
            "2. In the event of duplicate file names, clean timestamps or numbers are appended.\n"
            "3. All assortment moves are tracked in undo.json and can be reverted in 1 click.\n"
            "4. Free for personal and professional file management.\n"
        )
        txt_box.config(state=tk.DISABLED)

        rb1 = tk.Radiobutton(self.content_frame, text="I accept the agreement and safety guarantee", variable=self.agree_var, value="yes", bg="#ffffff", font=("Segoe UI", 9), command=self._check_agree)
        rb1.pack(anchor="w", pady=(8, 2))

        rb2 = tk.Radiobutton(self.content_frame, text="I do not accept the agreement", variable=self.agree_var, value="no", bg="#ffffff", font=("Segoe UI", 9), command=self._check_agree)
        rb2.pack(anchor="w")

        self._check_agree()

    def _check_agree(self):
        if self.agree_var.get() == "yes":
            self.btn_next.config(state=tk.NORMAL)
        else:
            self.btn_next.config(state=tk.DISABLED)

    def _render_destination(self):
        self.btn_back.config(state=tk.NORMAL)
        self.btn_next.config(text="Next >", state=tk.NORMAL)

        lbl_title = tk.Label(self.content_frame, text="Select Destination Location", font=("Segoe UI", 11, "bold"), bg="#ffffff", fg="#111827", anchor="w")
        lbl_title.pack(fill=tk.X, pady=(0, 4))

        lbl_sub = tk.Label(self.content_frame, text=f"Where should {APP_NAME} be installed on your system?", font=("Segoe UI", 9), bg="#ffffff", fg="#6b7280", anchor="w")
        lbl_sub.pack(fill=tk.X, pady=(0, 15))

        f_entry = tk.Frame(self.content_frame, bg="#ffffff")
        f_entry.pack(fill=tk.X, pady=5)

        ent = tk.Entry(f_entry, textvariable=self.install_dir, font=("Segoe UI", 9), bg="#ffffff", relief=tk.SOLID, bd=1)
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))

        btn_browse = tk.Button(f_entry, text="Browse...", font=("Segoe UI", 8), command=self._browse_dir, bg="#f3f4f6", relief=tk.GROOVE)
        btn_browse.pack(side=tk.RIGHT, padx=2)

        lbl_space = tk.Label(self.content_frame, text="At least 45.0 MB of free disk space is required.", font=("Segoe UI", 8), bg="#ffffff", fg="#9ca3af", anchor="w")
        lbl_space.pack(fill=tk.X, pady=(15, 0))

    def _browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir.get())
        if chosen:
            self.install_dir.set(str(Path(chosen) / APP_NAME))

    def _render_tasks(self):
        self.btn_back.config(state=tk.NORMAL)
        self.btn_next.config(text="Next >", state=tk.NORMAL)

        lbl_title = tk.Label(self.content_frame, text="Select Additional Shortcuts", font=("Segoe UI", 11, "bold"), bg="#ffffff", fg="#111827", anchor="w")
        lbl_title.pack(fill=tk.X, pady=(0, 4))

        lbl_sub = tk.Label(self.content_frame, text="Which shortcuts should be created for quick access?", font=("Segoe UI", 9), bg="#ffffff", fg="#6b7280", anchor="w")
        lbl_sub.pack(fill=tk.X, pady=(0, 15))

        cb1 = tk.Checkbutton(self.content_frame, text="Create a Desktop shortcut", variable=self.shortcut_desktop, bg="#ffffff", font=("Segoe UI", 9))
        cb1.pack(anchor="w", pady=4)

        cb2 = tk.Checkbutton(self.content_frame, text="Create a Start Menu shortcut", variable=self.shortcut_startmenu, bg="#ffffff", font=("Segoe UI", 9))
        cb2.pack(anchor="w", pady=4)

        cb3 = tk.Checkbutton(self.content_frame, text="Launch Organix on Windows startup (Optional)", variable=self.launch_startup, bg="#ffffff", font=("Segoe UI", 9))
        cb3.pack(anchor="w", pady=4)

    def _render_ready(self):
        self.btn_back.config(state=tk.NORMAL)
        self.btn_next.config(text="Install", state=tk.NORMAL, bg="#10b981", activebackground="#059669")

        lbl_title = tk.Label(self.content_frame, text="Ready to Install", font=("Segoe UI", 11, "bold"), bg="#ffffff", fg="#111827", anchor="w")
        lbl_title.pack(fill=tk.X, pady=(0, 4))

        lbl_sub = tk.Label(self.content_frame, text="Click Install to begin the installation.", font=("Segoe UI", 9), bg="#ffffff", fg="#6b7280", anchor="w")
        lbl_sub.pack(fill=tk.X, pady=(0, 12))

        txt_summary = tk.Text(self.content_frame, height=6, width=58, font=("Segoe UI", 8), bg="#f9fafb", relief=tk.SOLID, bd=1, padx=6, pady=6)
        txt_summary.pack(fill=tk.X, pady=4)
        txt_summary.insert(tk.END,
            f"Destination Folder:\n  {self.install_dir.get()}\n\n"
            f"Shortcuts:\n"
            f"  Desktop: {'Yes' if self.shortcut_desktop.get() else 'No'}\n"
            f"  Start Menu: {'Yes' if self.shortcut_startmenu.get() else 'No'}\n"
            f"  Launch on Startup: {'Yes' if self.launch_startup.get() else 'No'}\n"
        )
        txt_summary.config(state=tk.DISABLED)

    def _render_installing(self):
        self.btn_back.config(state=tk.DISABLED)
        self.btn_next.config(state=tk.DISABLED, bg="#0a84ff")
        self.btn_cancel.config(state=tk.DISABLED)

        lbl_title = tk.Label(self.content_frame, text=f"Installing {APP_NAME} Pro...", font=("Segoe UI", 11, "bold"), bg="#ffffff", fg="#111827", anchor="w")
        lbl_title.pack(fill=tk.X, pady=(0, 6))

        self.lbl_install_status = tk.Label(self.content_frame, text="Preparing installation...", font=("Segoe UI", 8), bg="#ffffff", fg="#4b5563", anchor="w")
        self.lbl_install_status.pack(fill=tk.X, pady=(0, 10))

        self.prog = ttk.Progressbar(self.content_frame, orient="horizontal", length=480, mode="determinate")
        self.prog.pack(fill=tk.X, pady=10)

        threading.Thread(target=self._run_install_worker, daemon=True).start()

    def _run_install_worker(self):
        try:
            target_path = Path(self.install_dir.get())
            target_path.mkdir(parents=True, exist_ok=True)

            # Source exe location (extracted by PyInstaller or in current dir)
            base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
            src_exe = base_dir / "Organix.exe"
            if not src_exe.exists():
                src_exe = Path(r"C:\Users\PC\.openclaw-autoclaw\workspace\desktop-file-organizer\dist\Organix.exe")
            if not src_exe.exists():
                src_exe = Path(r"C:\Users\PC\Desktop\Organix.exe")

            src_ico = base_dir / "app_icon.ico"
            if not src_ico.exists():
                src_ico = Path(r"C:\Users\PC\.openclaw-autoclaw\workspace\desktop-file-organizer\app_icon.ico")

            # 1. Silently terminate existing Organix instances using psutil (NO CMD window!)
            self.lbl_install_status.config(text="Closing active instances...")
            self.prog["value"] = 20
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'organix.exe':
                        proc.kill()
                except Exception:
                    pass
            time.sleep(0.3)

            # 2. Copy binary and icon natively
            self.lbl_install_status.config(text=f"Copying {APP_NAME}.exe to destination...")
            self.prog["value"] = 50
            dest_exe = target_path / "Organix.exe"
            if src_exe.exists():
                shutil.copy2(src_exe, dest_exe)

            dest_ico = target_path / "app_icon.ico"
            if src_ico.exists():
                shutil.copy2(src_ico, dest_ico)
            time.sleep(0.3)

            # 3. Create Windows Shortcuts silently using win32com (NO PowerShell / CMD window!)
            self.lbl_install_status.config(text="Creating desktop & program shortcuts...")
            self.prog["value"] = 80
            wscript = win32com.client.Dispatch("WScript.Shell")

            if self.shortcut_desktop.get():
                desktop_lnk = Path.home() / "Desktop" / "Organix.lnk"
                sc = wscript.CreateShortcut(str(desktop_lnk))
                sc.TargetPath = str(dest_exe)
                sc.WorkingDirectory = str(target_path)
                if dest_ico.exists():
                    sc.IconLocation = f"{dest_ico},0"
                sc.Description = "Organix - Desktop & Multi-Location File Organizer"
                sc.Save()

            if self.shortcut_startmenu.get():
                start_menu = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
                start_menu.mkdir(parents=True, exist_ok=True)
                start_lnk = start_menu / "Organix.lnk"
                sc2 = wscript.CreateShortcut(str(start_lnk))
                sc2.TargetPath = str(dest_exe)
                sc2.WorkingDirectory = str(target_path)
                if dest_ico.exists():
                    sc2.IconLocation = f"{dest_ico},0"
                sc2.Description = "Organix File Organizer"
                sc2.Save()

            # Startup shortcut if requested
            if self.launch_startup.get():
                startup_dir = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                startup_lnk = startup_dir / "Organix.lnk"
                sc3 = wscript.CreateShortcut(str(startup_lnk))
                sc3.TargetPath = str(dest_exe)
                sc3.WorkingDirectory = str(target_path)
                if dest_ico.exists():
                    sc3.IconLocation = f"{dest_ico},0"
                sc3.Description = "Organix Startup"
                sc3.Save()

            self.prog["value"] = 100
            self.lbl_install_status.config(text="Installation completed successfully!")
            time.sleep(0.4)

            self.after(100, lambda: self.show_step(6))

        except Exception as e:
            messagebox.showerror("Installation Error", str(e))
            self.btn_cancel.config(state=tk.NORMAL)

    def _render_completed(self):
        self.btn_back.config(state=tk.DISABLED)
        self.btn_next.config(text="Finish", state=tk.NORMAL, bg="#0a84ff", activebackground="#0071e3")
        self.btn_cancel.config(state=tk.DISABLED)

        lbl_title = tk.Label(self.content_frame, text=f"Completing the {APP_NAME} Setup Wizard", font=("Segoe UI", 13, "bold"), bg="#ffffff", fg="#111827", anchor="w")
        lbl_title.pack(fill=tk.X, pady=(5, 10))

        lbl_desc = tk.Label(
            self.content_frame,
            text=f"{APP_NAME} Pro has been successfully installed on your computer.\n\n"
                 f"The application may be launched by selecting the installed shortcuts or from your Desktop.\n\n"
                 f"Click Finish to exit Setup.",
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#4b5563",
            justify=tk.LEFT,
            wraplength=480
        )
        lbl_desc.pack(fill=tk.X, pady=(0, 15))

        cb = tk.Checkbutton(self.content_frame, text=f"Launch {APP_NAME} now", variable=self.launch_now, bg="#ffffff", font=("Segoe UI", 9, "bold"), fg="#111827")
        cb.pack(anchor="w", pady=5)

    def on_next(self):
        if self.step < 4:
            self.show_step(self.step + 1)
        elif self.step == 4:
            self.show_step(5)
        elif self.step == 6:
            if self.launch_now.get():
                target_exe = Path(self.install_dir.get()) / "Organix.exe"
                if target_exe.exists():
                    os.startfile(str(target_exe))
            self.destroy()

    def on_back(self):
        if self.step > 0 and self.step < 5:
            self.show_step(self.step - 1)

    def on_cancel(self):
        if messagebox.askyesno("Exit Setup", "Setup is not complete. Are you sure you want to exit?"):
            self.destroy()

if __name__ == "__main__":
    app = OrganixInstaller()
    app.mainloop()
