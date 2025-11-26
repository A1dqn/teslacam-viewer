# TeslaCam Viewer

A Python-based application for viewing and managing TeslaCam and Sentry Mode footage from Tesla vehicles.

## Features

- 📹 View TeslaCam recordings (front, left, right, and back cameras)
- 🎥 Play multiple camera angles simultaneously
- 📁 Browse and organize footage by date and event type
- 🔍 Search and filter recordings
- 💾 Export specific clips
- 🖥️ User-friendly GUI interface

## Requirements

- Python 3.8 or higher
- USB drive or storage device with TeslaCam footage

## Installation

1. Clone the repository:
```bash
git clone https://github.com/A1dqn/teslacam-viewer.git
cd teslacam-viewer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Connect your USB drive containing TeslaCam footage to your computer
2. Run the application:
```bash
python teslacam_viewer.py
```
3. Select the TeslaCam folder from your USB drive
4. Browse and play your recordings

## TeslaCam Folder Structure

The app expects the standard Tesla folder structure:
```
TeslaCam/
├── SavedClips/
├── SentryClips/
└── RecentClips/
```

## Features in Development

- [ ] Timeline scrubbing for precise navigation
- [ ] Event detection and tagging
- [ ] Cloud backup integration
- [ ] Video enhancement and stabilization
- [ ] Multi-language support

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Tesla for creating an amazing dashcam system
- The Tesla community for inspiration and feedback

## Support

If you encounter any issues or have suggestions, please open an issue on GitHub.