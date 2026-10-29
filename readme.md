# 🐜 Organix Pro — Smart Multi-Location File Organizer

<p align="center">
  <img src="web/app_icon.png" width="100" height="100" alt="Organix Ant Logo" />
  <br />
  <b>High-Performance File Organization & Drive Cleaning Hub for Windows</b>
  <br />
  <sub>Zero Data Loss Guarantee • Multi-Location Hub • 1-Click Clean • Auto-Update Supported</sub>
</p>

---

## 🌟 Overview

**Organix** is an intelligent, high-speed desktop and multi-location file organizer for Windows. It provides a central command hub to monitor, assort, and organize loose files across:
* **Desktop** (`Desktop/Sorted Files/`)
* **Downloads** (`Downloads/Downloads Assorted/`)
* **Documents** (`Documents/Documents Assorted/`)
* **System & Removable Drives** (`C:\C_Drive_Assorted`, `E:\E_Drive_Assorted`, etc.)

---

## ⚡ Key Features

1. **Multi-Location Hub (Page 1)**:
   - High-density compact dashboard displaying all monitored locations and storage drives.
   - Real-time disk capacity meters and unorganized file counters.
   - **1-Click Clean** action button directly on each card for instant auto-assortment.

2. **Ultra-Clean Location Studio (Page 2)**:
   - Minimalist single-line header with **Hub** navigation, Organix branding, and location selector.
   - Smart, cool, minimal mode tabs:
     - `Files`: Loose files inspection, bulk selection, and categorization.
     - `1-Click Clean`: Live category routing matrix with auto-assort engine.
     - `Subfolders`: Inspect and organize folders with "stay as it" safety.
     - `Assorted`: Browse organized files by category in one place.

3. **100% Zero Data Loss Guarantee**:
   - Files are moved safely into categorized folders; **never deleted**.
   - Automatic collision prevention (appends `(1)` if a duplicate exists).
   - Reversible in 1-click via the `Undo` button.

4. **Auto-Update System**:
   - Integrated with **GitHub Releases** (`mashadcloud-art/Organix`).
   - One-click update check and automated version tracking.

5. **Native Windows Setup Wizard**:
   - Packaged as a standard Windows Setup Wizard (`Organix_Setup.exe`) with a clean Next ➔ Next ➔ Install ➔ Finish flow.
   - Zero CMD or console window popups.

---

## 🚀 Installation & Running

### Option 1: Run the Setup Wizard
Download and run **`Organix_Setup.exe`** from the [Latest Release](https://github.com/mashadcloud-art/Organix/releases/latest).

### Option 2: Run from Source
```powershell
# Clone the repository
git clone https://github.com/mashadcloud-art/Organix.git
cd Organix

# Install Python dependencies
pip install psutil pypiwin32

# Run the app
python file_organizer.py
```

### Option 3: Build Standalone Executables
```powershell
# Build standalone Organix.exe
.\build_exe.bat

# Build setup wizard Organix_Setup.exe
python -m PyInstaller --noconsole --onefile --name "Organix_Setup" --icon "app_icon.ico" --add-data "dist\Organix.exe;." --add-data "app_icon.ico;." installer_wizard.py
```

---

## 📁 Default Assortment Tree
```
Sorted Files/
├── Images/       (.jpg, .png, .gif, .webp, .svg...)
├── Videos/       (.mp4, .mkv, .mov, .avi...)
├── Documents/    (.docx, .txt, .rtf, .xlsx, .pptx...)
├── PDF/          (.pdf)
├── Audio/        (.mp3, .wav, .flac, .aac...)
├── Archives/     (.zip, .rar, .7z, .tar...)
├── Installers/   (.exe, .msi, .apk...)
├── Code/         (.py, .js, .html, .css, .json...)
└── Other/
```

---

## 📄 License
Organix is distributed for personal and commercial file organization under the MIT License.
