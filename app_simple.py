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
        self.root.geometry("500x420")
        self.root.resizable(False, False)
        
        self.center_window()
        
        self.selected_file = None
        self.target_format = None
        self.output_dir = Path(__file__).parent / "converted"
        self.output_dir.mkdir(exist_ok=True)
        
        self.create_ui()
        
    def center_window(self):
        self.root.update_idletasks()
        w, h = 500, 420
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        
    def create_ui(self):
        main = ttk.Frame(self.root, padding="15")
        main.pack(fill="both", expand=True)
        
        # Header with title and credit
        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 15))
        
        # Logo (NO BORDER) and Title
        header_left = ttk.Frame(header)
        header_left.pack(side="left")
        
        # Canvas with NO border (highlightthickness=0)
        logo_canvas = tk.Canvas(header_left, width=40, height=40, bg="#f0f0f0", 
                               highlightthickness=0, bd=0)
        logo_canvas.pack(side="left", padx=(0, 10))
        logo_canvas.create_polygon(20, 5, 35, 20, 25, 20, 25, 35, 15, 35, 15, 20, 5, 20, 
                                  fill="#4a90d9", outline="#4a90d9")
        
        ttk.Label(header_left, text="File Converter Pro", font=("Segoe UI", 16, "bold")).pack(side="left")
        
        # Built by credit
        ttk.Label(header, text="Built by: Dequavious", font=("Segoe UI", 9), foreground="gray").pack(side="right")
        
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
        
        # Format selection
        self.format_frame = ttk.LabelFrame(main, text="Convert To", padding="10")
        self.format_frame.pack(fill="x", pady=(0, 10))
        
        self.format_var = tk.StringVar()
        self.format_buttons = []
        
        self.format_placeholder = ttk.Label(self.format_frame, text="Select a file first", foreground="gray")
        self.format_placeholder.pack(pady=15)
        
        # Convert button - BLUE
        self.convert_btn = tk.Button(main, text="Convert File", command=self.convert, state="disabled",
                                     bg="#4a90d9", fg="white", font=("Segoe UI", 10, "bold"),
                                     activebackground="#357abd", activeforeground="white")
        self.convert_btn.pack(fill="x", pady=(0, 10))
        
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
        
        for btn in self.format_buttons:
            btn.destroy()
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
            
        self.convert_btn.configure(state="disabled", text="Converting...")
        self.status.configure(text="Converting...")
        self.root.update()
        
        thread = threading.Thread(target=self.do_convert)
        thread.start()
        
    def do_convert(self):
        try:
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
                
            success = converter.convert(input_path, output_path, target)
            
            if success:
                self.root.after(0, lambda: self.done(output_path))
            else:
                self.root.after(0, lambda: self.failed("Conversion failed"))
        except Exception as e:
            error_msg = str(e)
            print(f"Error: {error_msg}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda msg=error_msg: self.failed(msg))
            
    def done(self, path):
        self.convert_btn.configure(state="normal", text="Convert File")
        name = Path(path).name
        self.status.configure(text=f"Saved: {name}")
        
        if messagebox.askyesno("Success!", f"Converted!\n\nSaved as: {name}\n\nOpen folder?"):
            self.open_output_folder()
        self.reset()
        
    def failed(self, error=""):
        self.convert_btn.configure(state="normal", text="Convert File")
        self.status.configure(text="Failed")
        messagebox.showerror("Error", f"Conversion failed.\n{error[:200]}")
        
    def reset(self):
        self.selected_file = None
        self.target_format = None
        self.format_var.set("")
        
        self.file_entry.configure(state="normal")
        self.file_entry.delete(0, "end")
        self.file_entry.configure(state="readonly")
        
        self.file_info.configure(text="No file selected", foreground="gray")
        
        for btn in self.format_buttons:
            btn.destroy()
        self.format_buttons.clear()
        
        self.format_placeholder.pack(pady=15)
        self.convert_btn.configure(state="disabled")
        self.status.configure(text="Ready", foreground="gray")
        
    def open_output_folder(self):
        import subprocess
        subprocess.run(['explorer', str(self.output_dir)])


def main():
    root = tk.Tk()
    app = SimpleConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
