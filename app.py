#!/usr/bin/env python3
"""
File Converter Pro - Professional Desktop Application
Modern, sleek UI with professional design
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import customtkinter as ctk
from PIL import Image, ImageDraw

# Add backend to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from backend.converters.pdf_converter import PDFConverter
from backend.converters.word_converter import WordConverter
from backend.converters.markdown_converter import MarkdownConverter
from backend.converters.image_converter import ImageConverter
from backend.converters.text_converter import TextConverter

# Modern Color Palette
COLORS = {
    'primary': '#6366F1',      # Indigo
    'primary_dark': '#4F46E5', # Darker Indigo
    'primary_light': '#818CF8', # Light Indigo
    'secondary': '#10B981',    # Emerald
    'accent': '#F59E0B',       # Amber
    'background': '#0F172A',   # Dark Slate
    'surface': '#1E293B',      # Slate 800
    'surface_light': '#334155', # Slate 700
    'text': '#F8FAFC',         # White
    'text_secondary': '#94A3B8', # Slate 400
    'border': '#475569',       # Slate 600
    'success': '#22C55E',
    'error': '#EF4444',
}

# Format configuration with icons and colors
FORMAT_CONFIG = {
    'pdf': {'name': 'PDF', 'icon': '📄', 'color': '#EF4444', 'desc': 'Portable Document'},
    'docx': {'name': 'Word', 'icon': '📝', 'color': '#3B82F6', 'desc': 'Microsoft Word'},
    'md': {'name': 'Markdown', 'icon': '📑', 'color': '#8B5CF6', 'desc': 'Markdown Doc'},
    'txt': {'name': 'Text', 'icon': '📃', 'color': '#6B7280', 'desc': 'Plain Text'},
    'png': {'name': 'PNG', 'icon': '🖼️', 'color': '#10B981', 'desc': 'PNG Image'},
    'jpg': {'name': 'JPG', 'icon': '🖼️', 'color': '#F59E0B', 'desc': 'JPEG Image'},
    'jpeg': {'name': 'JPEG', 'icon': '🖼️', 'color': '#F59E0B', 'desc': 'JPEG Image'},
    'webp': {'name': 'WebP', 'icon': '🖼️', 'color': '#EC4899', 'desc': 'WebP Image'},
    'bmp': {'name': 'BMP', 'icon': '🖼️', 'color': '#14B8A6', 'desc': 'BMP Image'},
    'html': {'name': 'HTML', 'icon': '🌐', 'color': '#F97316', 'desc': 'HTML Page'}
}

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ModernButton(ctk.CTkButton):
    """Custom modern button with hover effects"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            corner_radius=12,
            border_width=0,
            hover=True,
        )


class FileConverterPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("File Converter Pro")
        self.geometry("1000x800")
        self.minsize(900, 700)
        self.configure(fg_color=COLORS['background'])
        
        # Center window
        self.center_window()
        
        # State
        self.selected_file = None
        self.target_format = None
        self.is_converting = False
        
        # Output directory
        self.output_dir = BASE_DIR / "converted"
        self.output_dir.mkdir(exist_ok=True)
        
        # Build UI
        self.create_ui()
        
    def center_window(self):
        """Center window on screen"""
        self.update_idletasks()
        width = 1000
        height = 800
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
    def create_ui(self):
        """Create the main user interface"""
        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color=COLORS['background'])
        self.main_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.content_frame = ctk.CTkFrame(
            self.main_container, 
            fg_color=COLORS['background'],
            corner_radius=0
        )
        self.content_frame.pack(side="left", fill="both", expand=True, padx=30, pady=20)
        
        # Header
        self.create_header()
        
        # Main area - changes based on state
        self.main_area = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.main_area.pack(fill="both", expand=True, pady=(20, 0))
        
        # Show initial upload screen
        self.show_upload_screen()
        
    def create_sidebar(self):
        """Create left sidebar with branding"""
        sidebar = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS['surface'],
            width=80,
            corner_radius=0
        )
        sidebar.pack(side="left", fill="y", padx=0, pady=0)
        sidebar.pack_propagate(False)
        
        # Logo at top
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent", height=100)
        logo_frame.pack(fill="x", pady=(30, 0))
        
        logo = ctk.CTkLabel(
            logo_frame,
            text="🔄",
            font=ctk.CTkFont(size=36),
            fg_color=COLORS['primary'],
            corner_radius=15,
            width=50,
            height=50
        )
        logo.place(relx=0.5, rely=0.5, anchor="center")
        
        # Navigation items
        nav_items = [
            ("📁", "Convert", True),
            ("⚙️", "Settings", False),
            ("❓", "Help", False),
        ]
        
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", pady=(40, 0))
        
        for icon, label, active in nav_items:
            btn = ctk.CTkButton(
                nav_frame,
                text=icon,
                font=ctk.CTkFont(size=24),
                width=50,
                height=50,
                corner_radius=12,
                fg_color=COLORS['primary'] if active else "transparent",
                hover_color=COLORS['surface_light'],
                command=lambda l=label: self.nav_clicked(l)
            )
            btn.pack(pady=8)
            
        # Version at bottom
        version = ctk.CTkLabel(
            sidebar,
            text="v1.0",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        )
        version.pack(side="bottom", pady=20)
        
    def create_header(self):
        """Create header with title"""
        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        
        # Title
        title = ctk.CTkLabel(
            header,
            text="File Converter Pro",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color=COLORS['text']
        )
        title.pack(side="left")
        
        # Subtitle
        subtitle = ctk.CTkLabel(
            header,
            text="Convert between PDF, Word, Images & more",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=COLORS['text_secondary']
        )
        subtitle.pack(side="left", padx=(15, 0), pady=(8, 0))
        
    def show_upload_screen(self):
        """Show the upload/drag-drop screen"""
        # Clear main area
        for widget in self.main_area.winfo_children():
            widget.destroy()
            
        # Upload card
        self.upload_card = ctk.CTkFrame(
            self.main_area,
            fg_color=COLORS['surface'],
            corner_radius=24,
            border_width=2,
            border_color=COLORS['border']
        )
        self.upload_card.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Bind drag events
        self.upload_card.bind("<Enter>", lambda e: self.upload_card.configure(border_color=COLORS['primary']))
        self.upload_card.bind("<Leave>", lambda e: self.upload_card.configure(border_color=COLORS['border']))
        self.upload_card.bind("<Button-1>", lambda e: self.browse_file())
        
        # Content container
        content = ctk.CTkFrame(self.upload_card, fg_color="transparent")
        content.place(relx=0.5, rely=0.5, anchor="center")
        
        # Animated upload icon (using a large label)
        icon_container = ctk.CTkFrame(content, fg_color=COLORS['surface_light'], corner_radius=30, width=120, height=120)
        icon_container.pack(pady=(0, 30))
        icon_container.pack_propagate(False)
        
        self.upload_icon = ctk.CTkLabel(
            icon_container,
            text="☁️",
            font=ctk.CTkFont(size=60)
        )
        self.upload_icon.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        title = ctk.CTkLabel(
            content,
            text="Drop your files here",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=COLORS['text']
        )
        title.pack(pady=(0, 10))
        
        # Subtitle
        subtitle = ctk.CTkLabel(
            content,
            text="or click to browse from your computer",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=COLORS['text_secondary']
        )
        subtitle.pack(pady=(0, 30))
        
        # Supported formats chips
        formats_frame = ctk.CTkFrame(content, fg_color="transparent")
        formats_frame.pack(pady=(0, 30))
        
        formats = ["PDF", "Word", "Markdown", "Images", "Text"]
        for fmt in formats:
            chip = ctk.CTkLabel(
                formats_frame,
                text=fmt,
                font=ctk.CTkFont(size=11),
                fg_color=COLORS['surface_light'],
                text_color=COLORS['text_secondary'],
                corner_radius=20,
                padx=15,
                pady=6
            )
            chip.pack(side="left", padx=5)
            
        # Browse button
        browse_btn = ModernButton(
            content,
            text="Browse Files",
            width=180,
            height=50,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            command=self.browse_file
        )
        browse_btn.pack(pady=(10, 0))
        
        # Make entire card clickable
        for widget in [content, title, subtitle, icon_container]:
            widget.bind("<Button-1>", lambda e: self.browse_file())
            
    def show_file_preview(self):
        """Show file preview and conversion options"""
        # Clear main area
        for widget in self.main_area.winfo_children():
            widget.destroy()
            
        # File info card
        file_card = ctk.CTkFrame(
            self.main_area,
            fg_color=COLORS['surface'],
            corner_radius=20,
            border_width=1,
            border_color=COLORS['border']
        )
        file_card.pack(fill="x", padx=20, pady=(0, 20))
        
        # File icon and info
        file_header = ctk.CTkFrame(file_card, fg_color="transparent")
        file_header.pack(fill="x", padx=25, pady=25)
        
        ext = self.selected_file['ext']
        config = FORMAT_CONFIG.get(ext, FORMAT_CONFIG['txt'])
        
        # Icon with colored background
        icon_bg = ctk.CTkFrame(
            file_header,
            fg_color=config['color'],
            corner_radius=16,
            width=70,
            height=70
        )
        icon_bg.pack(side="left")
        icon_bg.pack_propagate(False)
        
        icon = ctk.CTkLabel(
            icon_bg,
            text=config['icon'],
            font=ctk.CTkFont(size=32)
        )
        icon.place(relx=0.5, rely=0.5, anchor="center")
        
        # File details
        info = ctk.CTkFrame(file_header, fg_color="transparent")
        info.pack(side="left", padx=(20, 0), fill="y")
        
        name = ctk.CTkLabel(
            info,
            text=self.selected_file['name'],
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLORS['text']
        )
        name.pack(anchor="w")
        
        size_kb = self.selected_file['size'] / 1024
        details = ctk.CTkLabel(
            info,
            text=f"{size_kb:.1f} KB • {config['desc']}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        details.pack(anchor="w", pady=(4, 0))
        
        # Change file button
        change_btn = ctk.CTkButton(
            file_header,
            text="✕",
            width=40,
            height=40,
            corner_radius=20,
            fg_color="transparent",
            hover_color=COLORS['error'],
            text_color=COLORS['text_secondary'],
            font=ctk.CTkFont(size=16),
            command=self.reset_ui
        )
        change_btn.pack(side="right")
        
        # Conversion options
        self.show_conversion_options()
        
    def show_conversion_options(self):
        """Show format conversion options"""
        # Options card
        options_card = ctk.CTkFrame(
            self.main_area,
            fg_color=COLORS['surface'],
            corner_radius=20,
            border_width=1,
            border_color=COLORS['border']
        )
        options_card.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Section title
        title = ctk.CTkLabel(
            options_card,
            text="Convert to",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLORS['text']
        )
        title.pack(anchor="w", padx=25, pady=(25, 20))
        
        # Format buttons grid
        formats_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        formats_frame.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        
        ext = self.selected_file['ext']
        available_formats = FORMAT_CONFIG.get(ext, {}).get('converts_to', [])
        
        self.format_buttons = {}
        row, col = 0, 0
        
        for i, fmt in enumerate(available_formats):
            config = FORMAT_CONFIG.get(fmt, {})
            
            # Format card
            card = ctk.CTkFrame(
                formats_frame,
                fg_color=COLORS['surface_light'],
                corner_radius=16,
                border_width=2,
                border_color="transparent",
                width=150,
                height=120
            )
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            card.grid_propagate(False)
            card.bind("<Enter>", lambda e, c=card: c.configure(border_color=COLORS['primary']))
            card.bind("<Leave>", lambda e, c=card, f=fmt: c.configure(
                border_color=COLORS['primary'] if self.target_format == f else "transparent"
            ))
            card.bind("<Button-1>", lambda e, f=fmt: self.select_format(f))
            
            # Icon
            icon = ctk.CTkLabel(
                card,
                text=config.get('icon', '📄'),
                font=ctk.CTkFont(size=40)
            )
            icon.place(relx=0.5, y=35, anchor="center")
            icon.bind("<Button-1>", lambda e, f=fmt: self.select_format(f))
            
            # Name
            name = ctk.CTkLabel(
                card,
                text=config.get('name', fmt.upper()),
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=COLORS['text']
            )
            name.place(relx=0.5, y=75, anchor="center")
            name.bind("<Button-1>", lambda e, f=fmt: self.select_format(f))
            
            self.format_buttons[fmt] = card
            
            col += 1
            if col > 3:
                col = 0
                row += 1
                
        # Configure grid
        for c in range(4):
            formats_frame.grid_columnconfigure(c, weight=1)
            
        # Convert button at bottom
        self.convert_btn = ModernButton(
            options_card,
            text="Convert File →",
            height=55,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            state="disabled",
            command=self.start_conversion
        )
        self.convert_btn.pack(fill="x", padx=25, pady=(10, 25))
        
    def show_progress(self):
        """Show conversion progress"""
        for widget in self.main_area.winfo_children():
            widget.destroy()
            
        # Progress card
        card = ctk.CTkFrame(
            self.main_area,
            fg_color=COLORS['surface'],
            corner_radius=24
        )
        card.pack(fill="both", expand=True, padx=20, pady=20)
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.place(relx=0.5, rely=0.5, anchor="center")
        
        # Animated spinner (using rotating label)
        self.spinner = ctk.CTkLabel(
            content,
            text="⏳",
            font=ctk.CTkFont(size=80)
        )
        self.spinner.pack(pady=(0, 30))
        
        # Start spinner animation
        self.animate_spinner()
        
        # Status
        self.status_label = ctk.CTkLabel(
            content,
            text="Converting your file...",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=COLORS['text']
        )
        self.status_label.pack(pady=(0, 10))
        
        # Subtitle
        subtitle = ctk.CTkLabel(
            content,
            text="This may take a few seconds",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_secondary']
        )
        subtitle.pack()
        
    def animate_spinner(self):
        """Animate the spinner"""
        if hasattr(self, 'spinner') and self.spinner.winfo_exists():
            spins = ["⏳", "⌛", "⏳", "⌛"]
            current = self.spinner.cget("text")
            next_spin = spins[(spins.index(current) + 1) % len(spins)]
            self.spinner.configure(text=next_spin)
            self.after(500, self.animate_spinner)
        
    def show_success(self, output_path):
        """Show success screen"""
        for widget in self.main_area.winfo_children():
            widget.destroy()
            
        card = ctk.CTkFrame(
            self.main_area,
            fg_color=COLORS['surface'],
            corner_radius=24
        )
        card.pack(fill="both", expand=True, padx=20, pady=20)
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.place(relx=0.5, rely=0.5, anchor="center")
        
        # Success icon
        success_icon = ctk.CTkLabel(
            content,
            text="✅",
            font=ctk.CTkFont(size=80)
        )
        success_icon.pack(pady=(0, 20))
        
        # Success text
        title = ctk.CTkLabel(
            content,
            text="Conversion Complete!",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=COLORS['success']
        )
        title.pack(pady=(0, 10))
        
        # Filename
        filename = ctk.CTkLabel(
            content,
            text=Path(output_path).name,
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_secondary']
        )
        filename.pack(pady=(0, 30))
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack()
        
        open_btn = ModernButton(
            btn_frame,
            text="📁 Open Folder",
            width=150,
            height=45,
            fg_color=COLORS['surface_light'],
            hover_color=COLORS['border'],
            command=self.open_output_folder
        )
        open_btn.pack(side="left", padx=5)
        
        again_btn = ModernButton(
            btn_frame,
            text="Convert Another",
            width=150,
            height=45,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            command=self.reset_ui
        )
        again_btn.pack(side="left", padx=5)
        
    def browse_file(self):
        """Open file browser"""
        filetypes = [
            ("All Supported", "*.pdf *.docx *.md *.txt *.png *.jpg *.jpeg *.webp *.bmp *.html"),
            ("PDF", "*.pdf"), ("Word", "*.docx"), ("Markdown", "*.md"),
            ("Text", "*.txt"), ("Images", "*.png *.jpg *.jpeg *.webp *.bmp"),
            ("HTML", "*.html"), ("All Files", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(title="Select a file", filetypes=filetypes)
        if filepath:
            self.process_file(filepath)
            
    def process_file(self, filepath):
        """Process selected file"""
        path = Path(filepath)
        ext = path.suffix.lower().lstrip('.')
        
        if ext not in FORMAT_CONFIG:
            messagebox.showerror("Unsupported Format", 
                f".{ext} files are not supported.\n\nSupported: PDF, DOCX, MD, TXT, PNG, JPG, WEBP, BMP, HTML")
            return
            
        self.selected_file = {
            'path': str(path),
            'name': path.name,
            'ext': ext,
            'size': path.stat().st_size
        }
        
        self.show_file_preview()
        
    def select_format(self, fmt):
        """Select target format"""
        self.target_format = fmt
        
        # Update UI
        for f, card in self.format_buttons.items():
            if f == fmt:
                card.configure(border_color=COLORS['primary'], fg_color=COLORS['surface'])
            else:
                card.configure(border_color="transparent", fg_color=COLORS['surface_light'])
                
        self.convert_btn.configure(state="normal")
        
    def start_conversion(self):
        """Start conversion"""
        if not self.selected_file or not self.target_format:
            return
            
        self.is_converting = True
        self.show_progress()
        
        thread = threading.Thread(target=self.convert_file)
        thread.daemon = True
        thread.start()
        
    def convert_file(self):
        """Perform conversion"""
        try:
            input_path = self.selected_file['path']
            target = self.target_format
            
            input_path_obj = Path(input_path)
            output_name = f"{input_path_obj.stem}_converted.{target}"
            output_path = str(self.output_dir / output_name)
            
            # Get converter
            ext = self.selected_file['ext']
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
                raise Exception("No converter available")
                
            success = converter.convert(input_path, output_path, target)
            
            if success:
                self.after(0, lambda: self.show_success(output_path))
            else:
                self.after(0, self.show_error)
                
        except Exception as e:
            print(f"Error: {e}")
            self.after(0, lambda: self.show_error(str(e)))
            
    def show_error(self, error=""):
        """Show error message"""
        messagebox.showerror("Conversion Failed", 
            f"Sorry, the conversion failed.\n\n{error if error else 'Please try again.'}")
        self.reset_ui()
        
    def reset_ui(self):
        """Reset to initial state"""
        self.selected_file = None
        self.target_format = None
        self.is_converting = False
        self.show_upload_screen()
        
    def open_output_folder(self):
        """Open output folder"""
        import subprocess
        path = str(self.output_dir)
        
        if sys.platform == 'win32':
            subprocess.run(['explorer', path])
        elif sys.platform == 'darwin':
            subprocess.run(['open', path])
        else:
            subprocess.run(['xdg-open', path])
            
    def nav_clicked(self, label):
        """Handle navigation click"""
        if label == "Convert":
            self.reset_ui()
        elif label == "Settings":
            self.show_settings()
            
    def show_settings(self):
        """Show settings dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Settings")
        dialog.geometry("400x300")
        dialog.configure(fg_color=COLORS['surface'])
        
        # Center
        dialog.transient(self)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 150
        dialog.geometry(f"+{x}+{y}")
        
        title = ctk.CTkLabel(
            dialog,
            text="Settings",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        )
        title.pack(pady=20)
        
        info = ctk.CTkLabel(
            dialog,
            text="File Converter Pro v1.0\nConvert between document formats",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        info.pack(pady=20)
        
        btn = ModernButton(dialog, text="Close", command=dialog.destroy)
        btn.pack(pady=20)


def main():
    app = FileConverterPro()
    app.mainloop()


if __name__ == "__main__":
    main()
