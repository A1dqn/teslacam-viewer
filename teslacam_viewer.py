#!/usr/bin/env python3
"""
TeslaCam Viewer - A GUI application for viewing Tesla dashcam footage
Author: Aidan
License: MIT
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import cv2
from PIL import Image, ImageTk
from datetime import datetime
import threading
import numpy as np


class TeslaCamViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("TeslaCam Viewer")
        self.root.geometry("1200x800")
        
        # Variables
        self.teslacam_path = None
        self.current_video = None
        self.video_captures = {}  # Dictionary to hold all 4 camera captures
        self.is_playing = False
        self.video_files = []
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the user interface"""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open TeslaCam Folder", command=self.open_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - File browser
        left_panel = ttk.Frame(main_container, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        
        ttk.Label(left_panel, text="TeslaCam Recordings", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Folder type filter
        filter_frame = ttk.Frame(left_panel)
        filter_frame.pack(fill=tk.X, pady=5)
        
        self.folder_type = tk.StringVar(value="All")
        ttk.Radiobutton(filter_frame, text="All", variable=self.folder_type, 
                       value="All", command=self.refresh_file_list).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="Saved", variable=self.folder_type, 
                       value="SavedClips", command=self.refresh_file_list).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="Sentry", variable=self.folder_type, 
                       value="SentryClips", command=self.refresh_file_list).pack(side=tk.LEFT)
        
        # File listbox with scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        scrollbar.config(command=self.file_listbox.yview)
        
        # Right panel - Video player
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Video display area
        self.video_frame = ttk.Label(right_panel, text="Select a video to play", 
                                     relief=tk.SUNKEN, background="black", 
                                     foreground="white", font=("Arial", 14))
        self.video_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Controls frame
        controls_frame = ttk.Frame(right_panel)
        controls_frame.pack(fill=tk.X)
        
        # Playback controls
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(pady=5)
        
        self.play_button = ttk.Button(button_frame, text="▶ Play", command=self.toggle_playback)
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="⏹ Stop", command=self.stop_video).pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(controls_frame, from_=0, to=100, 
                                      orient=tk.HORIZONTAL, variable=self.progress_var,
                                      command=self.seek_video)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # Time label
        self.time_label = ttk.Label(controls_frame, text="00:00 / 00:00")
        self.time_label.pack()
        
        # Status bar
        self.status_label = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
    def open_folder(self):
        """Open TeslaCam folder dialog"""
        folder = filedialog.askdirectory(title="Select TeslaCam Folder")
        if folder:
            self.teslacam_path = Path(folder)
            self.refresh_file_list()
            self.status_label.config(text=f"Loaded: {folder}")
    
    def parse_timestamp(self, filename):
        """Parse timestamp from TeslaCam filename"""
        try:
            # TeslaCam format: YYYY-MM-DD_HH-MM-SS-front.mp4
            # Extract base timestamp (before camera identifier)
            stem = filename.stem
            for camera in ['-front', '-left_repeater', '-right_repeater', '-back']:
                if camera in stem:
                    timestamp_str = stem.split(camera)[0]
                    break
            else:
                timestamp_str = stem
            
            # Replace last dashes with colons for time
            parts = timestamp_str.split('_')
            if len(parts) == 2:
                date_part = parts[0]
                time_part = parts[1].replace('-', ':')
                datetime_str = f"{date_part} {time_part}"
                return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        except:
            pass
        return None
    
    def get_camera_clips(self, front_video_path):
        """Get all camera clips for a given event"""
        # Extract the base timestamp from front camera file
        base_name = front_video_path.stem.replace('-front', '')
        parent_dir = front_video_path.parent
        
        cameras = {
            'front': parent_dir / f"{base_name}-front.mp4",
            'left': parent_dir / f"{base_name}-left_repeater.mp4",
            'right': parent_dir / f"{base_name}-right_repeater.mp4",
            'back': parent_dir / f"{base_name}-back.mp4"
        }
        
        # Return only existing files
        return {k: v for k, v in cameras.items() if v.exists()}
            
    def refresh_file_list(self):
        """Refresh the list of video files"""
        if not self.teslacam_path:
            return
            
        self.file_listbox.delete(0, tk.END)
        self.video_files = []
        
        folder_type = self.folder_type.get()
        
        # Collect all video files with metadata
        video_data = []
        
        # Search for video files
        if folder_type == "All":
            search_dirs = ["SavedClips", "SentryClips", "RecentClips"]
        else:
            search_dirs = [folder_type]
        
        for dir_name in search_dirs:
            dir_path = self.teslacam_path / dir_name
            if dir_path.exists():
                # Search in main folder
                for video_file in dir_path.glob("*-front.mp4"):
                    timestamp = self.parse_timestamp(video_file)
                    video_data.append((video_file, dir_name, timestamp))
                
                # Search in subdirectories (date folders)
                for subdir in dir_path.iterdir():
                    if subdir.is_dir():
                        for video_file in subdir.glob("*-front.mp4"):
                            timestamp = self.parse_timestamp(video_file)
                            video_data.append((video_file, dir_name, timestamp))
        
        # Sort by timestamp (newest first)
        video_data.sort(key=lambda x: x[2] if x[2] else datetime.min, reverse=True)
        
        # Populate listbox
        for video_file, dir_name, timestamp in video_data:
            if timestamp:
                # Format: [Type] MM/DD/YYYY HH:MM:SS
                display_name = f"[{dir_name[:6]}] {timestamp.strftime('%m/%d/%Y %I:%M:%S %p')}"
            else:
                # Fallback to filename
                display_name = f"[{dir_name[:6]}] {video_file.stem}"
            
            self.file_listbox.insert(tk.END, display_name)
            self.video_files.append(video_file)
        
        # Update status
        count = len(video_data)
        self.status_label.config(text=f"Found {count} clip(s) in {folder_type}")
                    
    def on_file_select(self, event):
        """Handle file selection from listbox"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            video_path = self.video_files[index]
            self.load_merged_video(video_path)
            
    def load_merged_video(self, front_video_path):
        """Load all camera angles for merged playback"""
        # Release any existing captures
        for cap in self.video_captures.values():
            cap.release()
        self.video_captures.clear()
        
        # Get all camera clips
        camera_clips = self.get_camera_clips(front_video_path)
        
        # Load all available cameras
        for camera, path in camera_clips.items():
            cap = cv2.VideoCapture(str(path))
            if cap.isOpened():
                self.video_captures[camera] = cap
        
        if self.video_captures:
            self.current_video = front_video_path
            camera_count = len(self.video_captures)
            self.status_label.config(text=f"Loaded: {front_video_path.stem} ({camera_count} cameras)")
            self.is_playing = False
            self.play_button.config(text="▶ Play")
            self.show_merged_frame()
        else:
            messagebox.showerror("Error", f"Could not open any video files")
            
    def show_merged_frame(self):
        """Display merged frame from all cameras in a grid"""
        if not self.video_captures:
            return
        
        frames = {}
        
        # Read frames from all cameras
        for camera, cap in self.video_captures.items():
            ret, frame = cap.read()
            if ret:
                frames[camera] = frame
        
        if not frames:
            return
        
        # Resize each frame to consistent size
        frame_width, frame_height = 480, 270  # Half of 960x540
        
        # Create placeholders for missing cameras
        camera_order = ['front', 'back', 'left', 'right']
        resized_frames = []
        labels = []
        
        for camera in camera_order:
            if camera in frames:
                frame = cv2.resize(frames[camera], (frame_width, frame_height))
                resized_frames.append(frame)
                labels.append(camera.upper())
            else:
                # Create black placeholder
                black_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
                resized_frames.append(black_frame)
                labels.append(f"{camera.upper()} (N/A)")
        
        # Add text labels to each frame
        for i, (frame, label) in enumerate(zip(resized_frames, labels)):
            cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.8, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Create 2x2 grid: [Front, Back]
        #                   [Left,  Right]
        top_row = np.hstack([resized_frames[0], resized_frames[1]])  # Front, Back
        bottom_row = np.hstack([resized_frames[2], resized_frames[3]])  # Left, Right
        merged_frame = np.vstack([top_row, bottom_row])
        
        # Convert to PhotoImage
        merged_frame = cv2.cvtColor(merged_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(merged_frame)
        imgtk = ImageTk.PhotoImage(image=img)
        
        self.video_frame.imgtk = imgtk
        self.video_frame.configure(image=imgtk)
        
        # Update progress bar (use front camera as reference)
        if 'front' in self.video_captures:
            cap = self.video_captures['front']
            current_pos = cap.get(cv2.CAP_PROP_POS_FRAMES)
            total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            if total_frames > 0:
                progress = (current_pos / total_frames) * 100
                self.progress_var.set(progress)
                
                # Update time label
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps > 0:
                    current_time = int(current_pos / fps)
                    total_time = int(total_frames / fps)
                    self.time_label.config(text=f"{current_time//60:02d}:{current_time%60:02d} / {total_time//60:02d}:{total_time%60:02d}")
                    
    def toggle_playback(self):
        """Toggle play/pause"""
        if not self.video_captures:
            messagebox.showwarning("No Video", "Please select a video first")
            return
            
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_button.config(text="⏸ Pause")
            self.play_video()
        else:
            self.play_button.config(text="▶ Play")
            
    def play_video(self):
        """Play merged video in a loop"""
        if self.is_playing and self.video_captures:
            # Check if any camera still has frames
            has_frames = False
            for cap in self.video_captures.values():
                if cap.get(cv2.CAP_PROP_POS_FRAMES) < cap.get(cv2.CAP_PROP_FRAME_COUNT):
                    has_frames = True
                    break
            
            if has_frames:
                self.show_merged_frame()
                self.root.after(33, self.play_video)  # ~30 FPS
            else:
                # End of video
                self.is_playing = False
                self.play_button.config(text="▶ Play")
                # Reset all captures to beginning
                for cap in self.video_captures.values():
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
    def stop_video(self):
        """Stop video playback"""
        self.is_playing = False
        self.play_button.config(text="▶ Play")
        for cap in self.video_captures.values():
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.show_merged_frame()
            
    def seek_video(self, value):
        """Seek to position in video"""
        if self.video_captures:
            # Use front camera as reference for seeking
            if 'front' in self.video_captures:
                cap = self.video_captures['front']
                total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                frame_number = int((float(value) / 100) * total_frames)
                
                # Seek all cameras to same position
                for camera_cap in self.video_captures.values():
                    camera_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                
                if not self.is_playing:
                    self.show_merged_frame()
                
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", 
                          "TeslaCam Viewer v2.0\n\n"
                          "A Python application for viewing Tesla dashcam footage.\n\n"
                          "Features:\n"
                          "- 4-camera merged view\n"
                          "- Synchronized playback\n\n"
                          "Created by Aidan\n"
                          "GitHub: github.com/A1dqn/teslacam-viewer")
        
    def __del__(self):
        """Cleanup on exit"""
        for cap in self.video_captures.values():
            cap.release()


def main():
    """Main application entry point"""
    root = tk.Tk()
    app = TeslaCamViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()