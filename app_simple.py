#!/usr/bin/env python3
"""
File Converter Pro - Simple UI
Basic Windows style (like WinRAR)
Uses standard tkinter only
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Add backend to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from backend.converters.pdf_converter import PDFConverter
from backend.converters.word_converter import WordConverter
from backend.converters.markdown_converter import MarkdownConverter
from backend.converters.image_converter import ImageConverter
from backend.converters.text_converter import TextConverter

# Format configurations
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


class SimpleFileConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("File Converter Pro")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        
        # Center window
        self.center_window()
        
        # State
        self.selected_file = None
        self.target_format = None
        self.output_dir = BASE_DIR / "converted"
        self.output_dir.mkdir(exist_ok=True)
        
        # Create UI
        self.create_ui()
        
    def center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        width = 500
        height = 450
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def create_ui(self):
        """Create simple UI"""
        # Main frame with padding
        main = ttk.Frame(self.root, padding="20")
        main.pack(fill="both", expand=True)
        
        # Logo and Title row
        header = ttk.Frame(main)
        header.pack(anchor="w", pady=(0, 20), fill="x")
        
        # Simple logo using Canvas
        logo_canvas = tk.Canvas(header, width=40, height=40, bg="#f0f0f0", 
                               highlightthickness=1, highlightbackground="#999")
        logo_canvas.pack(side="left", padx=(0, 10))
        # Draw a simple arrow icon
        logo_canvas.create_polygon(20, 5, 35, 20, 25, 20, 25, 35, 15, 35, 15, 20, 5, 20, 
                                  fill="#4a90d9", outline="#4a90d9")
        
        # Title
        title = ttk.Label(header, text="File Converter Pro", font=("Segoe UI", 18, "bold"))
        title.pack(side="left")
        
        # File selection - more visible frame
        file_frame = tk.LabelFrame(main, text=" Select File ", font=("Segoe UI", 10, "bold"),
                                   bg="#f5f5f5", fg="#333", bd=2, relief="groove", padx=10, pady=10)
        file_frame.pack(fill="x", pady=(0, 15))
        
        file_row = tk.Frame(file_frame, bg="#f5f5f5")
        file_row.pack(fill="x")
        
        self.file_entry = tk.Entry(file_row, state="readonly", font=("Segoe UI", 10),
                                   bg="white", fg="#333", relief="solid", bd=1)
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=3)
        
        tk.Button(file_row, text="Browse...", command=self.browse_file, width=10,
                  font=("Segoe UI", 9), bg="#e0e0e0", relief="raised", bd=2).pack(side="right")
        
        # File info
        self.file_info = tk.Label(file_frame, text="No file selected", 
                                   bg="#f5f5f5", fg="#666", font=("Segoe UI", 9))
        self.file_info.pack(anchor="w", pady=(8, 0))
        
        # Format selection - more visible frame
        self.format_frame = tk.LabelFrame(main, text=" Convert To ", font=("Segoe UI", 10, "bold"),
                                          bg="#f5f5f5", fg="#333", bd=2, relief="groove", padx=10, pady=10)
        self.format_frame.pack(fill="x", pady=(0, 15))
        
        self.format_var = tk.StringVar()
        self.format_buttons = []
        
        # Placeholder label (will be replaced when file selected)
        self.format_placeholder = tk.Label(self.format_frame, text="Select a file first", 
                                          bg="#f5f5f5", fg="#888", font=("Segoe UI", 10))
        self.format_placeholder.pack(pady=20)
        
        # Convert button - more visible
        self.convert_btn = tk.Button(main, text="Convert File", command=self.convert, state="disabled",
                                     font=("Segoe UI", 11, "bold"), bg="#4a90d9", fg="white",
                                     activebackground="#357abd", activeforeground="white",
                                     relief="raised", bd=3, padx=10, pady=8)
        self.convert_btn.pack(fill="x", pady=(5, 10))
        
        # Status
        self.status = tk.Label(main, text="Ready", fg="#666", bg="#f0f0f0", 
                              font=("Segoe UI", 9), anchor="w")
        self.status.pack(fill="x", pady=(0, 10))
        
        # Separator
        tk.Frame(main, bg="#ccc", height=2).pack(fill="x", pady=10)
        
        # Output folder button
        tk.Button(main, text="Open Output Folder", command=self.open_output_folder,
                 font=("Segoe UI", 9), bg="#e0e0e0", relief="raised", bd=2, padx=5, pady=5).pack(fill="x")
        
    def browse_file(self):
        """Browse for file"""
        filetypes = [
            ("All Supported", "*.pdf *.docx *.md *.txt *.png *.jpg *.jpeg *.webp *.bmp *.html"),
            ("PDF Documents", "*.pdf"),
            ("Word Documents", "*.docx"),
            ("Markdown Files", "*.md"),
            ("Text Files", "*.txt"),
            ("Images", "*.png *.jpg *.jpeg *.webp *.bmp"),
            ("HTML Files", "*.html"),
            ("All Files", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            title="Select a file to convert",
            filetypes=filetypes
        )
        
        if not filepath:
            return
            
        ext = Path(filepath).suffix.lower().lstrip('.')
        
        if ext not in FORMATS:
            messagebox.showerror(
                "Unsupported Format",
                f"Files of type .{ext} are not supported.\n\n"
                "Supported: PDF, DOCX, MD, TXT, PNG, JPG, WEBP, BMP, HTML"
            )
            return
            
        self.selected_file = {
            'path': filepath,
            'name': Path(filepath).name,
            'ext': ext,
            'size': Path(filepath).stat().st_size
        }
        
        # Update file entry
        self.file_entry.configure(state="normal")
        self.file_entry.delete(0, "end")
        self.file_entry.insert(0, filepath)
        self.file_entry.configure(state="readonly")
        
        # Update info
        size_kb = self.selected_file['size'] / 1024
        fmt = FORMATS[ext]
        self.file_info.configure(text=f"{fmt['name']} • {size_kb:.1f} KB")
        
        # Show format options
        self.show_format_options(ext)
        
    def show_format_options(self, ext):
        """Show available format options"""
        # Clear placeholder
        self.format_placeholder.pack_forget()
        
        # Clear old buttons
        for btn in self.format_buttons:
            btn.destroy()
        self.format_buttons.clear()
        
        # Get available formats
        available = FORMATS[ext]['to']
        
        # Create radio buttons in a grid
        frame = tk.Frame(self.format_frame, bg="#f5f5f5")
        frame.pack(fill="x", pady=5)
        
        row, col = 0, 0
        for fmt in available:
            fmt_name = FORMATS.get(fmt, {}).get('name', fmt.upper())
            
            rb = tk.Radiobutton(
                frame,
                text=fmt_name,
                variable=self.format_var,
                value=fmt,
                command=self.on_format_selected,
                bg="#f5f5f5", fg="#333", font=("Segoe UI", 10),
                selectcolor="#4a90d9", activebackground="#e0e0e0"
            )
            rb.grid(row=row, column=col, sticky="w", padx=15, pady=8)
            self.format_buttons.append(rb)
            
            col += 1
            if col > 2:
                col = 0
                row += 1
                
    def on_format_selected(self):
        """Handle format selection"""
        self.target_format = self.format_var.get()
        self.convert_btn.configure(state="normal")
        self.status.configure(text=f"Ready to convert to {self.target_format.upper()}")
        
    def convert(self):
        """Start conversion"""
        if not self.selected_file or not self.target_format:
            return
            
        self.convert_btn.configure(state="disabled", text="Converting...")
        self.status.configure(text="Converting... Please wait")
        self.root.update()
        
        # Run in background thread
        thread = threading.Thread(target=self.do_conversion)
        thread.start()
        
    def do_conversion(self):
        """Perform the conversion"""
        try:
            input_path = self.selected_file['path']
            target = self.target_format
            ext = self.selected_file['ext']
            
            # Generate output path
            input_path_obj = Path(input_path)
            output_name = f"{input_path_obj.stem}_converted.{target}"
            output_path = str(self.output_dir / output_name)
            
            # Get converter
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
                
            if not converter:
                raise Exception("No converter available for this file type")
                
            # Convert
            success = converter.convert(input_path, output_path, target)
            
            if success:
                self.root.after(0, lambda: self.conversion_success(output_path))
            else:
                self.root.after(0, self.conversion_failed)
                
        except Exception as e:
            print(f"Conversion error: {e}")
            self.root.after(0, lambda: self.conversion_failed(str(e)))
            
    def conversion_success(self, output_path):
        """Handle successful conversion"""
        self.convert_btn.configure(state="normal", text="Convert File")
        filename = Path(output_path).name
        self.status.configure(text=f"Saved: {filename}", foreground="green")
        
        result = messagebox.askyesno(
            "Conversion Complete",
            f"File converted successfully!\n\nSaved as: {filename}\n\nOpen output folder?"
        )
        
        if result:
            self.open_output_folder()
            
        self.reset_ui()
        
    def conversion_failed(self, error=""):
        """Handle failed conversion"""
        self.convert_btn.configure(state="normal", text="Convert File")
        self.status.configure(text="Conversion failed", foreground="red")
        
        messagebox.showerror(
            "Error",
            f"Sorry, the conversion failed.\n\n{error if error else 'Please try again.'}"
        )
        
    def reset_ui(self):
        """Reset UI to initial state"""
        self.selected_file = None
        self.target_format = None
        self.format_var.set("")
        
        self.file_entry.configure(state="normal")
        self.file_entry.delete(0, "end")
        self.file_entry.configure(state="readonly")
        
        self.file_info.configure(text="No file selected", foreground="gray")
        
        # Clear format buttons
        for btn in self.format_buttons:
            btn.destroy()
        self.format_buttons.clear()
        
        self.format_placeholder.pack(pady=20)
        
        self.convert_btn.configure(state="disabled")
        self.status.configure(text="Ready", foreground="gray")
        
    def open_output_folder(self):
        """Open the output folder"""
        import subprocess
        
        path = str(self.output_dir)
        
        if sys.platform == 'win32':
            subprocess.run(['explorer', path])
        elif sys.platform == 'darwin':
            subprocess.run(['open', path])
        else:
            subprocess.run(['xdg-open', path])


def main():
    root = tk.Tk()
    
    # Set Windows style
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = SimpleFileConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
