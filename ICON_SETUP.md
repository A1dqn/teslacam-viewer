# Icon Setup for TeslaCam Viewer

The TeslaCam Viewer supports custom window icons on Windows, macOS, and Linux.

## Quick Setup

1. **Get an Icon File**:
   - Download a `.ico` file (Windows icon format)
   - Or create your own using an online converter

2. **Place the Icon**:
   - Save the icon file as `icon.ico` in the same directory as `teslacam_viewer.py`
   - The app will automatically detect and use it

## Creating Your Own Icon

### Option 1: Online Converter
1. Find or create a PNG/JPG image (256x256 or larger recommended)
2. Visit an online converter like:
   - [ConvertICO.com](https://convertico.com/)
   - [ICOConvert.com](https://icoconvert.com/)
3. Upload your image and download the `.ico` file
4. Save as `icon.ico` in the app directory

### Option 2: Using Python (PIL/Pillow)
```python
from PIL import Image

# Load your image
img = Image.open('your_image.png')

# Resize to multiple sizes for better quality
img.save('icon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
```

### Option 3: Download Tesla-themed Icons
Search for "Tesla icon" or "dashcam icon" on icon websites:
- [Flaticon.com](https://www.flaticon.com/)
- [Icons8.com](https://icons8.com/)
- [IconArchive.com](https://iconarchive.com/)

## Recommended Icon Theme

For a TeslaCam viewer, consider:
- 📹 Camera icon
- 🚗 Tesla logo or car silhouette
- 🎥 Video camera icon
- 📱 Dashboard camera icon

## File Location

```
teslacam-viewer/
├── teslacam_viewer.py
├── icon.ico          ← Place your icon here
├── requirements.txt
└── README.md
```

## Troubleshooting

**Icon not showing?**
- Make sure the file is named exactly `icon.ico` (lowercase)
- Verify it's in the same directory as `teslacam_viewer.py`
- Try restarting the application
- On some systems, the taskbar icon may take a moment to update

**Wrong format?**
- The file must be in `.ico` format (not `.png` or `.jpg`)
- Use a converter tool to convert your image to `.ico`

## No Icon?

The app works perfectly fine without an icon file. If no `icon.ico` is found, the application will simply use the default system icon.

---

**Note**: Icon files are not included in the repository to keep it lightweight. Users can customize with their preferred icon.