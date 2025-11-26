# Building TeslaCam Viewer as an Executable (.exe)

This guide will help you create a standalone Windows executable that you can run without Python or PyCharm installed.

## Method 1: Using PyInstaller (Recommended)

### Step 1: Install PyInstaller

In PyCharm's terminal (bottom panel), run:

```bash
pip install pyinstaller
```

### Step 2: Build the Executable

Run this command in the terminal (make sure you're in the project directory):

```bash
pyinstaller --onefile --windowed --icon=icon.ico --name="TeslaCam Viewer" teslacam_viewer.py
```

#### What each option does:
- `--onefile` - Creates a single .exe file (easier to distribute)
- `--windowed` - Hides the console window (no black terminal)
- `--icon=icon.ico` - Uses your custom icon
- `--name="TeslaCam Viewer"` - Sets the exe name

### Step 3: Find Your EXE

After building (takes 1-2 minutes), find your executable at:
```
teslacam-viewer/dist/TeslaCam Viewer.exe
```

### Step 4: Test It!

1. Go to the `dist` folder
2. Double-click `TeslaCam Viewer.exe`
3. It should launch without needing Python!

## Method 2: Optimized Build (Smaller File Size)

For a smaller exe with external data files:

```bash
pyinstaller --windowed --icon=icon.ico --name="TeslaCam Viewer" --add-data "icon.ico;." teslacam_viewer.py
```

This creates a folder with the exe and supporting files.

## Distribution

### Option A: Single File (Easiest)
Just share the `TeslaCam Viewer.exe` from the `dist` folder. Anyone can run it without installing anything!

### Option B: Installer
Use **Inno Setup** to create a professional installer:
1. Download Inno Setup: https://jrsoftware.org/isinfo.php
2. Create a simple script to install your app
3. Package it as `TeslaCam_Viewer_Setup.exe`

## Troubleshooting

### "ModuleNotFoundError" when running exe
**Fix:** Add missing modules explicitly:
```bash
pyinstaller --onefile --windowed --icon=icon.ico --hidden-import=cv2 --hidden-import=PIL --name="TeslaCam Viewer" teslacam_viewer.py
```

### Exe is too large (>100MB)
**Fix:** Use the multi-file version (Method 2) or use UPX compression:
```bash
pip install pyinstaller[compression]
pyinstaller --onefile --windowed --upx-dir=/path/to/upx --icon=icon.ico --name="TeslaCam Viewer" teslacam_viewer.py
```

### Antivirus flags the exe
**Normal behavior!** PyInstaller exes are sometimes flagged as false positives. You can:
- Add an exception in your antivirus
- Code-sign the executable (requires certificate)
- Use multi-file distribution (less likely to be flagged)

### Icon doesn't show
**Fix:** Make sure `icon.ico` is in the same folder as `teslacam_viewer.py` when building.

## Quick Build Script

Create a file called `build.bat` in your project folder:

```batch
@echo off
echo Building TeslaCam Viewer...
pyinstaller --onefile --windowed --icon=icon.ico --name="TeslaCam Viewer" teslacam_viewer.py
echo Done! Check the dist folder.
pause
```

Just double-click `build.bat` to build!

## File Size Comparison

- **Single file exe**: ~80-150 MB (includes Python interpreter)
- **Multi-file**: ~50-80 MB total (smaller main exe)
- **With UPX compression**: ~40-60 MB

## Notes

- The first launch of the exe may be slower (unpacking files)
- Windows Defender might scan it the first time
- You only need to build once - the exe works on any Windows PC!
- To update: Just rebuild with the new code

## Sharing Your App

1. **Zip the exe**: Right-click `TeslaCam Viewer.exe` → Send to → Compressed folder
2. **Upload**: Share via Google Drive, Dropbox, or GitHub Releases
3. **Instructions**: Tell users to:
   - Download and extract
   - Right-click → Properties → Unblock (if needed)
   - Double-click to run!

That's it! Your Python app is now a distributable Windows application. 🎉
