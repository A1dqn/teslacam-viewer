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
from datetime import datetime, timedelta
import threading
import numpy as np


class MultiVideoCapture:
    """Handles playback across multiple sequential video clips"""
    def __init__(self, video_paths):
        self.video_paths = video_paths
        self.current_clip_index = 0
        self.current_capture = None
        self.total_frames = 0
        self.frame_offsets = []  # Starting frame number for each clip
        
        # Calculate total frames and offsets
        current_offset = 0
        for path in video_paths:
            self.frame_offsets.append(current_offset)
            cap = cv2.VideoCapture(str(path))
            if cap.isOpened():
                frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.total_frames += frames
                cap.release()
            current_offset = self.total_frames
        
        # Open first clip
        if self.video_paths:
            self.current_capture = cv2.VideoCapture(str(self.video_paths[0]))
    
    def isOpened(self):
        return self.current_capture is not None and self.current_capture.isOpened()
    
    def read(self):
        """Read next frame, automatically transitioning between clips"""
        if not self.current_capture or not self.current_capture.isOpened():
            return False, None
        
        ret, frame = self.current_capture.read()
        
        # If current clip ended, move to next clip
        if not ret and self.current_clip_index < len(self.video_paths) - 1:
            self.current_capture.release()
            self.current_clip_index += 1
            self.current_capture = cv2.VideoCapture(str(self.video_paths[self.current_clip_index]))
            ret, frame = self.current_capture.read()
        
        return ret, frame
    
    def get(self, prop):
        """Get video property"""
        if prop == cv2.CAP_PROP_FRAME_COUNT:
            return self.total_frames
        elif prop == cv2.CAP_PROP_POS_FRAMES:
            # Current position = offset of current clip + position within clip
            if self.current_capture and self.current_capture.isOpened():
                clip_pos = self.current_capture.get(cv2.CAP_PROP_POS_FRAMES)
                return self.frame_offsets[self.current_clip_index] + clip_pos
            return 0
        elif self.current_capture:
            return self.current_capture.get(prop)
        return 0
    
    def set(self, prop, value):
        """Set video property (mainly for seeking)"""
        if prop == cv2.CAP_PROP_POS_FRAMES:
            # Find which clip this frame belongs to
            target_frame = int(value)
            
            for i, offset in enumerate(self.frame_offsets):
                if i == len(self.frame_offsets) - 1 or target_frame < self.frame_offsets[i + 1]:
                    # This is the correct clip
                    if i != self.current_clip_index:
                        # Switch to this clip
                        if self.current_capture:
                            self.current_capture.release()
                        self.current_clip_index = i
                        self.current_capture = cv2.VideoCapture(str(self.video_paths[i]))
                    
                    # Seek within the clip
                    if self.current_capture and self.current_capture.isOpened():
                        local_frame = target_frame - offset
                        self.current_capture.set(cv2.CAP_PROP_POS_FRAMES, local_frame)
                    break
        elif self.current_capture:
            self.current_capture.set(prop, value)
    
    def release(self):
        """Release all resources"""
        if self.current_capture:
            self.current_capture.release()
            self.current_capture = None


class TeslaCamViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("TeslaCam Viewer")
        self.root.geometry("1400x900")
        
        # Variables
        self.teslacam_path = None
        self.current_video = None
        self.video_captures = {}  # Dictionary to hold all 4 camera captures
        self.is_playing = False
        self.video_files = []
        self.all_events = []
        
        # Configure style
        self.setup_style()
        
        # Setup UI
        self.setup_ui()
        
    def setup_style(self):
        """Configure modern styling"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colors
        bg_color = '#1e1e1e'
        fg_color = '#ffffff'
        accent_color = '#007acc'
        hover_color = '#005a9e'
        
        # Configure Treeview
        style.configure('Treeview',
                       background='#2d2d2d',
                       foreground=fg_color,
                       fieldbackground='#2d2d2d',
                       borderwidth=0,
                       font=('Segoe UI', 10))
        style.map('Treeview', background=[('selected', accent_color)])
        
        # Configure Treeview headings
        style.configure('Treeview.Heading',
                       background='#3c3c3c',
                       foreground=fg_color,
                       borderwidth=0,
                       font=('Segoe UI', 10, 'bold'))
        style.map('Treeview.Heading', background=[('active', hover_color)])
        
    def setup_ui(self):
        """Initialize the user interface"""
        # Configure root window
        self.root.configure(bg='#1e1e1e')
        
        # Menu bar
        menubar = tk.Menu(self.root, bg='#2d2d2d', fg='#ffffff')
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0, bg='#2d2d2d', fg='#ffffff')
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open TeslaCam Folder...", command=self.open_folder, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        help_menu = tk.Menu(menubar, tearoff=0, bg='#2d2d2d', fg='#ffffff')
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.open_folder())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<space>', lambda e: self.toggle_playback())
        
        # Top toolbar
        toolbar = tk.Frame(self.root, bg='#2d2d2d', height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0)
        
        # Open folder button
        open_btn = tk.Button(toolbar, text="📁 Open TeslaCam Folder", 
                            command=self.open_folder,
                            bg='#007acc', fg='#ffffff', 
                            font=('Segoe UI', 11, 'bold'),
                            relief=tk.FLAT, padx=20, pady=10,
                            cursor='hand2')
        open_btn.pack(side=tk.LEFT, padx=15, pady=10)
        
        # Folder path label
        self.folder_label = tk.Label(toolbar, text="No folder selected", 
                                    bg='#2d2d2d', fg='#888888',
                                    font=('Segoe UI', 10))
        self.folder_label.pack(side=tk.LEFT, padx=10)
        
        # Main container
        main_container = tk.Frame(self.root, bg='#1e1e1e')
        main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Left panel - Event browser
        left_panel = tk.Frame(main_container, bg='#252525', width=500)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=0, pady=0)
        
        # Search and filter section
        filter_container = tk.Frame(left_panel, bg='#252525')
        filter_container.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(filter_container, text="Filter Events", 
                bg='#252525', fg='#ffffff',
                font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Filter buttons
        filter_frame = tk.Frame(filter_container, bg='#252525')
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.folder_type = tk.StringVar(value="All")
        
        filter_options = [
            ("All Events", "All"),
            ("💾 Saved", "SavedClips"),
            ("🛡️ Sentry", "SentryClips"),
            ("🕐 Recent", "RecentClips")
        ]
        
        for text, value in filter_options:
            btn = tk.Radiobutton(filter_frame, text=text, variable=self.folder_type,
                                value=value, command=self.refresh_file_list,
                                bg='#252525', fg='#ffffff', 
                                selectcolor='#007acc',
                                font=('Segoe UI', 10),
                                activebackground='#252525',
                                activeforeground='#ffffff',
                                cursor='hand2')
            btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # Search box
        search_frame = tk.Frame(filter_container, bg='#252525')
        search_frame.pack(fill=tk.X)
        
        tk.Label(search_frame, text="Search:", bg='#252525', fg='#ffffff',
                font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_events())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               bg='#3c3c3c', fg='#ffffff',
                               font=('Segoe UI', 10),
                               insertbackground='#ffffff',
                               relief=tk.FLAT)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        
        # Event list with Treeview
        list_container = tk.Frame(left_panel, bg='#252525')
        list_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Column headers
        columns = ('date', 'time', 'duration', 'type')
        self.event_tree = ttk.Treeview(list_container, columns=columns, 
                                       show='tree headings', selectmode='browse')
        
        # Define columns
        self.event_tree.heading('#0', text='Event')
        self.event_tree.heading('date', text='Date')
        self.event_tree.heading('time', text='Time')
        self.event_tree.heading('duration', text='Duration')
        self.event_tree.heading('type', text='Type')
        
        self.event_tree.column('#0', width=50, minwidth=50)
        self.event_tree.column('date', width=100, minwidth=80)
        self.event_tree.column('time', width=100, minwidth=80)
        self.event_tree.column('duration', width=80, minwidth=60)
        self.event_tree.column('type', width=80, minwidth=60)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=self.event_tree.yview)
        self.event_tree.configure(yscrollcommand=scrollbar.set)
        
        self.event_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.event_tree.bind('<<TreeviewSelect>>', self.on_event_select)
        
        # Right panel - Video player
        right_panel = tk.Frame(main_container, bg='#1e1e1e')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Video info section
        info_frame = tk.Frame(right_panel, bg='#1e1e1e')
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.video_title = tk.Label(info_frame, text="No event selected",
                                    bg='#1e1e1e', fg='#ffffff',
                                    font=('Segoe UI', 14, 'bold'),
                                    anchor='w')
        self.video_title.pack(side=tk.LEFT)
        
        self.video_info = tk.Label(info_frame, text="",
                                   bg='#1e1e1e', fg='#888888',
                                   font=('Segoe UI', 10),
                                   anchor='w')
        self.video_info.pack(side=tk.LEFT, padx=(15, 0))
        
        # Video display area
        video_container = tk.Frame(right_panel, bg='#000000', relief=tk.SUNKEN, bd=2)
        video_container.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.video_frame = tk.Label(video_container, text="Select an event to play", 
                                    background="#000000", 
                                    foreground="#666666", 
                                    font=("Segoe UI", 16))
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        
        # Controls frame
        controls_frame = tk.Frame(right_panel, bg='#2d2d2d')
        controls_frame.pack(fill=tk.X)
        
        # Playback controls
        button_frame = tk.Frame(controls_frame, bg='#2d2d2d')
        button_frame.pack(pady=15)
        
        self.play_button = tk.Button(button_frame, text="▶ Play", 
                                     command=self.toggle_playback,
                                     bg='#007acc', fg='#ffffff',
                                     font=('Segoe UI', 11, 'bold'),
                                     relief=tk.FLAT, padx=20, pady=8,
                                     cursor='hand2')
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        stop_btn = tk.Button(button_frame, text="⏹ Stop", 
                            command=self.stop_video,
                            bg='#3c3c3c', fg='#ffffff',
                            font=('Segoe UI', 11),
                            relief=tk.FLAT, padx=20, pady=8,
                            cursor='hand2')
        stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        progress_frame = tk.Frame(controls_frame, bg='#2d2d2d')
        progress_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(progress_frame, from_=0, to=100, 
                                      orient=tk.HORIZONTAL, variable=self.progress_var,
                                      command=self.seek_video)
        self.progress_bar.pack(fill=tk.X)
        
        # Time label
        self.time_label = tk.Label(controls_frame, text="00:00 / 00:00",
                                   bg='#2d2d2d', fg='#ffffff',
                                   font=('Segoe UI', 10))
        self.time_label.pack(pady=(0, 10))
        
        # Status bar
        self.status_label = tk.Label(self.root, text="Ready - Open a TeslaCam folder to begin", 
                                    relief=tk.FLAT, bg='#2d2d2d', fg='#888888',
                                    font=('Segoe UI', 9), anchor='w', padx=15)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
    def open_folder(self):
        """Open TeslaCam folder dialog"""
        folder = filedialog.askdirectory(title="Select TeslaCam Folder")
        if folder:
            self.teslacam_path = Path(folder)
            self.folder_label.config(text=str(folder), fg='#ffffff')
            self.refresh_file_list()
    
    def parse_timestamp(self, filename):
        """Parse timestamp from TeslaCam filename"""
        try:
            # TeslaCam format: YYYY-MM-DD_HH-MM-SS-front.mp4
            stem = filename.stem
            for camera in ['-front', '-left_repeater', '-right_repeater', '-back']:
                if camera in stem:
                    timestamp_str = stem.split(camera)[0]
                    break
            else:
                timestamp_str = stem
            
            parts = timestamp_str.split('_')
            if len(parts) == 2:
                date_part = parts[0]
                time_part = parts[1].replace('-', ':')
                datetime_str = f"{date_part} {time_part}"
                return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        except:
            pass
        return None
    
    def get_sequential_clips(self, base_video_path, camera_type):
        """Get all sequential 1-minute clips for a camera to form complete event"""
        parent_dir = base_video_path.parent
        base_timestamp = self.parse_timestamp(base_video_path)
        
        if not base_timestamp:
            return [base_video_path]
        
        sequential_clips = []
        checked_times = set()
        
        # Look backwards for earlier clips (up to 60 minutes)
        current_time = base_timestamp
        for _ in range(60):  # Check up to 60 minutes back
            prev_time = current_time - timedelta(minutes=1)
            if prev_time in checked_times:
                break
            checked_times.add(prev_time)
            
            prev_filename = f"{prev_time.strftime('%Y-%m-%d_%H-%M-%S')}-{camera_type}.mp4"
            prev_path = parent_dir / prev_filename
            
            if prev_path.exists():
                sequential_clips.insert(0, prev_path)
                current_time = prev_time
            else:
                break
        
        # Add the base clip
        sequential_clips.append(base_video_path)
        checked_times.add(base_timestamp)
        
        # Look forward for later clips (up to 60 minutes)
        current_time = base_timestamp
        for _ in range(60):  # Check up to 60 minutes forward
            next_time = current_time + timedelta(minutes=1)
            if next_time in checked_times:
                break
            checked_times.add(next_time)
            
            next_filename = f"{next_time.strftime('%Y-%m-%d_%H-%M-%S')}-{camera_type}.mp4"
            next_path = parent_dir / next_filename
            
            if next_path.exists():
                sequential_clips.append(next_path)
                current_time = next_time
            else:
                break
        
        return sequential_clips
    
    def get_camera_clips(self, front_video_path):
        """Get all camera clips for a given event"""
        base_name = front_video_path.stem.replace('-front', '')
        parent_dir = front_video_path.parent
        
        cameras = {
            'front': parent_dir / f"{base_name}-front.mp4",
            'left': parent_dir / f"{base_name}-left_repeater.mp4",
            'right': parent_dir / f"{base_name}-right_repeater.mp4",
            'back': parent_dir / f"{base_name}-back.mp4"
        }
        
        return {k: v for k, v in cameras.items() if v.exists()}
            
    def refresh_file_list(self):
        """Refresh the list of video files"""
        if not self.teslacam_path:
            return
        
        self.status_label.config(text="Loading events...")
        self.root.update()
            
        for item in self.event_tree.get_children():
            self.event_tree.delete(item)
        
        self.video_files = []
        self.all_events = []
        
        folder_type = self.folder_type.get()
        
        video_data = []
        
        if folder_type == "All":
            search_dirs = ["SavedClips", "SentryClips", "RecentClips"]
        else:
            search_dirs = [folder_type]
        
        for dir_name in search_dirs:
            dir_path = self.teslacam_path / dir_name
            if dir_path.exists():
                for video_file in dir_path.glob("*-front.mp4"):
                    timestamp = self.parse_timestamp(video_file)
                    video_data.append((video_file, dir_name, timestamp))
                
                for subdir in dir_path.iterdir():
                    if subdir.is_dir():
                        for video_file in subdir.glob("*-front.mp4"):
                            timestamp = self.parse_timestamp(video_file)
                            video_data.append((video_file, dir_name, timestamp))
        
        video_data.sort(key=lambda x: x[2] if x[2] else datetime.min, reverse=True)
        
        # Group events by finding first clip of each sequence
        processed_timestamps = set()
        
        for video_file, dir_name, timestamp in video_data:
            if timestamp and timestamp not in processed_timestamps:
                # Get all sequential clips starting from this one
                sequential_clips = self.get_sequential_clips(video_file, 'front')
                
                # Mark all timestamps in this sequence as processed
                for clip in sequential_clips:
                    clip_time = self.parse_timestamp(clip)
                    if clip_time:
                        processed_timestamps.add(clip_time)
                
                # Use the first clip's timestamp for display
                first_clip_time = self.parse_timestamp(sequential_clips[0])
                
                if first_clip_time:
                    duration_min = len(sequential_clips)
                    date_str = first_clip_time.strftime('%m/%d/%Y')
                    time_str = first_clip_time.strftime('%I:%M:%S %p')
                    duration_str = f"{duration_min} min"
                    type_str = dir_name.replace('Clips', '')
                    
                    event_data = {
                        'path': sequential_clips[0],
                        'timestamp': first_clip_time,
                        'duration': duration_min,
                        'type': dir_name,
                        'date': date_str,
                        'time': time_str
                    }
                    self.all_events.append(event_data)
        
        self.filter_events()
        
    def filter_events(self):
        """Filter events based on search text"""
        for item in self.event_tree.get_children():
            self.event_tree.delete(item)
        
        self.video_files = []
        search_text = self.search_var.get().lower()
        
        event_number = 1
        for event in self.all_events:
            if search_text:
                searchable = f"{event['date']} {event['time']} {event['type']}".lower()
                if search_text not in searchable:
                    continue
            
            self.event_tree.insert('', 'end', 
                                  text=f"#{event_number}",
                                  values=(event['date'], event['time'], 
                                         f"{event['duration']} min", 
                                         event['type'].replace('Clips', '')))
            self.video_files.append(event['path'])
            event_number += 1
        
        count = len(self.video_files)
        folder_type = self.folder_type.get()
        self.status_label.config(text=f"Found {count} event(s) in {folder_type}")
                    
    def on_event_select(self, event):
        """Handle event selection from tree"""
        selection = self.event_tree.selection()
        if selection:
            item = selection[0]
            index = self.event_tree.index(item)
            video_path = self.video_files[index]
            self.load_merged_video(video_path)
            
    def load_merged_video(self, front_video_path):
        """Load all camera angles for merged playback with sequential clip stitching"""
        for cap in self.video_captures.values():
            if isinstance(cap, MultiVideoCapture):
                cap.release()
        self.video_captures.clear()
        
        camera_clips = self.get_camera_clips(front_video_path)
        
        total_clips = 0
        for camera, path in camera_clips.items():
            camera_type = camera if camera == 'front' or camera == 'back' else f"{camera}_repeater"
            sequential_clips = self.get_sequential_clips(path, camera_type)
            
            if sequential_clips:
                multi_cap = MultiVideoCapture(sequential_clips)
                if multi_cap.isOpened():
                    self.video_captures[camera] = multi_cap
                    total_clips = max(total_clips, len(sequential_clips))
        
        if self.video_captures:
            self.current_video = front_video_path
            timestamp = self.parse_timestamp(front_video_path)
            
            if timestamp:
                self.video_title.config(text=timestamp.strftime('%A, %B %d, %Y'))
                camera_count = len(self.video_captures)
                self.video_info.config(text=f"🕐 {timestamp.strftime('%I:%M:%S %p')} • 📹 {camera_count} cameras • ⏱️ {total_clips} minutes")
            
            self.is_playing = False
            self.play_button.config(text="▶ Play")
            self.show_merged_frame()
            self.status_label.config(text=f"Ready to play - {total_clips} minute event with {len(self.video_captures)} camera angles")
        else:
            messagebox.showerror("Error", f"Could not open any video files")
            
    def show_merged_frame(self):
        """Display merged frame from all cameras in a grid"""
        if not self.video_captures:
            return
        
        frames = {}
        
        for camera, cap in self.video_captures.items():
            ret, frame = cap.read()
            if ret:
                frames[camera] = frame
        
        if not frames:
            return
        
        frame_width, frame_height = 480, 270
        
        camera_order = ['front', 'back', 'left', 'right']
        resized_frames = []
        labels = []
        
        for camera in camera_order:
            if camera in frames:
                frame = cv2.resize(frames[camera], (frame_width, frame_height))
                resized_frames.append(frame)
                labels.append(camera.upper())
            else:
                black_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
                resized_frames.append(black_frame)
                labels.append(f"{camera.upper()} (N/A)")
        
        for i, (frame, label) in enumerate(zip(resized_frames, labels)):
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame_width, 50), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
            
            cv2.putText(frame, label, (15, 32), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.9, (255, 255, 255), 2, cv2.LINE_AA)
            resized_frames[i] = frame
        
        top_row = np.hstack([resized_frames[0], resized_frames[1]])
        bottom_row = np.hstack([resized_frames[2], resized_frames[3]])
        merged_frame = np.vstack([top_row, bottom_row])
        
        merged_frame = cv2.cvtColor(merged_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(merged_frame)
        imgtk = ImageTk.PhotoImage(image=img)
        
        self.video_frame.imgtk = imgtk
        self.video_frame.configure(image=imgtk)
        
        if 'front' in self.video_captures:
            cap = self.video_captures['front']
            current_pos = cap.get(cv2.CAP_PROP_POS_FRAMES)
            total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            if total_frames > 0:
                progress = (current_pos / total_frames) * 100
                self.progress_var.set(progress)
                
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps > 0:
                    current_time = int(current_pos / fps)
                    total_time = int(total_frames / fps)
                    self.time_label.config(text=f"{current_time//60:02d}:{current_time%60:02d} / {total_time//60:02d}:{total_time%60:02d}")
                    
    def toggle_playback(self):
        """Toggle play/pause"""
        if not self.video_captures:
            messagebox.showwarning("No Video", "Please select an event first")
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
            has_frames = False
            for cap in self.video_captures.values():
                if cap.get(cv2.CAP_PROP_POS_FRAMES) < cap.get(cv2.CAP_PROP_FRAME_COUNT):
                    has_frames = True
                    break
            
            if has_frames:
                self.show_merged_frame()
                self.root.after(16, self.play_video)  # ~60 FPS (16ms delay)
            else:
                self.is_playing = False
                self.play_button.config(text="▶ Play")
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
            if 'front' in self.video_captures:
                cap = self.video_captures['front']
                total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                frame_number = int((float(value) / 100) * total_frames)
                
                for camera_cap in self.video_captures.values():
                    camera_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                
                if not self.is_playing:
                    self.show_merged_frame()
                
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About TeslaCam Viewer", 
                          "TeslaCam Viewer v2.0\n\n"
                          "A modern application for viewing Tesla dashcam footage\n\n"
                          "Features:\n"
                          "  • 4-camera synchronized playback\n"
                          "  • Automatic clip stitching\n"
                          "  • Event timeline and filtering\n"
                          "  • Modern, intuitive interface\n\n"
                          "Created by Aidan\n"
                          "GitHub: github.com/A1dqn/teslacam-viewer\n\n"
                          "Keyboard Shortcuts:\n"
                          "  • Ctrl+O: Open folder\n"
                          "  • Space: Play/Pause\n"
                          "  • Ctrl+Q: Quit")
        
    def __del__(self):
        """Cleanup on exit"""
        for cap in self.video_captures.values():
            if isinstance(cap, MultiVideoCapture):
                cap.release()


def main():
    """Main application entry point"""
    root = tk.Tk()
    app = TeslaCamViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()