#!/usr/bin/env python3
"""
File Converter Pro - Advanced UI
Dark sleek Discord/Spotify-inspired theme with sidebar navigation.
Complete rewrite for v2.0.
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk

from config import FORMATS, VERSION, APP_NAME, AUTHOR, get_filetypes, get_formats_by_category
from backend.converter_registry import get_converter, get_json_converter, is_supported
from backend.converters.base_converter import ConversionError
from backend.batch_converter import BatchConverter, BatchItem
from backend.history import ConversionHistory
from backend.settings import Settings
from utils.platform_utils import open_folder, open_file
from utils.file_utils import get_file_size_str

# Drag-and-drop support
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# Dark sleek color palette
C = {
    'bg':            '#0f0f0f',
    'bg2':           '#1a1a2e',
    'bg_card':       '#16213e',
    'bg_hover':      '#1e2a4a',
    'bg_input':      '#0a0a1a',
    'accent':        '#7c3aed',
    'accent_hover':  '#6d28d9',
    'accent_glow':   '#8b5cf6',
    'success':       '#10b981',
    'error':         '#ef4444',
    'warning':       '#f59e0b',
    'text':          '#f8fafc',
    'text2':         '#94a3b8',
    'text_muted':    '#475569',
    'border':        '#1e293b',
    'border_active': '#7c3aed',
    'divider':       '#1e293b',
    'sidebar':       '#1a1a2e',
    'sidebar_active':'#7c3aed',
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class FileConverterPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("960x680")
        self.minsize(860, 620)
        self.configure(fg_color=C['bg'])

        self.selected_file = None
        self.target_format = None
        self.output_dir = Path(__file__).parent / "converted"
        self.output_dir.mkdir(exist_ok=True)

        self.cancel_event = threading.Event()
        self.killed = False
        self.conversion_thread = None
        self.batch_converter = None

        self.history = ConversionHistory()
        self.settings = Settings()

        self.current_page = "convert"

        self.center_window()
        self._build_layout()
        self._setup_dnd()
        self.show_page("convert")

    def center_window(self):
        self.update_idletasks()
        w, h = 960, 680
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')

    def _setup_dnd(self):
        if not DND_AVAILABLE:
            return
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<DropEnter>>', self._dnd_enter)
            self.dnd_bind('<<DropLeave>>', self._dnd_leave)
            self.dnd_bind('<<Drop>>', self._dnd_drop)
        except Exception:
            pass

    def _dnd_enter(self, event):
        if hasattr(self, 'drop_overlay'):
            self.drop_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _dnd_leave(self, event):
        if hasattr(self, 'drop_overlay'):
            self.drop_overlay.place_forget()

    def _dnd_drop(self, event):
        if hasattr(self, 'drop_overlay'):
            self.drop_overlay.place_forget()
        raw = event.data
        files = []
        if '{' in raw:
            import re
            files = re.findall(r'\{([^}]+)\}', raw)
            rest = re.sub(r'\{[^}]+\}', '', raw).strip()
            if rest:
                files.extend(rest.split())
        else:
            files = raw.split()

        if self.current_page == "batch" and files:
            for f in files:
                self._batch_add_file(f)
        elif files:
            self._load_file(files[0])

    # ── Layout ──────────────────────────────────────────────

    def _build_layout(self):
        # Drop overlay
        self.drop_overlay = ctk.CTkFrame(self, fg_color=("#222244", "#222244"),
                                          corner_radius=0)
        drop_lbl = ctk.CTkLabel(self.drop_overlay, text="Drop files here",
                                font=ctk.CTkFont(size=28, weight="bold"),
                                text_color=C['accent_glow'])
        drop_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Main layout: sidebar + content
        self.main_frame = ctk.CTkFrame(self, fg_color=C['bg'], corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)

        self._build_sidebar()

        self.content = ctk.CTkFrame(self.main_frame, fg_color=C['bg'], corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # Header
        header = ctk.CTkFrame(self.content, fg_color="transparent", height=70)
        header.pack(fill="x", padx=30, pady=(20, 0))
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="y")
        ctk.CTkLabel(title_frame, text=APP_NAME,
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=C['text']).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Convert anything. Fast.",
                     font=ctk.CTkFont(size=13),
                     text_color=C['text2']).pack(anchor="w", pady=(2, 0))

        credit = ctk.CTkLabel(header, text=f"Built by: {AUTHOR}",
                              font=ctk.CTkFont(size=11),
                              text_color=C['text_muted'])
        credit.pack(side="right", anchor="ne", pady=(5, 0))

        # Page container
        self.page_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_frame.pack(fill="both", expand=True, padx=30, pady=(15, 20))

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self.main_frame, fg_color=C['sidebar'],
                               width=72, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo at top
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent", height=60)
        logo_frame.pack(fill="x", pady=(15, 20))
        logo_frame.pack_propagate(False)
        ctk.CTkLabel(logo_frame, text="FC",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=C['accent_glow']).place(relx=0.5, rely=0.5, anchor="center")

        # Nav items
        self.nav_buttons = {}
        nav_items = [
            ("convert", "Convert"),
            ("batch",   "Batch"),
            ("history", "History"),
            ("settings","Settings"),
        ]

        for page_id, label in nav_items:
            btn_frame = ctk.CTkFrame(sidebar, fg_color="transparent", height=56)
            btn_frame.pack(fill="x", pady=2)
            btn_frame.pack_propagate(False)

            indicator = ctk.CTkFrame(btn_frame, fg_color="transparent",
                                     width=4, corner_radius=2)
            indicator.pack(side="left", fill="y", padx=(0, 0))

            btn = ctk.CTkButton(btn_frame, text=label,
                               font=ctk.CTkFont(size=10),
                               width=68, height=48, corner_radius=10,
                               fg_color="transparent",
                               hover_color=C['bg_hover'],
                               text_color=C['text2'],
                               command=lambda p=page_id: self.show_page(p))
            btn.pack(expand=True)

            self.nav_buttons[page_id] = {'btn': btn, 'indicator': indicator}

        # Spacer
        ctk.CTkFrame(sidebar, fg_color="transparent").pack(fill="both", expand=True)

        # Version at bottom
        ctk.CTkLabel(sidebar, text=f"v{VERSION}",
                     font=ctk.CTkFont(size=9),
                     text_color=C['text_muted']).pack(pady=(0, 15))

    def show_page(self, page_id):
        self.current_page = page_id

        # Update nav indicators
        for pid, widgets in self.nav_buttons.items():
            if pid == page_id:
                widgets['indicator'].configure(fg_color=C['accent'])
                widgets['btn'].configure(text_color=C['text'], fg_color=C['bg_hover'])
            else:
                widgets['indicator'].configure(fg_color="transparent")
                widgets['btn'].configure(text_color=C['text2'], fg_color="transparent")

        # Clear page
        for w in self.page_frame.winfo_children():
            w.destroy()

        # Show page
        pages = {
            "convert":  self._page_convert,
            "batch":    self._page_batch,
            "history":  self._page_history,
            "settings": self._page_settings,
        }
        pages.get(page_id, self._page_convert)()

    # ── Convert Page ────────────────────────────────────────

    def _page_convert(self):
        if self.selected_file:
            self._show_convert_screen()
        else:
            self._show_upload_screen()

    def _show_upload_screen(self):
        card = ctk.CTkFrame(self.page_frame, fg_color=C['bg_card'],
                            corner_radius=16, border_width=2,
                            border_color=C['border'])
        card.pack(fill="both", expand=True)

        center = ctk.CTkFrame(card, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # Icon
        icon_bg = ctk.CTkFrame(center, fg_color=C['bg_hover'],
                               corner_radius=25, width=100, height=100)
        icon_bg.pack(pady=(0, 25))
        icon_bg.pack_propagate(False)
        ctk.CTkLabel(icon_bg, text="", font=ctk.CTkFont(size=44)).place(
            relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(center, text="Drop your files here",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=C['text']).pack()
        ctk.CTkLabel(center, text="or click to browse from your computer",
                     font=ctk.CTkFont(size=13),
                     text_color=C['text2']).pack(pady=(8, 25))

        # Format chips
        chips = ctk.CTkFrame(center, fg_color="transparent")
        chips.pack(pady=(0, 25))
        categories = ["Documents", "Images", "Audio", "Video", "Data"]
        for cat in categories:
            ctk.CTkLabel(chips, text=cat, font=ctk.CTkFont(size=11),
                         fg_color=C['bg_hover'], corner_radius=15,
                         text_color=C['text2'],
                         padx=14, pady=5).pack(side="left", padx=4)

        ctk.CTkButton(center, text="Browse Files", width=180, height=48,
                      corner_radius=12, fg_color=C['accent'],
                      hover_color=C['accent_hover'],
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._browse_single).pack()

    def _show_convert_screen(self):
        f = self.selected_file
        ext = f['ext']
        cfg = FORMATS.get(ext, {'name': ext.upper(), 'icon': ''})

        # File card
        file_card = ctk.CTkFrame(self.page_frame, fg_color=C['bg_card'],
                                 corner_radius=12, border_width=1,
                                 border_color=C['border'], height=80)
        file_card.pack(fill="x", pady=(0, 15))
        file_card.pack_propagate(False)

        inner = ctk.CTkFrame(file_card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=15)

        icon_bg = ctk.CTkFrame(inner, fg_color=C['accent'],
                               corner_radius=10, width=48, height=48)
        icon_bg.pack(side="left")
        icon_bg.pack_propagate(False)
        ctk.CTkLabel(icon_bg, text=cfg.get('icon', ''),
                     font=ctk.CTkFont(size=20)).place(relx=0.5, rely=0.5, anchor="center")

        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", padx=(15, 0), fill="y")
        ctk.CTkLabel(info, text=f['name'],
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C['text']).pack(anchor="w")
        ctk.CTkLabel(info, text=f"{get_file_size_str(f['size'])}  |  {cfg['name']}",
                     font=ctk.CTkFont(size=12),
                     text_color=C['text2']).pack(anchor="w")

        ctk.CTkButton(inner, text="X", width=35, height=35, corner_radius=17,
                      fg_color="transparent", hover_color=C['error'],
                      text_color=C['text2'],
                      font=ctk.CTkFont(size=14),
                      command=self._clear_file).pack(side="right")

        # Format selection card
        fmt_card = ctk.CTkFrame(self.page_frame, fg_color=C['bg_card'],
                                corner_radius=12, border_width=1,
                                border_color=C['border'])
        fmt_card.pack(fill="both", expand=True, pady=(0, 15))

        ctk.CTkLabel(fmt_card, text="Convert to",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=C['text']).pack(anchor="w", padx=20, pady=(20, 12))

        btn_container = ctk.CTkFrame(fmt_card, fg_color="transparent")
        btn_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        available = FORMATS.get(ext, {}).get('to', [])
        self.format_buttons = {}

        row_frame = None
        for i, fmt in enumerate(available):
            if i % 4 == 0:
                row_frame = ctk.CTkFrame(btn_container, fg_color="transparent")
                row_frame.pack(fill="x", pady=4)

            fmt_cfg = FORMATS.get(fmt, {})
            btn = ctk.CTkButton(
                row_frame,
                text=f"{fmt_cfg.get('icon', '')}  {fmt_cfg.get('name', fmt.upper())}",
                height=46, corner_radius=10,
                fg_color=C['bg_hover'],
                hover_color=C['accent'],
                text_color=C['text2'],
                font=ctk.CTkFont(size=12),
                command=lambda fo=fmt: self._select_format(fo))
            btn.pack(side="left", expand=True, fill="x", padx=4)
            self.format_buttons[fmt] = btn

        # Bottom buttons
        bottom = ctk.CTkFrame(self.page_frame, fg_color="transparent", height=55)
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        self.convert_btn = ctk.CTkButton(
            bottom, text="Convert File", height=50,
            corner_radius=12, fg_color=C['accent'],
            hover_color=C['accent_hover'],
            font=ctk.CTkFont(size=15, weight="bold"),
            state="disabled",
            command=self._start_convert)
        self.convert_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.kill_btn = ctk.CTkButton(
            bottom, text="Kill", width=80, height=50,
            corner_radius=12, fg_color=C['error'],
            hover_color="#dc2626",
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self._kill)
        self.kill_btn.pack(side="right")

    def _select_format(self, fmt):
        self.target_format = fmt
        for f, btn in self.format_buttons.items():
            if f == fmt:
                btn.configure(fg_color=C['accent'], text_color=C['text'])
            else:
                btn.configure(fg_color=C['bg_hover'], text_color=C['text2'])
        self.convert_btn.configure(state="normal")

    def _browse_single(self):
        ft = get_filetypes()
        path = filedialog.askopenfilename(title="Select a file", filetypes=ft)
        if path:
            self._load_file(path)

    def _load_file(self, path):
        path = str(path).strip()
        ext = Path(path).suffix.lower().lstrip('.')
        if ext not in FORMATS:
            messagebox.showerror("Error", f".{ext} not supported")
            return
        self.selected_file = {
            'path': path, 'name': Path(path).name,
            'ext': ext, 'size': Path(path).stat().st_size
        }
        self.target_format = None
        self.show_page("convert")

    def _clear_file(self):
        self.selected_file = None
        self.target_format = None
        self.show_page("convert")

    def _start_convert(self):
        if not self.selected_file or not self.target_format:
            return

        self.killed = False
        self.cancel_event.clear()

        self.convert_btn.configure(state="disabled", text="Converting...")
        self.kill_btn.configure(state="normal")

        self.conversion_thread = threading.Thread(target=self._do_convert, daemon=True)
        self.conversion_thread.start()

    def _do_convert(self):
        start = time.time()
        try:
            inp = self.selected_file['path']
            ext = self.selected_file['ext']
            tgt = self.target_format
            out_name = f"{Path(inp).stem}_converted.{tgt}"
            out_path = str(self.output_dir / out_name)

            def prog(pct, msg=""):
                if not self.killed:
                    self.after(0, lambda: self._update_convert_progress(pct, msg))

            if ext == 'json' and tgt in ('yaml', 'toml'):
                conv = get_json_converter(tgt, self.cancel_event, prog)
            else:
                conv = get_converter(ext, self.cancel_event, prog)

            if self.killed:
                return
            conv.convert(inp, out_path, tgt)
            if self.killed:
                return

            duration = time.time() - start
            self.history.add(inp, out_path, "success", duration)
            self.after(0, lambda: self._convert_done(out_path))

        except ConversionError as e:
            if not self.killed:
                self.history.add(self.selected_file['path'], "", "failed", time.time() - start)
                self.after(0, lambda: self._convert_failed(e.message))
        except Exception as e:
            if not self.killed:
                self.after(0, lambda: self._convert_failed(str(e)))

    def _update_convert_progress(self, pct, msg):
        if self.killed:
            return
        txt = f"Converting... {pct}%"
        if msg:
            txt = f"{msg} ({pct}%)"
        self.convert_btn.configure(text=txt)

    def _convert_done(self, path):
        name = Path(path).name
        self.convert_btn.configure(state="normal", text="Convert File")
        self.kill_btn.configure(state="disabled")

        # Show success dialog
        result = messagebox.askyesnocancel(
            "Success!",
            f"Converted!\n\nSaved as: {name}\n\n"
            "Yes = Open folder\nNo = Open file\nCancel = Close"
        )
        if result is True:
            open_folder(self.output_dir)
        elif result is False:
            open_file(path)

        self._clear_file()

    def _convert_failed(self, error):
        self.convert_btn.configure(state="normal", text="Convert File")
        self.kill_btn.configure(state="disabled")
        messagebox.showerror("Conversion Failed", f"{error}")

    def _kill(self):
        self.killed = True
        self.cancel_event.set()
        if self.batch_converter and self.batch_converter.is_running:
            self.batch_converter.kill()
        self.convert_btn.configure(state="normal", text="Convert File")
        self.kill_btn.configure(state="disabled")

    # ── Batch Page ──────────────────────────────────────────

    def _page_batch(self):
        header = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="Batch Conversion",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=C['text']).pack(side="left")
        ctk.CTkButton(header, text="+ Add Files", width=120, height=36,
                      corner_radius=10, fg_color=C['accent'],
                      hover_color=C['accent_hover'],
                      command=self._batch_browse).pack(side="right")

        # File list
        self.batch_list_frame = ctk.CTkScrollableFrame(
            self.page_frame, fg_color=C['bg_card'],
            corner_radius=12, border_width=1, border_color=C['border'])
        self.batch_list_frame.pack(fill="both", expand=True, pady=(0, 12))

        self.batch_items_widgets = []
        if not hasattr(self, '_batch_files'):
            self._batch_files = []

        if not self._batch_files:
            ctk.CTkLabel(self.batch_list_frame,
                         text="No files added yet.\nDrag & drop or click '+ Add Files'",
                         font=ctk.CTkFont(size=13),
                         text_color=C['text_muted']).pack(expand=True, pady=40)
        else:
            self._rebuild_batch_list()

        # Format selector + convert row
        bottom = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        bottom.pack(fill="x")

        ctk.CTkLabel(bottom, text="Convert all to:",
                     font=ctk.CTkFont(size=13),
                     text_color=C['text2']).pack(side="left", padx=(0, 10))

        all_targets = set()
        for bf in getattr(self, '_batch_files', []):
            for t in FORMATS.get(bf['ext'], {}).get('to', []):
                all_targets.add(t)
        target_list = sorted(all_targets) if all_targets else ["Select files first"]

        self.batch_format_var = ctk.StringVar(value="")
        self.batch_format_menu = ctk.CTkOptionMenu(
            bottom, values=target_list if target_list else ["---"],
            variable=self.batch_format_var,
            width=120, height=36, corner_radius=10,
            fg_color=C['bg_hover'], button_color=C['accent'],
            button_hover_color=C['accent_hover'])
        self.batch_format_menu.pack(side="left", padx=(0, 15))

        self.batch_convert_btn = ctk.CTkButton(
            bottom, text=f"Convert All ({len(getattr(self, '_batch_files', []))} files)",
            height=42, corner_radius=12,
            fg_color=C['accent'], hover_color=C['accent_hover'],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._batch_start)
        self.batch_convert_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.batch_kill_btn = ctk.CTkButton(
            bottom, text="Kill", width=70, height=42,
            corner_radius=12, fg_color=C['error'],
            hover_color="#dc2626",
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled",
            command=self._kill)
        self.batch_kill_btn.pack(side="right")

    def _rebuild_batch_list(self):
        for w in self.batch_list_frame.winfo_children():
            w.destroy()

        for i, bf in enumerate(self._batch_files):
            row = ctk.CTkFrame(self.batch_list_frame, fg_color=C['bg_hover'],
                               corner_radius=8, height=45)
            row.pack(fill="x", pady=3, padx=5)
            row.pack_propagate(False)

            icon = FORMATS.get(bf['ext'], {}).get('icon', '')
            ctk.CTkLabel(row, text=f"  {icon}  {bf['name']}",
                         font=ctk.CTkFont(size=12),
                         text_color=C['text']).pack(side="left", padx=5)

            size_str = get_file_size_str(bf['size'])
            ctk.CTkLabel(row, text=size_str,
                         font=ctk.CTkFont(size=11),
                         text_color=C['text_muted']).pack(side="left", padx=10)

            # Status indicator
            status = bf.get('status', 'pending')
            if status == 'done':
                ctk.CTkLabel(row, text="Done", text_color=C['success'],
                             font=ctk.CTkFont(size=11)).pack(side="right", padx=10)
            elif status == 'failed':
                ctk.CTkLabel(row, text="Failed", text_color=C['error'],
                             font=ctk.CTkFont(size=11)).pack(side="right", padx=10)
            elif status == 'converting':
                ctk.CTkLabel(row, text="Converting...", text_color=C['warning'],
                             font=ctk.CTkFont(size=11)).pack(side="right", padx=10)
            else:
                ctk.CTkButton(row, text="X", width=28, height=28,
                              corner_radius=14, fg_color="transparent",
                              hover_color=C['error'], text_color=C['text_muted'],
                              font=ctk.CTkFont(size=11),
                              command=lambda idx=i: self._batch_remove(idx)).pack(side="right", padx=5)

    def _batch_browse(self):
        ft = get_filetypes()
        paths = filedialog.askopenfilenames(title="Select files", filetypes=ft)
        for p in paths:
            self._batch_add_file(p)
        if paths:
            self.show_page("batch")

    def _batch_add_file(self, path):
        path = str(path).strip()
        ext = Path(path).suffix.lower().lstrip('.')
        if not is_supported(ext):
            return
        if not hasattr(self, '_batch_files'):
            self._batch_files = []
        self._batch_files.append({
            'path': path, 'name': Path(path).name,
            'ext': ext, 'size': Path(path).stat().st_size,
            'status': 'pending'
        })

    def _batch_remove(self, idx):
        if 0 <= idx < len(self._batch_files):
            self._batch_files.pop(idx)
            self.show_page("batch")

    def _batch_start(self):
        fmt = self.batch_format_var.get()
        if not fmt or not self._batch_files:
            messagebox.showwarning("Batch", "Add files and select a target format.")
            return

        self.killed = False
        self.cancel_event.clear()
        self.batch_convert_btn.configure(state="disabled", text="Converting...")
        self.batch_kill_btn.configure(state="normal")

        def on_update(idx, item):
            if idx < len(self._batch_files):
                self._batch_files[idx]['status'] = item.status
            self.after(0, lambda: self._batch_ui_update(idx, item))

        def on_done():
            self.after(0, self._batch_finished)

        self.batch_converter = BatchConverter(
            str(self.output_dir),
            on_item_update=on_update,
            on_batch_complete=on_done
        )
        self.batch_converter._cancel_event = self.cancel_event

        for bf in self._batch_files:
            self.batch_converter.add(bf['path'], fmt)

        self.batch_converter.start()

    def _batch_ui_update(self, idx, item):
        if self.killed:
            return
        self._rebuild_batch_list()
        done = self.batch_converter.completed
        total = self.batch_converter.total
        self.batch_convert_btn.configure(text=f"Converting {done}/{total}...")

    def _batch_finished(self):
        if self.killed:
            return
        done = sum(1 for it in self.batch_converter.items if it.status == 'done')
        total = len(self.batch_converter.items)
        self.batch_convert_btn.configure(state="normal",
                                         text=f"Done! {done}/{total} converted")
        self.batch_kill_btn.configure(state="disabled")
        self._rebuild_batch_list()

        if messagebox.askyesno("Batch Complete",
                               f"{done}/{total} files converted.\n\nOpen output folder?"):
            open_folder(self.output_dir)

    # ── History Page ────────────────────────────────────────

    def _page_history(self):
        header = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="Recent Conversions",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=C['text']).pack(side="left")
        ctk.CTkButton(header, text="Clear All", width=100, height=32,
                      corner_radius=8, fg_color=C['error'],
                      hover_color="#dc2626",
                      font=ctk.CTkFont(size=12),
                      command=self._clear_history).pack(side="right")

        scroll = ctk.CTkScrollableFrame(self.page_frame, fg_color=C['bg_card'],
                                         corner_radius=12, border_width=1,
                                         border_color=C['border'])
        scroll.pack(fill="both", expand=True)

        records = self.history.get_recent(50)
        if not records:
            ctk.CTkLabel(scroll, text="No conversion history yet.",
                         font=ctk.CTkFont(size=13),
                         text_color=C['text_muted']).pack(expand=True, pady=40)
            return

        for rec in records:
            row = ctk.CTkFrame(scroll, fg_color=C['bg_hover'],
                               corner_radius=8, height=42)
            row.pack(fill="x", pady=2, padx=5)
            row.pack_propagate(False)

            status_color = C['success'] if rec['status'] == 'success' else C['error']
            ctk.CTkLabel(row, text="  " + rec.get('source_name', '?'),
                         font=ctk.CTkFont(size=12),
                         text_color=C['text']).pack(side="left", padx=5)
            ctk.CTkLabel(row, text="->",
                         text_color=C['text_muted']).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=rec.get('output_name', '?'),
                         font=ctk.CTkFont(size=12),
                         text_color=status_color).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=rec.get('datetime', ''),
                         font=ctk.CTkFont(size=10),
                         text_color=C['text_muted']).pack(side="right", padx=10)

    def _clear_history(self):
        self.history.clear()
        self.show_page("history")

    # ── Settings Page ───────────────────────────────────────

    def _page_settings(self):
        ctk.CTkLabel(self.page_frame, text="Settings",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=C['text']).pack(anchor="w", pady=(0, 20))

        card = ctk.CTkFrame(self.page_frame, fg_color=C['bg_card'],
                            corner_radius=12, border_width=1,
                            border_color=C['border'])
        card.pack(fill="x", pady=(0, 15))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=25, pady=20)

        # Output folder
        ctk.CTkLabel(inner, text="Output Folder",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C['text']).pack(anchor="w")

        folder_row = ctk.CTkFrame(inner, fg_color="transparent")
        folder_row.pack(fill="x", pady=(8, 20))

        self.output_entry = ctk.CTkEntry(
            folder_row, height=36, corner_radius=8,
            fg_color=C['bg_input'], border_color=C['border'],
            text_color=C['text'])
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.output_entry.insert(0, str(self.output_dir))

        ctk.CTkButton(folder_row, text="Change", width=80, height=36,
                      corner_radius=8, fg_color=C['accent'],
                      hover_color=C['accent_hover'],
                      command=self._change_output_folder).pack(side="right")

        # After conversion
        ctk.CTkLabel(inner, text="After Conversion",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C['text']).pack(anchor="w")

        self.after_conv_var = ctk.StringVar(value=self.settings.get("after_conversion", "ask"))
        for val, label in [("ask", "Ask me each time"), ("open_folder", "Open output folder"),
                           ("notify", "Show notification only")]:
            ctk.CTkRadioButton(inner, text=label, variable=self.after_conv_var,
                               value=val, text_color=C['text2'],
                               fg_color=C['accent'], hover_color=C['accent_hover'],
                               command=lambda: self.settings.set("after_conversion",
                                                                  self.after_conv_var.get())
                               ).pack(anchor="w", pady=3)

        # Quality settings card
        card2 = ctk.CTkFrame(self.page_frame, fg_color=C['bg_card'],
                             corner_radius=12, border_width=1,
                             border_color=C['border'])
        card2.pack(fill="x", pady=(0, 15))

        inner2 = ctk.CTkFrame(card2, fg_color="transparent")
        inner2.pack(fill="x", padx=25, pady=20)

        ctk.CTkLabel(inner2, text="Image Quality (JPEG/WebP)",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C['text']).pack(anchor="w")

        quality_row = ctk.CTkFrame(inner2, fg_color="transparent")
        quality_row.pack(fill="x", pady=(8, 15))

        self.quality_label = ctk.CTkLabel(quality_row,
                                          text=f"{self.settings.get('image_quality', 85)}%",
                                          font=ctk.CTkFont(size=13),
                                          text_color=C['accent_glow'])
        self.quality_label.pack(side="right", padx=10)

        self.quality_slider = ctk.CTkSlider(
            quality_row, from_=10, to=100,
            number_of_steps=18,
            fg_color=C['bg_hover'], progress_color=C['accent'],
            button_color=C['accent_glow'], button_hover_color=C['accent'],
            command=self._on_quality_change)
        self.quality_slider.set(self.settings.get("image_quality", 85))
        self.quality_slider.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(inner2, text="Audio Bitrate",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C['text']).pack(anchor="w", pady=(5, 0))

        self.bitrate_var = ctk.StringVar(value=self.settings.get("audio_bitrate", "192k"))
        bitrate_row = ctk.CTkFrame(inner2, fg_color="transparent")
        bitrate_row.pack(fill="x", pady=(8, 0))
        for br in ["128k", "192k", "256k", "320k"]:
            ctk.CTkRadioButton(bitrate_row, text=br, variable=self.bitrate_var,
                               value=br, text_color=C['text2'],
                               fg_color=C['accent'], hover_color=C['accent_hover'],
                               command=lambda: self.settings.set("audio_bitrate",
                                                                  self.bitrate_var.get())
                               ).pack(side="left", padx=10)

        # Reset
        ctk.CTkButton(self.page_frame, text="Reset to Defaults", height=40,
                      corner_radius=10, fg_color=C['bg_hover'],
                      hover_color=C['error'], text_color=C['text2'],
                      command=self._reset_settings).pack(fill="x", pady=(5, 0))

    def _change_output_folder(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_dir = Path(folder)
            self.output_dir.mkdir(exist_ok=True)
            self.settings.set("output_dir", str(folder))
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, str(folder))

    def _on_quality_change(self, value):
        val = int(value)
        self.quality_label.configure(text=f"{val}%")
        self.settings.set("image_quality", val)

    def _reset_settings(self):
        self.settings.reset()
        self.show_page("settings")


if __name__ == "__main__":
    app = FileConverterPro()
    app.mainloop()
