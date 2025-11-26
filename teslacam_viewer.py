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


class TeslaCamViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("TeslaCam Viewer")
        self.root.geometry("1200x800")
        
        # Variables
        self.teslacam_path = None
        self.current_video = None
        self.video_capture = None
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
            
    def refresh_file_list(self):
        """Refresh the list of video files"""
        if not self.teslacam_path:
            return
            
        self.file_listbox.delete(0, tk.END)
        self.video_files = []
        
        folder_type = self.folder_type.get()
        
        # Search for video files
        if folder_type == "All":
            search_dirs = ["SavedClips", "SentryClips", "RecentClips"]
        else:
            search_dirs = [folder_type]
            
        for dir_name in search_dirs:
            dir_path = self.teslacam_path / dir_name
            if dir_path.exists():
                for video_file in sorted(dir_path.glob("*-front.mp4")):
                    # Extract timestamp from filename
                    timestamp = video_file.stem.split("-front")[0]
                    display_name = f"[{dir_name}] {timestamp}"
                    self.file_listbox.insert(tk.END, display_name)
                    self.video_files.append(video_file)
                    
    def on_file_select(self, event):
        """Handle file selection from listbox"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            video_path = self.video_files[index]
            self.load_video(video_path)
            
    def load_video(self, video_path):
        """Load a video file"""
        if self.video_capture:
            self.video_capture.release()
            
        self.current_video = video_path
        self.video_capture = cv2.VideoCapture(str(video_path))
        
        if self.video_capture.isOpened():
            self.status_label.config(text=f"Loaded: {video_path.name}")
            self.is_playing = False
            self.play_button.config(text="▶ Play")
            self.show_frame()
        else:
            messagebox.showerror("Error", f"Could not open video: {video_path.name}")
            
    def show_frame(self):
        """Display current video frame"""
        if self.video_capture and self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
            if ret:
                # Convert frame to PhotoImage
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (960, 540))  # Resize for display
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                
                self.video_frame.imgtk = imgtk
                self.video_frame.configure(image=imgtk)
                
                # Update progress
                current_pos = self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)
                total_frames = self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT)
                if total_frames > 0:
                    progress = (current_pos / total_frames) * 100
                    self.progress_var.set(progress)
                    
    def toggle_playback(self):
        """Toggle play/pause"""
        if not self.video_capture:
            messagebox.showwarning("No Video", "Please select a video first")
            return
            
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_button.config(text="⏸ Pause")
            self.play_video()
        else:
            self.play_button.config(text="▶ Play")
            
    def play_video(self):
        """Play video in a loop"""
        if self.is_playing and self.video_capture and self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
            if ret:
                self.show_frame()
                self.root.after(30, self.play_video)  # ~30 FPS
            else:
                # End of video
                self.is_playing = False
                self.play_button.config(text="▶ Play")
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
    def stop_video(self):
        """Stop video playback"""
        self.is_playing = False
        self.play_button.config(text="▶ Play")
        if self.video_capture:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.show_frame()
            
    def seek_video(self, value):
        """Seek to position in video"""
        if self.video_capture and self.video_capture.isOpened():
            total_frames = self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT)
            frame_number = int((float(value) / 100) * total_frames)
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            if not self.is_playing:
                self.show_frame()
                
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", 
                          "TeslaCam Viewer v1.0\n\n"
                          "A Python application for viewing Tesla dashcam footage.\n\n"
                          "Created by Aidan\n"
                          "GitHub: github.com/A1dqn/teslacam-viewer")
        
    def __del__(self):
        """Cleanup on exit"""
        if self.video_capture:
            self.video_capture.release()


def main():
    """Main application entry point"""
    root = tk.Tk()
    app = TeslaCamViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()