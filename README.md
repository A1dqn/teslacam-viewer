# TeslaCam Viewer

A modern Python application for viewing and managing TeslaCam and Sentry Mode footage from Tesla vehicles with synchronized 4-camera playback.

## ✨ Features

### Video Playback
- 🎥 **4-Camera Synchronized Playback** - View all camera angles (front, back, left, right) simultaneously in a grid layout
- 🔗 **Automatic Clip Stitching** - Seamlessly merges 1-minute clips into complete events
- ⚡ **Variable Playback Speed** - Control playback from 0.5x to 3x speed
- 🎬 **Normalized Speed** - Consistent playback feel regardless of source framerate
- 📊 **Progress Bar** - Visual timeline with seek capability

### Organization & Discovery
- 🔍 **Auto-Detect TeslaCam Folder** - Automatically finds your USB drive on startup
- 📁 **Smart Event Grouping** - Groups clips within 15 minutes into single events
- 🔎 **Search & Filter** - Search by date, time, or event type
- 📋 **Event Timeline** - Browse all events with detailed information
- 🏷️ **Event Types** - Separate views for Saved, Sentry, and Recent clips

### Modern Interface
- 🎨 **Dark Theme UI** - Modern, sleek interface designed for extended viewing
- 📱 **Intuitive Controls** - Clean, easy-to-use playback controls
- ⌨️ **Keyboard Shortcuts** - Quick access to common functions
- 📈 **Event Details** - Shows timestamp, duration, camera count, and FPS

## 📋 Requirements

- Python 3.8 or higher
- USB drive or storage device with TeslaCam footage
- Operating System: Windows, macOS, or Linux

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/A1dqn/teslacam-viewer.git
cd teslacam-viewer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## 📖 Usage

1. **Connect Your USB Drive** containing TeslaCam footage to your computer

2. **Launch the Application**:
```bash
python teslacam_viewer.py
```

3. **Automatic Detection** - The app will automatically search for and load your TeslaCam folder
   - If not found, click "Open TeslaCam Folder" to select manually

4. **Browse Events** - Use the event list on the left to browse recordings
   - Filter by type: All Events, Saved, Sentry, or Recent
   - Search by date or time

5. **Play Videos**:
   - Click an event to load it
   - Press **Space** or click **Play** to start playback
   - Use speed buttons (0.5x - 3x) to adjust playback speed
   - Drag the progress bar to seek

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open TeslaCam folder |
| `Space` | Play/Pause video |
| `Ctrl+Q` | Quit application |

## 📂 TeslaCam Folder Structure

The app expects the standard Tesla folder structure:
```
TeslaCam/
├── SavedClips/
│   └── YYYY-MM-DD_HH-MM-SS-camera.mp4
├── SentryClips/
│   └── YYYY-MM-DD_HH-MM-SS/
│       └── YYYY-MM-DD_HH-MM-SS-camera.mp4
└── RecentClips/
    └── YYYY-MM-DD_HH-MM-SS-camera.mp4
```

Each event includes files for up to 4 cameras:
- `*-front.mp4` - Front camera
- `*-back.mp4` - Rear camera
- `*-left_repeater.mp4` - Left side camera
- `*-right_repeater.mp4` - Right side camera

## 🎯 Key Features Explained

### Automatic Clip Stitching
TeslaCam records in 1-minute segments. The viewer automatically:
- Detects sequential clips in the same recording session
- Merges them into a single playable event
- Provides seamless playback across clip boundaries

### Multi-Camera Synchronization
- All 4 camera angles are synchronized and displayed in a 2x2 grid
- Cameras are labeled (FRONT, BACK, LEFT, RIGHT)
- Missing cameras show a black placeholder

### Smart Event Detection
- Events are grouped when clips are within 15 minutes of each other
- Each event shows the start time and total duration
- Events are sorted by date (newest first)

## 🔧 Technical Details

### Dependencies
- **opencv-python** (cv2) - Video processing and playback
- **Pillow** (PIL) - Image handling
- **tkinter** - GUI framework (included with Python)
- **numpy** - Array operations for video frames

### Performance
- Time-based playback ensures smooth video at any speed
- Optimized frame display (1ms update loop)
- Efficient memory management with multi-clip handling

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Tesla for creating an amazing dashcam system
- The Tesla community for inspiration and feedback
- Contributors and users who help improve this project

## 💬 Support

If you encounter any issues or have suggestions:
- Open an issue on [GitHub Issues](https://github.com/A1dqn/teslacam-viewer/issues)
- Provide details about your system and the problem
- Include any error messages or screenshots

## 🗺️ Roadmap

- [ ] Video export functionality
- [ ] Event tagging and notes
- [ ] GPS data overlay (if available)
- [ ] Cloud backup integration
- [ ] Video enhancement filters
- [ ] Multi-language support

---

**Made with ❤️ for Tesla owners**