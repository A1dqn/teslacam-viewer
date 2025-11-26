#!/usr/bin/env python3
"""
TeslaCam Viewer - A GUI application for viewing Tesla dashcam footage
Author: Aidan
License: MIT
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from pathlib import Path
import cv2
from PIL import Image, ImageTk
from datetime import datetime, timedelta
import threading
import numpy as np
import platform
import time
import json


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


class TagNoteDialog(tk.Toplevel):
    """Dialog for editing event tags and notes"""
    def __init__(self, parent, event_data):
        super().__init__(parent)
        self.title("Edit Event Tags & Notes")
        self.geometry("500x400")
        self.configure(bg='#2d2d2d')
        
        self.event_data = event_data
        self.result = None
        
        # Tags section
        tk.Label(self, text="Tags (comma-separated):", bg='#2d2d2d', fg='#ffffff',
                font=('Segoe UI', 10, 'bold')).pack(pady=(20, 5), padx=20, anchor='w')
        
        self.tags_entry = tk.Entry(self, bg='#3c3c3c', fg='#ffffff',
                                   font=('Segoe UI', 10),
                                   insertbackground='#ffffff',
                                   relief=tk.FLAT)
        self.tags_entry.pack(fill=tk.X, padx=20, ipady=5)
        
        # Pre-fill existing tags
        if 'tags' in event_data and event_data['tags']:
            self.tags_entry.insert(0, ', '.join(event_data['tags']))
        
        # Notes section
        tk.Label(self, text="Notes:", bg='#2d2d2d', fg='#ffffff',
                font=('Segoe UI', 10, 'bold')).pack(pady=(20, 5), padx=20, anchor='w')
        
        self.notes_text = tk.Text(self, bg='#3c3c3c', fg='#ffffff',
                                 font=('Segoe UI', 10),
                                 insertbackground='#ffffff',
                                 relief=tk.FLAT, height=10)
        self.notes_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Pre-fill existing notes
        if 'notes' in event_data and event_data['notes']:
            self.notes_text.insert('1.0', event_data['notes'])
        
        # Buttons
        button_frame = tk.Frame(self, bg='#2d2d2d')
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        tk.Button(button_frame, text="Save", command=self.save,
                 bg='#007acc', fg='#ffffff',
                 font=('Segoe UI', 10, 'bold'),
                 relief=tk.FLAT, padx=20, pady=8,
                 cursor='hand2').pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(button_frame, text="Cancel", command=self.cancel,
                 bg='#3c3c3c', fg='#ffffff',
                 font=('Segoe UI', 10),
                 relief=tk.FLAT, padx=20, pady=8,
                 cursor='hand2').pack(side=tk.LEFT)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
    def save(self):
        """Save tags and notes"""
        tags_text = self.tags_entry.get().strip()
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
        notes = self.notes_text.get('1.0', 'end-1c').strip()
        
        self.result = {
            'tags': tags,
            'notes': notes
        }
        self.destroy()
    
    def cancel(self):
        """Cancel without saving"""
        self.result = None
        self.destroy()


class ExportProgressDialog(tk.Toplevel):
    """Dialog showing export progress"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Exporting Video")
        self.geometry("400x150")
        self.configure(bg='#2d2d2d')
        
        tk.Label(self, text="Exporting video...", bg='#2d2d2d', fg='#ffffff',
                font=('Segoe UI', 12, 'bold')).pack(pady=(20, 10))
        
        self.progress = ttk.Progressbar(self, length=350, mode='determinate')
        self.progress.pack(pady=10)
        
        self.status_label = tk.Label(self, text="Processing...", bg='#2d2d2d', fg='#888888',
                                     font=('Segoe UI', 9))
        self.status_label.pack(pady=10)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
    def update_progress(self, value, status=""):
        """Update progress bar and status"""
        self.progress['value'] = value
        if status:
            self.status_label.config(text=status)
        self.update()


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
        self.playback_speed = 1.0  # Current playback speed multiplier
        self.speed_buttons = []  # Store speed button references
        self.last_frame_time = 0  # Track time of last frame for accurate playback
        self.video_fps = 30.0  # Will be set from actual video
        self.metadata = {}  # Store tags and notes
        
        # Configure style
        self.setup_style()
        
        # Setup UI
        self.setup_ui()
        
        # Auto-detect TeslaCam folder on startup
        self.root.after(100, self.auto_detect_teslacam)
        
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
        file_menu.add_command(label="Export Current Event...", command=self.export_current_event, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        help_menu = tk.Menu(menubar, tearoff=0, bg='#2d2d2d', fg='#ffffff')
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.open_folder())
        self.root.bind('<Control-e>', lambda e: self.export_current_event())
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
        
        # Export button
        export_btn = tk.Button(toolbar, text="💾 Export Event", 
                              command=self.export_current_event,
                              bg='#3c3c3c', fg='#ffffff', 
                              font=('Segoe UI', 11),
                              relief=tk.FLAT, padx=20, pady=10,
                              cursor='hand2')
        export_btn.pack(side=tk.LEFT, padx=(0, 15), pady=10)
        
        # Folder path label
        self.folder_label = tk.Label(toolbar, text="Searching for TeslaCam folder...", 
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
        columns = ('date', 'time', 'duration', 'type', 'tags')
        self.event_tree = ttk.Treeview(list_container, columns=columns, 
                                       show='tree headings', selectmode='browse')
        
        # Define columns
        self.event_tree.heading('#0', text='Event')
        self.event_tree.heading('date', text='Date')
        self.event_tree.heading('time', text='Time')
        self.event_tree.heading('duration', text='Duration')
        self.event_tree.heading('type', text='Type')
        self.event_tree.heading('tags', text='Tags')
        
        self.event_tree.column('#0', width=50, minwidth=50)
        self.event_tree.column('date', width=100, minwidth=80)
        self.event_tree.column('time', width=100, minwidth=80)
        self.event_tree.column('duration', width=70, minwidth=60)
        self.event_tree.column('type', width=60, minwidth=50)
        self.event_tree.column('tags', width=120, minwidth=80)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=self.event_tree.yview)
        self.event_tree.configure(yscrollcommand=scrollbar.set)
        
        self.event_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.event_tree.bind('<<TreeviewSelect>>', self.on_event_select)
        
        # Context menu for event tree
        self.context_menu = tk.Menu(self.root, tearoff=0, bg='#2d2d2d', fg='#ffffff')
        self.context_menu.add_command(label="✏️ Edit Tags & Notes", command=self.edit_tags_notes)
        self.context_menu.add_command(label="💾 Export Event", command=self.export_selected_event)
        self.event_tree.bind('<Button-3>', self.show_context_menu)  # Right-click
        
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
        
        # Tags and notes display
        self.tags_notes_frame = tk.Frame(right_panel, bg='#1e1e1e')
        self.tags_notes_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.tags_label = tk.Label(self.tags_notes_frame, text="",
                                   bg='#1e1e1e', fg='#888888',
                                   font=('Segoe UI', 9),
                                   anchor='w')
        self.tags_label.pack(side=tk.LEFT)
        
        self.notes_label = tk.Label(self.tags_notes_frame, text="",
                                    bg='#1e1e1e', fg='#888888',
                                    font=('Segoe UI', 9, 'italic'),
                                    anchor='w')
        self.notes_label.pack(side=tk.LEFT, padx=(15, 0))
        
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
        
        # Speed control buttons
        speed_frame = tk.Frame(controls_frame, bg='#2d2d2d')
        speed_frame.pack(pady=(0, 10))
        
        tk.Label(speed_frame, text="Speed:", bg='#2d2d2d', fg='#ffffff',
                font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 10))
        
        speeds = [0.5, 1.0, 1.5, 2.0, 3.0]
        for speed in speeds:
            btn = tk.Button(speed_frame, text=f"{speed}x",
                          command=lambda s=speed: self.set_playback_speed(s),
                          bg='#3c3c3c', fg='#ffffff',
                          font=('Segoe UI', 9),
                          relief=tk.FLAT, padx=12, pady=4,
                          cursor='hand2')
            btn.pack(side=tk.LEFT, padx=2)
            self.speed_buttons.append(btn)
        
        # Highlight 1x speed by default
        self.speed_buttons[1].config(bg='#007acc')
        
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
        self.status_label = tk.Label(self.root, text="Ready - Searching for TeslaCam folder...", 
                                    relief=tk.FLAT, bg='#2d2d2d', fg='#888888',
                                    font=('Segoe UI', 9), anchor='w', padx=15)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
    
    def show_context_menu(self, event):
        """Show context menu on right-click"""
        # Select the item under cursor
        item = self.event_tree.identify_row(event.y)
        if item:
            self.event_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def edit_tags_notes(self):
        """Open dialog to edit tags and notes for selected event"""
        selection = self.event_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an event first")
            return
        
        item = selection[0]
        index = self.event_tree.index(item)
        event_data = self.all_events[index]
        
        # Open dialog
        dialog = TagNoteDialog(self.root, event_data)
        self.root.wait_window(dialog)
        
        if dialog.result:
            # Update event data
            event_data['tags'] = dialog.result['tags']
            event_data['notes'] = dialog.result['notes']
            
            # Save metadata
            self.save_metadata()
            
            # Refresh display
            self.filter_events()
            self.update_tags_notes_display(event_data)
    
    def update_tags_notes_display(self, event_data):
        """Update the tags and notes display for current event"""
        tags = event_data.get('tags', [])
        notes = event_data.get('notes', '')
        
        if tags:
            self.tags_label.config(text=f"🏷️ Tags: {', '.join(tags)}")
        else:
            self.tags_label.config(text="")
        
        if notes:
            # Truncate long notes
            display_notes = notes if len(notes) <= 50 else notes[:47] + "..."
            self.notes_label.config(text=f"📝 {display_notes}")
        else:
            self.notes_label.config(text="")
    
    def get_event_key(self, event_data):
        """Generate unique key for event"""
        first_clip = event_data['clips'][0]
        return str(first_clip)
    
    def load_metadata(self):
        """Load tags and notes from JSON file"""
        if not self.teslacam_path:
            return
        
        metadata_file = self.teslacam_path / 'teslacam_metadata.json'
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    self.metadata = json.load(f)
            except:
                self.metadata = {}
        else:
            self.metadata = {}
    
    def save_metadata(self):
        """Save tags and notes to JSON file"""
        if not self.teslacam_path:
            return
        
        metadata_file = self.teslacam_path / 'teslacam_metadata.json'
        
        # Build metadata from all events
        metadata_to_save = {}
        for event in self.all_events:
            event_key = self.get_event_key(event)
            if event.get('tags') or event.get('notes'):
                metadata_to_save[event_key] = {
                    'tags': event.get('tags', []),
                    'notes': event.get('notes', '')
                }
        
        try:
            with open(metadata_file, 'w') as f:
                json.dump(metadata_to_save, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save metadata: {str(e)}")
    
    def export_selected_event(self):
        """Export the selected event"""
        selection = self.event_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an event to export")
            return
        
        item = selection[0]
        index = self.event_tree.index(item)
        event_clips = self.video_files[index]
        event_data = self.all_events[index]
        
        self.export_event(event_clips, event_data)
    
    def export_current_event(self):
        """Export the currently loaded event"""
        if not self.current_video:
            messagebox.showwarning("No Event", "Please select an event first")
            return
        
        selection = self.event_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an event first")
            return
        
        self.export_selected_event()
    
    def export_event(self, event_clips, event_data):
        """Export event as merged video file"""
        # Ask user for save location
        timestamp = event_data['timestamp']
        default_name = f"TeslaCam_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4"), ("All Files", "*.*")],
            initialfile=default_name
        )
        
        if not save_path:
            return
        
        # Create progress dialog
        progress_dialog = ExportProgressDialog(self.root)
        
        # Export in separate thread
        def export_thread():
            try:
                self.export_video_file(event_clips, save_path, progress_dialog)
                progress_dialog.destroy()
                messagebox.showinfo("Export Complete", f"Video exported successfully to:\n{save_path}")
            except Exception as e:
                progress_dialog.destroy()
                messagebox.showerror("Export Failed", f"Failed to export video:\n{str(e)}")
        
        threading.Thread(target=export_thread, daemon=True).start()
    
    def export_video_file(self, event_clips, output_path, progress_dialog):
        """Export merged 4-camera video to file"""
        # Collect all camera clips
        camera_clip_lists = {
            'front': [],
            'left': [],
            'right': [],
            'back': []
        }
        
        for front_clip in event_clips:
            camera_clips = self.get_camera_clips(front_clip)
            for camera, clip_path in camera_clips.items():
                camera_clip_lists[camera].append(clip_path)
        
        # Create video captures
        captures = {}
        for camera, clip_list in camera_clip_lists.items():
            if clip_list:
                multi_cap = MultiVideoCapture(clip_list)
                if multi_cap.isOpened():
                    captures[camera] = multi_cap
        
        if not captures:
            raise Exception("No video files found to export")
        
        # Get video properties
        front_cap = captures.get('front', list(captures.values())[0])
        fps = front_cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0
        
        total_frames = front_cap.get(cv2.CAP_PROP_FRAME_COUNT)
        
        # Output video settings (4-camera grid: 960x540)
        frame_width, frame_height = 480, 270
        output_width, output_height = frame_width * 2, frame_height * 2
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (output_width, output_height))
        
        camera_order = ['front', 'back', 'left', 'right']
        frame_count = 0
        
        while True:
            frames = {}
            has_frames = False
            
            # Read from all cameras
            for camera, cap in captures.items():
                ret, frame = cap.read()
                if ret:
                    frames[camera] = frame
                    has_frames = True
            
            if not has_frames:
                break
            
            # Create merged frame
            resized_frames = []
            for camera in camera_order:
                if camera in frames:
                    frame = cv2.resize(frames[camera], (frame_width, frame_height))
                    # Add camera label
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (0, 0), (frame_width, 50), (0, 0, 0), -1)
                    frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
                    cv2.putText(frame, camera.upper(), (15, 32), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
                    resized_frames.append(frame)
                else:
                    black_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
                    resized_frames.append(black_frame)
            
            # Merge into grid
            top_row = np.hstack([resized_frames[0], resized_frames[1]])
            bottom_row = np.hstack([resized_frames[2], resized_frames[3]])
            merged_frame = np.vstack([top_row, bottom_row])
            
            # Write frame
            out.write(merged_frame)
            
            # Update progress
            frame_count += 1
            if total_frames > 0:
                progress = (frame_count / total_frames) * 100
                progress_dialog.update_progress(progress, f"Frame {frame_count}/{int(total_frames)}")
        
        # Cleanup
        out.release()
        for cap in captures.values():
            cap.release()
    
    def set_playback_speed(self, speed):
        """Set playback speed"""
        self.playback_speed = speed
        
        # Update button colors to show selected speed
        speeds = [0.5, 1.0, 1.5, 2.0, 3.0]
        for i, btn in enumerate(self.speed_buttons):
            if speeds[i] == speed:
                btn.config(bg='#007acc')
            else:
                btn.config(bg='#3c3c3c')
    
    def find_teslacam_folder(self):
        """Search for TeslaCam folder in common locations"""
        search_locations = []
        
        if platform.system() == 'Windows':
            # Check all drive letters (common for USB drives)
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    search_locations.append(Path(drive))
        else:
            # macOS and Linux
            # Check /Volumes (macOS) and /media, /mnt (Linux)
            for mount_point in ['/Volumes', '/media', '/mnt']:
                if os.path.exists(mount_point):
                    mount_path = Path(mount_point)
                    if mount_path.exists():
                        # Add all subdirectories (mounted drives)
                        try:
                            for item in mount_path.iterdir():
                                if item.is_dir():
                                    search_locations.append(item)
                        except PermissionError:
                            pass
        
        # Search each location for TeslaCam folder
        for location in search_locations:
            try:
                teslacam_path = location / "TeslaCam"
                if teslacam_path.exists() and teslacam_path.is_dir():
                    # Verify it has the expected subfolders
                    has_clips = any([
                        (teslacam_path / "SavedClips").exists(),
                        (teslacam_path / "SentryClips").exists(),
                        (teslacam_path / "RecentClips").exists()
                    ])
                    
                    if has_clips:
                        return teslacam_path
            except (PermissionError, OSError):
                continue
        
        return None
    
    def auto_detect_teslacam(self):
        """Automatically detect and load TeslaCam folder on startup"""
        self.status_label.config(text="Searching for TeslaCam folder...")
        self.root.update()
        
        teslacam_path = self.find_teslacam_folder()
        
        if teslacam_path:
            self.teslacam_path = teslacam_path
            self.folder_label.config(text=f"✓ Auto-detected: {str(teslacam_path)}", fg='#00ff00')
            self.status_label.config(text="TeslaCam folder auto-detected and loaded!")
            self.load_metadata()
            self.refresh_file_list()
        else:
            self.folder_label.config(text="No TeslaCam folder found - Click to select manually", fg='#ff9900')
            self.status_label.config(text="No TeslaCam folder found - Please open folder manually")
        
    def open_folder(self):
        """Open TeslaCam folder dialog"""
        folder = filedialog.askdirectory(title="Select TeslaCam Folder")
        if folder:
            self.teslacam_path = Path(folder)
            self.folder_label.config(text=str(folder), fg='#ffffff')
            self.load_metadata()
            self.refresh_file_list()
    
    def parse_timestamp(self, filename):
        """Parse timestamp from TeslaCam filename"""
        try:
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
    
    def get_all_clips_in_folder(self, base_video_path, camera_type):
        """Get ALL clips in the same folder/subfolder for this camera"""
        parent_dir = base_video_path.parent
        
        # Find all clips for this camera type in the same folder
        pattern = f"*-{camera_type}.mp4"
        all_clips = list(parent_dir.glob(pattern))
        
        # Sort by timestamp
        clips_with_time = []
        for clip in all_clips:
            timestamp = self.parse_timestamp(clip)
            if timestamp:
                clips_with_time.append((clip, timestamp))
        
        # Sort by time
        clips_with_time.sort(key=lambda x: x[1])
        
        return [clip for clip, _ in clips_with_time]
    
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
        
        # Collect all clips by folder/subfolder
        folder_clips = {}  # key: folder path, value: list of (clip, timestamp, dir_name)
        
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
                    folder_key = str(video_file.parent)
                    if folder_key not in folder_clips:
                        folder_clips[folder_key] = []
                    folder_clips[folder_key].append((video_file, timestamp, dir_name))
                
                # Search in subdirectories
                for subdir in dir_path.iterdir():
                    if subdir.is_dir():
                        for video_file in subdir.glob("*-front.mp4"):
                            timestamp = self.parse_timestamp(video_file)
                            folder_key = str(video_file.parent)
                            if folder_key not in folder_clips:
                                folder_clips[folder_key] = []
                            folder_clips[folder_key].append((video_file, timestamp, dir_name))
        
        # Group clips in each folder by time proximity
        for folder_path, clips in folder_clips.items():
            # Sort by timestamp
            clips.sort(key=lambda x: x[1] if x[1] else datetime.min)
            
            # Group clips that are within 15 minutes of each other
            events = []
            current_event = []
            
            for clip, timestamp, dir_name in clips:
                if not timestamp:
                    continue
                    
                if not current_event:
                    current_event.append((clip, timestamp, dir_name))
                else:
                    # Check if this clip is within 15 minutes of the previous one
                    last_timestamp = current_event[-1][1]
                    if (timestamp - last_timestamp).total_seconds() <= 900:  # 15 minutes
                        current_event.append((clip, timestamp, dir_name))
                    else:
                        # Start new event
                        events.append(current_event)
                        current_event = [(clip, timestamp, dir_name)]
            
            if current_event:
                events.append(current_event)
            
            # Create event entries
            for event_clips in events:
                if event_clips:
                    first_clip, first_time, dir_name = event_clips[0]
                    
                    duration_min = len(event_clips)
                    date_str = first_time.strftime('%m/%d/%Y')
                    time_str = first_time.strftime('%I:%M:%S %p')
                    duration_str = f"{duration_min} min"
                    type_str = dir_name.replace('Clips', '')
                    
                    # Store all clips for this event
                    all_clip_paths = [clip for clip, _, _ in event_clips]
                    
                    event_data = {
                        'clips': all_clip_paths,  # All clips in this event
                        'timestamp': first_time,
                        'duration': duration_min,
                        'type': dir_name,
                        'date': date_str,
                        'time': time_str,
                        'tags': [],
                        'notes': ''
                    }
                    
                    # Load tags and notes from metadata
                    event_key = self.get_event_key(event_data)
                    if event_key in self.metadata:
                        event_data['tags'] = self.metadata[event_key].get('tags', [])
                        event_data['notes'] = self.metadata[event_key].get('notes', '')
                    
                    self.all_events.append(event_data)
        
        # Sort all events by timestamp (newest first)
        self.all_events.sort(key=lambda x: x['timestamp'], reverse=True)
        
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
                searchable = f"{event['date']} {event['time']} {event['type']} {' '.join(event.get('tags', []))}".lower()
                if search_text not in searchable:
                    continue
            
            # Format tags for display
            tags_display = ', '.join(event.get('tags', [])) if event.get('tags') else ''
            
            self.event_tree.insert('', 'end', 
                                  text=f"#{event_number}",
                                  values=(event['date'], event['time'], 
                                         f"{event['duration']} min", 
                                         event['type'].replace('Clips', ''),
                                         tags_display))
            self.video_files.append(event['clips'])  # Store all clips for this event
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
            event_clips = self.video_files[index]  # Get all clips for this event
            event_data = self.all_events[index]
            self.load_merged_video(event_clips)
            self.update_tags_notes_display(event_data)
            
    def load_merged_video(self, front_video_clips):
        """Load all camera angles for merged playback with all clips in event"""
        for cap in self.video_captures.values():
            if isinstance(cap, MultiVideoCapture):
                cap.release()
        self.video_captures.clear()
        
        # For each camera, get corresponding clips
        camera_clip_lists = {
            'front': [],
            'left': [],
            'right': [],
            'back': []
        }
        
        # Collect all clips for each camera
        for front_clip in front_video_clips:
            camera_clips = self.get_camera_clips(front_clip)
            
            for camera, clip_path in camera_clips.items():
                if camera == 'front':
                    camera_clip_lists['front'].append(clip_path)
                elif camera == 'left':
                    camera_clip_lists['left'].append(clip_path)
                elif camera == 'right':
                    camera_clip_lists['right'].append(clip_path)
                elif camera == 'back':
                    camera_clip_lists['back'].append(clip_path)
        
        # Create MultiVideoCapture for each camera that has clips
        total_clips = 0
        for camera, clip_list in camera_clip_lists.items():
            if clip_list:
                multi_cap = MultiVideoCapture(clip_list)
                if multi_cap.isOpened():
                    self.video_captures[camera] = multi_cap
                    total_clips = max(total_clips, len(clip_list))
        
        if self.video_captures:
            self.current_video = front_video_clips[0]
            timestamp = self.parse_timestamp(front_video_clips[0])
            
            # Get actual video FPS for display only
            if 'front' in self.video_captures:
                fps = self.video_captures['front'].get(cv2.CAP_PROP_FPS)
                if fps > 0:
                    self.video_fps = fps
                else:
                    self.video_fps = 30.0  # Default
            
            if timestamp:
                self.video_title.config(text=timestamp.strftime('%A, %B %d, %Y'))
                camera_count = len(self.video_captures)
                self.video_info.config(text=f"🕐 {timestamp.strftime('%I:%M:%S %p')} • 📹 {camera_count} cameras • ⏱️ {total_clips} minutes • {self.video_fps:.1f} FPS")
            
            self.is_playing = False
            self.play_button.config(text="▶ Play")
            self.show_merged_frame()
            self.status_label.config(text=f"Ready to play - {total_clips} minute event")
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
            self.last_frame_time = time.time()
            self.play_video()
        else:
            self.play_button.config(text="▶ Play")
            
    def play_video(self):
        """Play merged video with normalized speed for all framerates"""
        if self.is_playing and self.video_captures:
            has_frames = False
            for cap in self.video_captures.values():
                if cap.get(cv2.CAP_PROP_POS_FRAMES) < cap.get(cv2.CAP_PROP_FRAME_COUNT):
                    has_frames = True
                    break
            
            if has_frames:
                current_time = time.time()
                
                # Use fixed 30ms frame interval for consistent real-time feel
                # This normalizes playback across all framerates
                frame_duration = 0.030 / self.playback_speed  # 30ms base = ~33 FPS feel
                time_since_last_frame = current_time - self.last_frame_time
                
                # Only show new frame if enough time has passed
                if time_since_last_frame >= frame_duration:
                    self.show_merged_frame()
                    self.last_frame_time = current_time
                
                # Schedule next update with minimal delay
                self.root.after(1, self.play_video)
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
                          "TeslaCam Viewer v2.1\n\n"
                          "A modern application for viewing Tesla dashcam footage\n\n"
                          "Features:\n"
                          "  • 4-camera synchronized playback\n"
                          "  • Automatic clip stitching\n"
                          "  • Event timeline and filtering\n"
                          "  • Auto-detect TeslaCam folder\n"
                          "  • Adjustable playback speed (0.5x - 3x)\n"
                          "  • Video export functionality\n"
                          "  • Event tagging and notes\n"
                          "  • Modern, intuitive interface\n\n"
                          "Created by Aidan\n"
                          "GitHub: github.com/A1dqn/teslacam-viewer\n\n"
                          "Keyboard Shortcuts:\n"
                          "  • Ctrl+O: Open folder\n"
                          "  • Ctrl+E: Export event\n"
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