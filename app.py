#!/usr/bin/env python3
"""
File Converter Pro - Advanced Modern UI
Dark theme with sidebar
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).parent))

from backend.converters.pdf_converter import PDFConverter
from backend.converters.word_converter import WordConverter
from backend.converters.markdown_converter import MarkdownConverter
from backend.converters.image_converter import ImageConverter
from backend.converters.text_converter import TextConverter

# Colors
COLORS = {
    'bg': '#0f172a',
    'sidebar': '#1e293b',
    'card': '#1e293b',
    'card_hover': '#334155',
    'primary': '#6366f1',
    'primary_hover': '#4f46e5',
    'text': '#f8fafc',
    'text_secondary': '#94a3b8',
    'border': '#334155',
}

# Format config
FORMATS = {
    'pdf': {'name': 'PDF', 'icon': '📄', 'to': ['docx', 'txt', 'md', 'png', 'jpg']},
    'docx': {'name': 'Word', 'icon': '📝', 'to': ['pdf', 'txt', 'md']},
    'md': {'name': 'Markdown', 'icon': '📑', 'to': ['pdf', 'docx', 'txt', 'html']},
    'txt': {'name': 'Text', 'icon': '📃', 'to': ['pdf', 'docx', 'md']},
    'png': {'name': 'PNG', 'icon': '🖼️', 'to': ['pdf', 'jpg', 'webp', 'bmp']},
    'jpg': {'name': 'JPG', 'icon': '🖼️', 'to': ['pdf', 'png', 'webp', 'bmp']},
    'jpeg': {'name': 'JPEG', 'icon': '🖼️', 'to': ['pdf', 'png', 'webp', 'bmp']},
    'webp': {'name': 'WebP', 'icon': '🖼️', 'to': ['pdf', 'png', 'jpg', 'bmp']},
    'bmp': {'name': 'BMP', 'icon': '🖼️', 'to': ['pdf', 'png', 'jpg', 'webp']},
    'html': {'name': 'HTML', 'icon': '🌐', 'to': ['pdf', 'md']}
}

ctk.set_appearance_mode("dark")


class FileConverterPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("File Converter Pro")
        self.geometry("900x700")
        self.minsize(800, 600)
        self.configure(fg_color=COLORS['bg'])
        
        self.selected_file = None
        self.target_format = None
        self.output_dir = Path(__file__).parent / "converted"
        self.output_dir.mkdir(exist_ok=True)
        
        self.center_window()
        self.create_ui()
        
    def center_window(self):
        self.update_idletasks()
        w, h = 900, 700
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')
        
    def create_ui(self):
        # Main container
        main = ctk.CTkFrame(self, fg_color=COLORS['bg'])
        main.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Sidebar
        self.create_sidebar(main)
        
        # Content area
        content = ctk.CTkFrame(main, fg_color=COLORS['bg'])
        content.pack(side="left", fill="both", expand=True, padx=25, pady=20)
        
        # Header with title and credit
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        # Title on left
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(title_frame, text="File Converter Pro", 
                    font=ctk.CTkFont(size=26, weight="bold"),
                    text_color=COLORS['text']).pack(anchor="w")
        
        ctk.CTkLabel(title_frame, text="Convert between PDF, Word, Images & more",
                    font=ctk.CTkFont(size=13),
                    text_color=COLORS['text_secondary']).pack(anchor="w", pady=(5, 0))
        
        # Built by credit on right
        ctk.CTkLabel(header, text="Built by: Dequavious", 
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text_secondary']).pack(side="right", pady=(10, 0))
        
        # Main content frame
        self.main_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)
        
        self.show_upload_screen()
        
    def create_sidebar(self, parent):
        """Create left sidebar - just navigation, no logo"""
        sidebar = ctk.CTkFrame(parent, fg_color=COLORS['sidebar'], 
                              width=70, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # Center container
        container = ctk.CTkFrame(sidebar, fg_color="transparent", width=70)
        container.pack(fill="y", expand=True)
        container.pack_propagate(False)
        
        # Navigation icon only (no logo)
        nav_frame = ctk.CTkFrame(container, fg_color="transparent", width=70, height=80)
        nav_frame.pack(pady=(40, 0))
        nav_frame.pack_propagate(False)
        
        btn = ctk.CTkButton(nav_frame, text="📁", font=ctk.CTkFont(size=22),
                           width=45, height=45, corner_radius=10,
                           fg_color=COLORS['primary'],
                           hover_color=COLORS['card_hover'])
        btn.place(relx=0.5, rely=0.5, anchor="center")
        
        # Version at bottom
        version_frame = ctk.CTkFrame(container, fg_color="transparent", width=70, height=40)
        version_frame.pack(side="bottom", pady=20)
        version_frame.pack_propagate(False)
        
        ctk.CTkLabel(version_frame, text="v1.0", font=ctk.CTkFont(size=10),
                    text_color=COLORS['text_secondary']).place(relx=0.5, rely=0.5, anchor="center")
        
    def show_upload_screen(self):
        """Show initial upload screen with 🔄 icon"""
        for w in self.main_frame.winfo_children():
            w.destroy()
            
        # Upload card
        card = ctk.CTkFrame(self.main_frame, fg_color=COLORS['card'], 
                           corner_radius=16, border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Center content
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.place(relx=0.5, rely=0.5, anchor="center")
        
        # 🔄 Icon in a circle
        icon_bg = ctk.CTkFrame(content, fg_color=COLORS['card_hover'], 
                              corner_radius=50, width=100, height=100)
        icon_bg.pack(pady=(0, 25))
        icon_bg.pack_propagate(False)
        
        ctk.CTkLabel(icon_bg, text="🔄", font=ctk.CTkFont(size=50)).place(
            relx=0.5, rely=0.5, anchor="center")
        
        # Title
        ctk.CTkLabel(content, text="Drop your files here",
                    font=ctk.CTkFont(size=22, weight="bold"),
                    text_color=COLORS['text']).pack()
        
        ctk.CTkLabel(content, text="or click to browse from your computer",
                    font=ctk.CTkFont(size=13),
                    text_color=COLORS['text_secondary']).pack(pady=(8, 25))
        
        # Format chips
        chips = ctk.CTkFrame(content, fg_color="transparent")
        chips.pack(pady=(0, 25))
        
        for text in ["PDF", "Word", "Markdown", "Images", "Text"]:
            ctk.CTkLabel(chips, text=text, font=ctk.CTkFont(size=11),
                        fg_color=COLORS['card_hover'], corner_radius=15,
                        padx=12, pady=5).pack(side="left", padx=4)
        
        # Browse button
        ctk.CTkButton(content, text="Browse Files", width=170, height=45,
                     corner_radius=10, fg_color=COLORS['primary'],
                     hover_color=COLORS['primary_hover'],
                     command=self.browse_file).pack()
        
    def browse_file(self):
        """Browse for file"""
        filetypes = [
            ("All Supported", "*.pdf *.docx *.md *.txt *.png *.jpg *.jpeg *.webp *.bmp *.html"),
            ("PDF", "*.pdf"), ("Word", "*.docx"), ("Markdown", "*.md"),
            ("Text", "*.txt"), ("Images", "*.png *.jpg *.jpeg *.webp *.bmp"),
            ("HTML", "*.html"), ("All Files", "*.*")
        ]
        
        path = filedialog.askopenfilename(title="Select a file", filetypes=filetypes)
        if path:
            ext = Path(path).suffix.lower().lstrip('.')
            if ext in FORMATS:
                self.selected_file = {
                    'path': path,
                    'name': Path(path).name,
                    'ext': ext,
                    'size': Path(path).stat().st_size
                }
                self.show_convert_screen()
            else:
                messagebox.showerror("Error", f".{ext} not supported")
                
    def show_convert_screen(self):
        """Show file and format selection"""
        for w in self.main_frame.winfo_children():
            w.destroy()
            
        # File info card
        file_card = ctk.CTkFrame(self.main_frame, fg_color=COLORS['card'],
                                corner_radius=12, border_width=1, border_color=COLORS['border'])
        file_card.pack(fill="x", padx=10, pady=(0, 15))
        
        header = ctk.CTkFrame(file_card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=20)
        
        ext = self.selected_file['ext']
        cfg = FORMATS[ext]
        
        # File icon
        icon_bg = ctk.CTkFrame(header, fg_color=COLORS['primary'], 
                              corner_radius=10, width=50, height=50)
        icon_bg.pack(side="left")
        icon_bg.pack_propagate(False)
        ctk.CTkLabel(icon_bg, text=cfg['icon'], font=ctk.CTkFont(size=22)).place(
            relx=0.5, rely=0.5, anchor="center")
        
        # File info
        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side="left", padx=(15, 0), fill="y")
        
        ctk.CTkLabel(info, text=self.selected_file['name'],
                    font=ctk.CTkFont(size=15, weight="bold"),
                    text_color=COLORS['text']).pack(anchor="w")
        
        size_kb = self.selected_file['size'] / 1024
        ctk.CTkLabel(info, text=f"{size_kb:.1f} KB • {cfg['name']}",
                    font=ctk.CTkFont(size=12),
                    text_color=COLORS['text_secondary']).pack(anchor="w")
        
        # Remove button
        ctk.CTkButton(header, text="✕", width=35, height=35, corner_radius=17,
                     fg_color="transparent", hover_color="#ef4444",
                     command=self.show_upload_screen).pack(side="right")
        
        # Format selection card
        fmt_card = ctk.CTkFrame(self.main_frame, fg_color=COLORS['card'],
                               corner_radius=12, border_width=1, border_color=COLORS['border'])
        fmt_card.pack(fill="both", expand=True, padx=10, pady=(0, 15))
        
        ctk.CTkLabel(fmt_card, text="Convert to",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=COLORS['text']).pack(anchor="w", padx=20, pady=(20, 15))
        
        # Format buttons
        available = FORMATS[ext]['to']
        self.format_buttons = {}
        
        btn_container = ctk.CTkFrame(fmt_card, fg_color="transparent")
        btn_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        for i in range(0, len(available), 3):
            row_frame = ctk.CTkFrame(btn_container, fg_color="transparent")
            row_frame.pack(fill="x", pady=5)
            
            row_formats = available[i:i+3]
            for fmt in row_formats:
                fmt_cfg = FORMATS.get(fmt, {})
                
                btn = ctk.CTkButton(row_frame, 
                                   text=f"{fmt_cfg.get('icon', '📄')}  {fmt_cfg.get('name', fmt.upper())}",
                                   height=50, corner_radius=10,
                                   fg_color=COLORS['card_hover'],
                                   hover_color=COLORS['primary'],
                                   command=lambda f=fmt: self.select_format(f))
                btn.pack(side="left", expand=True, fill="x", padx=5)
                self.format_buttons[fmt] = btn
        
        # Convert button
        self.convert_btn = ctk.CTkButton(fmt_card, text="Convert File →", height=50,
                                        corner_radius=10, fg_color=COLORS['primary'],
                                        state="disabled", command=self.convert)
        self.convert_btn.pack(fill="x", padx=20, pady=(10, 20))
        
    def select_format(self, fmt):
        """Handle format selection"""
        self.target_format = fmt
        
        for f, btn in self.format_buttons.items():
            if f == fmt:
                btn.configure(fg_color=COLORS['primary'])
            else:
                btn.configure(fg_color=COLORS['card_hover'])
                
        self.convert_btn.configure(state="normal")
        
    def convert(self):
        """Start conversion"""
        if not self.selected_file or not self.target_format:
            return
            
        self.convert_btn.configure(state="disabled", text="Converting...")
        
        thread = threading.Thread(target=self.do_convert)
        thread.start()
        
    def do_convert(self):
        """Perform conversion"""
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
                
            if converter and converter.convert(input_path, output_path, target):
                self.after(0, lambda: self.conversion_done(output_path))
            else:
                self.after(0, self.conversion_failed)
                
        except Exception as e:
            print(f"Error: {e}")
            self.after(0, lambda: self.conversion_failed(str(e)))
            
    def conversion_done(self, path):
        """Show success"""
        name = Path(path).name
        self.convert_btn.configure(state="normal", text="Convert File →")
        
        if messagebox.askyesno("Success!", f"Saved: {name}\n\nOpen folder?"):
            import subprocess
            subprocess.run(['explorer', str(self.output_dir)])
            
        self.show_upload_screen()
        
    def conversion_failed(self, error=""):
        """Show error"""
        self.convert_btn.configure(state="normal", text="Convert File →")
        messagebox.showerror("Error", f"Failed.\n{error[:100] if error else ''}")


if __name__ == "__main__":
    app = FileConverterPro()
    app.mainloop()
