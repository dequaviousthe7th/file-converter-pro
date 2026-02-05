#!/usr/bin/env python3
"""
File Converter Pro - Simple UI (WinRAR Style)
Basic, clean, functional
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.converters.pdf_converter import PDFConverter
from backend.converters.word_converter import WordConverter
from backend.converters.markdown_converter import MarkdownConverter
from backend.converters.image_converter import ImageConverter
from backend.converters.text_converter import TextConverter

FORMATS = {
    'pdf': {'name': 'PDF', 'to': ['docx', 'txt', 'md', 'png', 'jpg']},
    'docx': {'name': 'Word', 'to': ['pdf', 'txt', 'md']},
    'md': {'name': 'Markdown', 'to': ['pdf', 'docx', 'txt', 'html']},
    'txt': {'name': 'Text', 'to': ['pdf', 'docx', 'md']},
    'png': {'name': 'PNG', 'to': ['pdf', 'jpg', 'webp', 'bmp']},
    'jpg': {'name': 'JPG', 'to': ['pdf', 'png', 'webp', 'bmp']},
    'jpeg': {'name': 'JPEG', 'to': ['pdf', 'png', 'webp', 'bmp']},
    'webp': {'name': 'WebP', 'to': ['pdf', 'png', 'jpg', 'bmp']},
    'bmp': {'name': 'BMP', 'to': ['pdf', 'png', 'jpg', 'webp']},
    'html': {'name': 'HTML', 'to': ['pdf', 'md']}
}


class SimpleConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("File Converter Pro")
        self.root.geometry("400x500")
        self.root.resizable(True, True)
        self.root.minsize(350, 500)
        
        self.center_window()
        
        self.selected_file = None
        self.target_format = None
        self.conversion_thread = None
        self.stop_requested = False
        self.killed = False  # Track if conversion was killed
        self.output_dir = Path(__file__).parent / "converted"
        self.output_dir.mkdir(exist_ok=True)
        
        self.create_ui()
        
    def center_window(self):
        self.root.update_idletasks()
        w, h = 400, 500
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        
    def create_ui(self):
        # Create a canvas with scrollbar for scrolling
        canvas = tk.Canvas(self.root, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        
        # Main frame inside canvas
        main = ttk.Frame(canvas, padding="15")
        
        # Configure canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollbar hidden initially (only show when needed)
        scrollbar.pack(side="right", fill="y")
        scrollbar.pack_forget()  # Hide initially
        canvas.pack(side="left", fill="both", expand=True)
        
        # Function to show/hide scrollbar based on content
        def update_scrollbar(event=None):
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = canvas.winfo_height()
                if content_height > canvas_height:
                    scrollbar.pack(side="right", fill="y")
                else:
                    scrollbar.pack_forget()
        
        # Update scrollbar on configure
        canvas.bind("<Configure>", lambda e: (on_canvas_configure(e), update_scrollbar(e)))
        main.bind("<Configure>", lambda e: (configure_canvas(e), update_scrollbar(e)))
        
        # Create window inside canvas - WIDTH MUST MATCH ROOT
        canvas_window = canvas.create_window((0, 0), window=main, anchor="nw", width=400)
        
        # Update scroll region when frame changes size
        def configure_canvas(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        main.bind("<Configure>", configure_canvas)
        
        # Also update when canvas changes size
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", on_canvas_configure)
        
        # Header with title and credit
        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 15))
        
        # Logo, Title and Credit - stacked
        header_left = ttk.Frame(header)
        header_left.pack(side="left")
        
        # Logo and Title row
        logo_title_row = ttk.Frame(header_left)
        logo_title_row.pack(anchor="w")
        
        # Canvas with NO border (highlightthickness=0)
        logo_canvas = tk.Canvas(logo_title_row, width=40, height=40, bg="#f0f0f0", 
                               highlightthickness=0, bd=0)
        logo_canvas.pack(side="left", padx=(0, 10))
        logo_canvas.create_polygon(20, 5, 35, 20, 25, 20, 25, 35, 15, 35, 15, 20, 5, 20, 
                                  fill="#5ba3e8", outline="#5ba3e8")
        
        # Right side of header - Version at top right
        header_right = ttk.Frame(header)
        header_right.pack(side="right")
        
        # Version at top right - CODE LOCATION: Line ~131
        # ADJUST pady=(TOP, BOTTOM) to move up/down
        ttk.Label(header_right, text="Version: 1.1.0", font=("Segoe UI", 8), foreground="gray").pack(anchor="ne", pady=(32, 0))
        
        title_frame = ttk.Frame(logo_title_row)
        title_frame.pack(side="left")
        
        ttk.Label(title_frame, text="File Converter Pro", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        
        # Built by credit - UNDER the title - CODE LOCATION: Line ~141
        # This is below "File Converter Pro" title
        ttk.Label(title_frame, text="Built by: Dequavious", font=("Segoe UI", 8), foreground="gray").pack(anchor="w")
        
        # File selection
        file_frame = ttk.LabelFrame(main, text="Select File", padding="10")
        file_frame.pack(fill="x", pady=(0, 10))
        
        file_row = ttk.Frame(file_frame)
        file_row.pack(fill="x")
        
        self.file_entry = ttk.Entry(file_row, state="readonly")
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ttk.Button(file_row, text="Browse...", command=self.browse_file, width=10).pack(side="right")
        
        self.file_info = ttk.Label(file_frame, text="No file selected", foreground="gray")
        self.file_info.pack(anchor="w", pady=(5, 0))
        
        # Format selection - FIXED HEIGHT to prevent expansion
        self.format_frame = ttk.LabelFrame(main, text="Convert To", padding="10", height=90)
        self.format_frame.pack(fill="x", pady=(0, 10))
        self.format_frame.pack_propagate(False)  # Prevent frame from resizing to fit content
        
        self.format_var = tk.StringVar()
        self.format_buttons = []
        
        self.format_placeholder = ttk.Label(self.format_frame, text="Select a file first", foreground="gray")
        self.format_placeholder.pack(pady=15)
        
        # Convert button - Standard style like Open Output Folder, but bigger
        self.convert_btn = ttk.Button(main, text="Convert File", command=self.convert, state="disabled")
        self.convert_btn.pack(fill="x", pady=(0, 10), ipady=8)
        
        # Progress bar (hidden initially)
        self.progress = ttk.Progressbar(main, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 5))
        self.progress["value"] = 0
        
        # Kill button (disabled initially) - INSTANT KILL
        self.stop_btn = ttk.Button(main, text="☠ Kill", command=self.kill_conversion, state="disabled")
        self.stop_btn.pack(anchor="e", pady=(0, 10))
        
        # Status
        self.status = ttk.Label(main, text="Ready", foreground="gray")
        self.status.pack(anchor="w")
        
        # Separator
        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=15)
        
        # Output folder
        ttk.Button(main, text="Open Output Folder", command=self.open_output_folder).pack(fill="x")
        
    def browse_file(self):
        filetypes = [
            ("All Supported", "*.pdf *.docx *.md *.txt *.png *.jpg *.jpeg *.webp *.bmp *.html"),
            ("PDF", "*.pdf"), ("Word", "*.docx"), ("Markdown", "*.md"),
            ("Text", "*.txt"), ("Images", "*.png *.jpg *.jpeg *.webp *.bmp"),
            ("HTML", "*.html"), ("All Files", "*.*")
        ]
        
        path = filedialog.askopenfilename(title="Select a file", filetypes=filetypes)
        if not path:
            return
            
        ext = Path(path).suffix.lower().lstrip('.')
        if ext not in FORMATS:
            messagebox.showerror("Error", f".{ext} not supported")
            return
            
        self.selected_file = {'path': path, 'name': Path(path).name, 'ext': ext, 'size': Path(path).stat().st_size}
        
        self.file_entry.configure(state="normal")
        self.file_entry.delete(0, "end")
        self.file_entry.insert(0, path)
        self.file_entry.configure(state="readonly")
        
        size_kb = self.selected_file['size'] / 1024
        self.file_info.configure(text=f"{FORMATS[ext]['name']} • {size_kb:.1f} KB")
        
        self.show_formats(ext)
        
    def show_formats(self, ext):
        self.format_placeholder.pack_forget()
        
        # Clear old buttons and frames
        for widget in self.format_frame.winfo_children():
            widget.destroy()
        self.format_buttons.clear()
        
        available = FORMATS[ext]['to']
        frame = ttk.Frame(self.format_frame)
        frame.pack(fill="x")
        
        row, col = 0, 0
        for fmt in available:
            name = FORMATS.get(fmt, {}).get('name', fmt.upper())
            rb = ttk.Radiobutton(frame, text=name, variable=self.format_var, value=fmt,
                                command=self.on_format_selected)
            rb.grid(row=row, column=col, sticky="w", padx=10, pady=5)
            self.format_buttons.append(rb)
            col += 1
            if col > 2:
                col = 0
                row += 1
                
    def on_format_selected(self):
        self.target_format = self.format_var.get()
        self.convert_btn.configure(state="normal")
        self.status.configure(text=f"Ready to convert to {self.target_format.upper()}")
        
    def convert(self):
        if not self.selected_file or not self.target_format:
            return
        
        # Reset kill state
        self.killed = False
        self.stop_requested = False
            
        self.convert_btn.configure(state="disabled", text="Converting...")
        self.stop_btn.configure(state="normal")
        self.status.configure(text="Converting...")
        self.progress["value"] = 0
        self.root.update()
        
        # Start progress animation
        self.animate_progress()
        
        # Create daemon thread that can be killed
        self.conversion_thread = threading.Thread(target=self.do_convert)
        self.conversion_thread.daemon = True  # Daemon so it dies with main
        self.conversion_thread.start()
        
    def kill_conversion(self):
        """Kill the conversion instantly"""
        self.killed = True
        self.stop_requested = True
        self.status.configure(text="Killed")
        
        # INSTANT KILL: Terminate the thread by force
        if self.conversion_thread and self.conversion_thread.is_alive():
            import ctypes
            thread_id = self.conversion_thread.ident
            if thread_id:
                try:
                    # Raise exception in the thread to kill it
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(
                        ctypes.c_long(thread_id), ctypes.py_object(SystemExit)
                    )
                except:
                    pass
        
        # INSTANT UI RESET - FORCE IT
        self.conversion_thread = None
        self.progress["value"] = 0
        self.convert_btn.configure(state="disabled", text="Convert File")
        self.stop_btn.configure(state="disabled")
        
        # Cancel any pending after callbacks
        for after_id in self.root.tk.call('after', 'info'):
            try:
                self.root.after_cancel(after_id)
            except:
                pass
        
    def animate_progress(self):
        """Animate progress bar during conversion - FAST"""
        # Stop animation if killed or stopped
        if self.killed or self.stop_requested:
            return
        if self.convert_btn.cget("text") == "Converting...":
            current = self.progress["value"]
            if current < 90:
                self.progress["value"] = current + 5  # Bigger steps
                self.root.after(50, self.animate_progress)  # Faster updates
        
    def do_convert(self):
        try:
            # Check if killed immediately
            if self.killed:
                return
                
            input_path = self.selected_file['path']
            target = self.target_format
            ext = self.selected_file['ext']
            
            output_name = f"{Path(input_path).stem}_converted.{target}"
            output_path = str(self.output_dir / output_name)
            
            converter = None
            if ext == 'pdf':
                converter = PDFConverter()
            elif ext == 'docx':
                converter = WordConverter()
            elif ext == 'md':
                converter = MarkdownConverter()
            elif ext in ['png', 'jpg', 'jpeg', 'webp', 'bmp']:
                converter = ImageConverter()
            elif ext == 'txt':
                converter = TextConverter()
            elif ext == 'html':
                converter = MarkdownConverter()
                
            if converter is None:
                raise Exception(f"No converter for {ext}")
            
            # Check if killed before conversion
            if self.killed:
                return
                
            success = converter.convert(input_path, output_path, target)
            
            # Check if killed after conversion
            if self.killed:
                return
            
            if success:
                self.root.after(0, lambda: self.done(output_path))
            else:
                self.root.after(0, lambda: self.failed("Conversion failed"))
        except Exception as e:
            if self.killed:
                return  # Ignore errors if killed
            error_msg = str(e)
            print(f"Error: {error_msg}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda msg=error_msg: self.failed(msg))
            
    def done(self, path):
        # If killed, ignore the result completely
        if self.killed:
            return
        if self.stop_requested:
            self.stop_requested = False
            self.reset()
            return
        self.progress["value"] = 100
        self.convert_btn.configure(state="normal", text="Convert File")
        self.stop_btn.configure(state="disabled")
        name = Path(path).name
        self.status.configure(text=f"Saved: {name}")
        
        # Auto-reset progress bar after 2 seconds
        self.root.after(2000, lambda: self.progress.configure(value=0))
        
        if messagebox.askyesno("Success!", f"Converted!\n\nSaved as: {name}\n\nOpen folder?"):
            self.open_output_folder()
        self.reset()
        
    def failed(self, error=""):
        # If killed, ignore the error completely
        if self.killed:
            return
        was_stopped = self.stop_requested
        self.stop_requested = False
        self.progress["value"] = 0
        self.convert_btn.configure(state="disabled" if was_stopped else "normal", text="Convert File")
        self.stop_btn.configure(state="disabled")
        self.status.configure(text="Stopped" if was_stopped else "Failed")
        if not was_stopped:
            messagebox.showerror("Error", f"Conversion failed.\n{error[:200]}")
        
    def reset(self):
        self.selected_file = None
        self.target_format = None
        self.format_var.set("")
        
        self.file_entry.configure(state="normal")
        self.file_entry.delete(0, "end")
        self.file_entry.configure(state="readonly")
        
        self.file_info.configure(text="No file selected", foreground="gray")
        
        # Clear all widgets from format frame to prevent expansion
        for widget in self.format_frame.winfo_children():
            widget.destroy()
        self.format_buttons.clear()
        
        self.format_placeholder.pack(pady=15)
        self.convert_btn.configure(state="disabled", text="Convert File")
        self.stop_btn.configure(state="disabled")
        self.progress["value"] = 0
        self.status.configure(text="Ready", foreground="gray")
        self.stop_requested = False
        self.killed = False
        
    def open_output_folder(self):
        import subprocess
        subprocess.run(['explorer', str(self.output_dir)])


def main():
    root = tk.Tk()
    app = SimpleConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
