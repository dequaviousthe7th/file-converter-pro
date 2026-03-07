#!/usr/bin/env python3
"""
File Converter Pro - Advanced UI
Modern studio-inspired design with top tab navigation.
Complete rebuild for v2.0.
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

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# ── Color Palette ─────────────────────────────────────────
# Charcoal/slate base with teal/emerald accents
T = {
    'bg':           '#111116',
    'bg_card':      '#1c1c24',
    'bg_elevated':  '#252530',
    'bg_surface':   '#2a2a36',
    'bg_input':     '#18181f',
    'accent':       '#00d4aa',
    'accent_hover': '#00b894',
    'accent_dim':   '#0a3d32',
    'success':      '#00d4aa',
    'error':        '#ff6b6b',
    'error_hover':  '#e05555',
    'warning':      '#ffd93d',
    'text':         '#eef0f4',
    'text_sec':     '#8b8fa3',
    'text_dim':     '#555770',
    'border':       '#2d2d3a',
    'border_focus': '#00d4aa',
    'tab_bg':       '#1c1c24',
    'tab_active':   '#252530',
    'tab_indicator':'#00d4aa',
    'row_hover':    '#22222e',
    'row_alt':      '#1a1a22',
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

CATEGORIES = ["Documents", "Images", "Audio", "Video", "Data", "Config"]


class FileConverterPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1060x720")
        self.minsize(900, 640)
        self.configure(fg_color=T['bg'])

        # Set window icon
        self._set_icon()

        self.selected_file = None
        self.target_format = None
        self.output_dir = Path(__file__).parent / "converted"
        self.output_dir.mkdir(exist_ok=True)

        self.cancel_event = threading.Event()
        self.killed = False
        self.conversion_thread = None
        self.batch_converter = None
        self._batch_files = []

        self.history = ConversionHistory()
        self.settings = Settings()

        self.current_tab = "convert"
        self._banner_after_id = None

        self._center_window()
        self._build_ui()
        self._setup_dnd()
        self._show_tab("convert")

    # ── Window Setup ──────────────────────────────────────

    def _set_icon(self):
        """Set the window icon using multiple methods for reliability."""
        assets = Path(__file__).parent / "assets"
        try:
            ico = assets / "logo.ico"
            if ico.exists():
                self.iconbitmap(str(ico))
        except Exception:
            pass
        try:
            png = assets / "logo.png"
            if png.exists():
                icon_img = tk.PhotoImage(file=str(png))
                self.iconphoto(True, icon_img)
                self._icon_ref = icon_img  # prevent garbage collection
        except Exception:
            pass

    def _center_window(self):
        self.update_idletasks()
        w, h = 1060, 720
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

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
        self.drop_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _dnd_leave(self, event):
        self.drop_overlay.place_forget()

    def _dnd_drop(self, event):
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

        if self.current_tab == "batch" and files:
            for f in files:
                self._batch_add_file(f)
            self._show_tab("batch")
        elif files:
            self._load_file(files[0])

    # ── Main UI Build ─────────────────────────────────────

    def _build_ui(self):
        # Drop overlay (hidden)
        self.drop_overlay = ctk.CTkFrame(self, fg_color=("rgba(0,0,0,0.7)", "#111116"),
                                          corner_radius=0)
        drop_inner = ctk.CTkFrame(self.drop_overlay, fg_color=T['bg_card'],
                                   corner_radius=20, border_width=3,
                                   border_color=T['accent'], width=360, height=200)
        drop_inner.place(relx=0.5, rely=0.5, anchor="center")
        drop_inner.pack_propagate(False)
        ctk.CTkLabel(drop_inner, text="Drop Files Here",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=T['accent']).place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(drop_inner, text="Release to add files",
                     font=ctk.CTkFont(size=13),
                     text_color=T['text_sec']).place(relx=0.5, rely=0.6, anchor="center")

        # Container
        self.root_frame = ctk.CTkFrame(self, fg_color=T['bg'], corner_radius=0)
        self.root_frame.pack(fill="both", expand=True)

        self._build_top_bar()
        self._build_content_area()
        self._build_status_bar()

    def _build_top_bar(self):
        top = ctk.CTkFrame(self.root_frame, fg_color=T['bg_card'], height=56, corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)

        # App name on the left
        brand = ctk.CTkFrame(top, fg_color="transparent")
        brand.pack(side="left", padx=24)

        # Logo mark
        logo_box = ctk.CTkFrame(brand, fg_color=T['accent'], corner_radius=8,
                                 width=32, height=32)
        logo_box.pack(side="left", pady=12)
        logo_box.pack_propagate(False)
        ctk.CTkLabel(logo_box, text="FC", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=T['bg']).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(brand, text=APP_NAME,
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=T['text']).pack(side="left", padx=(10, 0))

        # Tab buttons in center
        tab_container = ctk.CTkFrame(top, fg_color="transparent")
        tab_container.pack(side="left", padx=(40, 0))

        self.tab_buttons = {}
        self.tab_indicators = {}
        tabs = [
            ("convert",  "Convert"),
            ("batch",    "Batch"),
            ("history",  "History"),
            ("settings", "Settings"),
        ]

        for tab_id, label in tabs:
            tab_frame = ctk.CTkFrame(tab_container, fg_color="transparent")
            tab_frame.pack(side="left", padx=2)

            btn = ctk.CTkButton(
                tab_frame, text=label,
                font=ctk.CTkFont(size=13),
                width=90, height=36, corner_radius=8,
                fg_color="transparent",
                hover_color=T['bg_elevated'],
                text_color=T['text_sec'],
                command=lambda t=tab_id: self._show_tab(t)
            )
            btn.pack(pady=(10, 0))

            indicator = ctk.CTkFrame(tab_frame, fg_color="transparent",
                                      height=3, corner_radius=2)
            indicator.pack(fill="x", pady=(4, 0), padx=10)

            self.tab_buttons[tab_id] = btn
            self.tab_indicators[tab_id] = indicator

        # Right side spacer
        ctk.CTkFrame(top, fg_color="transparent", width=24).pack(side="right")

    def _build_content_area(self):
        self.content = ctk.CTkFrame(self.root_frame, fg_color=T['bg'], corner_radius=0)
        self.content.pack(fill="both", expand=True)

        # Banner area (for inline success/error messages)
        self.banner_frame = ctk.CTkFrame(self.content, fg_color="transparent", height=0)
        self.banner_frame.pack(fill="x", padx=32)
        self.banner_frame.pack_propagate(False)

        # Page frame
        self.page_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_frame.pack(fill="both", expand=True, padx=32, pady=(8, 16))

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self.root_frame, fg_color=T['bg_card'], height=32, corner_radius=0)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.status_label = ctk.CTkLabel(bar, text="Ready",
                                          font=ctk.CTkFont(size=11),
                                          text_color=T['text_dim'])
        self.status_label.pack(side="left", padx=20)

        # Spacer before credit
        ctk.CTkFrame(bar, fg_color="transparent", width=20).pack(side="right")

        author_link = ctk.CTkLabel(bar, text=AUTHOR,
                                    font=ctk.CTkFont(size=11),
                                    text_color=T['text_sec'], cursor="hand2")
        author_link.pack(side="right", padx=(0, 0))
        author_link.bind("<Enter>", lambda e: author_link.configure(text_color=T['accent']))
        author_link.bind("<Leave>", lambda e: author_link.configure(text_color=T['text_sec']))
        author_link.bind("<Button-1>", lambda e: __import__('webbrowser').open("https://github.com/dequaviousthe7th"))

        ctk.CTkLabel(bar, text="Built by: ",
                     font=ctk.CTkFont(size=11),
                     text_color=T['text_dim']).pack(side="right", padx=(0, 0))

        ctk.CTkLabel(bar, text=f"v{VERSION}",
                     font=ctk.CTkFont(size=11),
                     text_color=T['text_dim']).pack(side="right", padx=(0, 10))

    # ── Tab Navigation ────────────────────────────────────

    def _show_tab(self, tab_id):
        self.current_tab = tab_id

        for tid, btn in self.tab_buttons.items():
            if tid == tab_id:
                btn.configure(text_color=T['text'], fg_color=T['tab_active'])
                self.tab_indicators[tid].configure(fg_color=T['tab_indicator'])
            else:
                btn.configure(text_color=T['text_sec'], fg_color="transparent")
                self.tab_indicators[tid].configure(fg_color="transparent")

        for w in self.page_frame.winfo_children():
            w.destroy()

        pages = {
            "convert":  self._page_convert,
            "batch":    self._page_batch,
            "history":  self._page_history,
            "settings": self._page_settings,
        }
        pages.get(tab_id, self._page_convert)()

    # ── Banner System ─────────────────────────────────────

    def _show_banner(self, text, kind="success", duration=6000, actions=None):
        """Show an inline banner at top of content area."""
        if self._banner_after_id:
            self.after_cancel(self._banner_after_id)
            self._banner_after_id = None

        for w in self.banner_frame.winfo_children():
            w.destroy()

        colors = {
            "success": (T['accent_dim'], T['accent']),
            "error":   ("#3d1a1a", T['error']),
            "warning": ("#3d3a1a", T['warning']),
            "info":    (T['bg_elevated'], T['text']),
        }
        bg_col, text_col = colors.get(kind, colors["info"])

        self.banner_frame.configure(height=52)

        banner = ctk.CTkFrame(self.banner_frame, fg_color=bg_col, corner_radius=10,
                               border_width=1, border_color=text_col)
        banner.pack(fill="x", pady=(8, 0))

        inner = ctk.CTkFrame(banner, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(inner, text=text,
                     font=ctk.CTkFont(size=13),
                     text_color=text_col).pack(side="left")

        if actions:
            for label, cmd in actions:
                ctk.CTkButton(inner, text=label, width=100, height=30,
                              corner_radius=6, fg_color=text_col,
                              hover_color=T['bg_surface'],
                              text_color=bg_col,
                              font=ctk.CTkFont(size=11, weight="bold"),
                              command=cmd).pack(side="right", padx=(6, 0))

        # Close button
        ctk.CTkButton(inner, text="x", width=28, height=28, corner_radius=14,
                      fg_color="transparent", hover_color=T['bg_surface'],
                      text_color=text_col, font=ctk.CTkFont(size=12),
                      command=self._hide_banner).pack(side="right", padx=(6, 0))

        if duration:
            self._banner_after_id = self.after(duration, self._hide_banner)

    def _hide_banner(self):
        if self._banner_after_id:
            self.after_cancel(self._banner_after_id)
            self._banner_after_id = None
        for w in self.banner_frame.winfo_children():
            w.destroy()
        self.banner_frame.configure(height=0)

    # ── Convert Page ──────────────────────────────────────

    def _page_convert(self):
        if self.selected_file:
            self._convert_file_view()
        else:
            self._convert_upload_view()

    def _convert_upload_view(self):
        # Centered drop zone
        outer = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        # Drop zone card
        zone = ctk.CTkFrame(outer, fg_color=T['bg_card'], corner_radius=16,
                             border_width=2, border_color=T['border'])
        zone.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72, relheight=0.78)

        center = ctk.CTkFrame(zone, fg_color="transparent")
        center.place(relx=0.5, rely=0.45, anchor="center")

        # Upload icon area
        icon_ring = ctk.CTkFrame(center, fg_color="transparent", border_width=2,
                                  border_color=T['border'], corner_radius=35,
                                  width=70, height=70)
        icon_ring.pack(pady=(0, 20))
        icon_ring.pack_propagate(False)
        ctk.CTkLabel(icon_ring, text="+", font=ctk.CTkFont(size=32, weight="bold"),
                     text_color=T['accent']).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(center, text="Select a file to convert",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=T['text']).pack()
        ctk.CTkLabel(center, text="Drag & drop or browse from your computer",
                     font=ctk.CTkFont(size=13),
                     text_color=T['text_sec']).pack(pady=(6, 24))

        # Category pills
        pills = ctk.CTkFrame(center, fg_color="transparent")
        pills.pack(pady=(0, 28))
        for cat in CATEGORIES:
            ctk.CTkLabel(pills, text=cat, font=ctk.CTkFont(size=10),
                         fg_color=T['bg_elevated'], corner_radius=12,
                         text_color=T['text_sec'],
                         padx=12, pady=4).pack(side="left", padx=3)

        ctk.CTkButton(center, text="Browse Files",
                      width=200, height=46, corner_radius=23,
                      fg_color=T['accent'], hover_color=T['accent_hover'],
                      text_color=T['bg'],
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._browse_single).pack()

        # Supported count note
        total_fmts = len(FORMATS)
        ctk.CTkLabel(zone, text=f"{total_fmts} formats supported",
                     font=ctk.CTkFont(size=11),
                     text_color=T['text_dim']).place(relx=0.5, rely=0.92, anchor="center")

    def _convert_file_view(self):
        f = self.selected_file
        ext = f['ext']
        cfg = FORMATS.get(ext, {'name': ext.upper(), 'icon': ''})

        # File info card
        file_card = ctk.CTkFrame(self.page_frame, fg_color=T['bg_card'],
                                  corner_radius=12, border_width=1,
                                  border_color=T['border'], height=72)
        file_card.pack(fill="x", pady=(0, 12))
        file_card.pack_propagate(False)

        fc_inner = ctk.CTkFrame(file_card, fg_color="transparent")
        fc_inner.pack(fill="both", expand=True, padx=16, pady=12)

        # File type badge
        badge = ctk.CTkFrame(fc_inner, fg_color=T['accent_dim'], corner_radius=8,
                              width=44, height=44)
        badge.pack(side="left")
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text=ext.upper()[:4],
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=T['accent']).place(relx=0.5, rely=0.5, anchor="center")

        info_col = ctk.CTkFrame(fc_inner, fg_color="transparent")
        info_col.pack(side="left", padx=(12, 0), fill="y")
        ctk.CTkLabel(info_col, text=f['name'],
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=T['text']).pack(anchor="w")
        ctk.CTkLabel(info_col, text=f"{cfg['name']}  -  {get_file_size_str(f['size'])}",
                     font=ctk.CTkFont(size=11),
                     text_color=T['text_sec']).pack(anchor="w")

        ctk.CTkButton(fc_inner, text="Remove", width=80, height=32, corner_radius=8,
                      fg_color="transparent", hover_color=T['error'],
                      border_width=1, border_color=T['border'],
                      text_color=T['text_sec'], font=ctk.CTkFont(size=11),
                      command=self._clear_file).pack(side="right")

        # Format selection area
        fmt_card = ctk.CTkFrame(self.page_frame, fg_color=T['bg_card'],
                                 corner_radius=12, border_width=1,
                                 border_color=T['border'])
        fmt_card.pack(fill="both", expand=True, pady=(0, 12))

        # Header row
        fmt_header = ctk.CTkFrame(fmt_card, fg_color="transparent")
        fmt_header.pack(fill="x", padx=20, pady=(16, 10))

        ctk.CTkLabel(fmt_header, text="Convert to",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=T['text']).pack(side="left")

        # Category filter tabs
        available = FORMATS.get(ext, {}).get('to', [])
        available_cats = set()
        for fmt in available:
            cat = FORMATS.get(fmt, {}).get('category', '')
            if cat:
                available_cats.add(cat)

        if len(available_cats) > 1:
            cat_row = ctk.CTkFrame(fmt_card, fg_color="transparent")
            cat_row.pack(fill="x", padx=20, pady=(0, 8))

            self._active_cat_filter = None
            self._cat_filter_buttons = {}

            def show_cat(cat_name):
                self._active_cat_filter = cat_name
                self._render_format_buttons(fmt_btn_area, ext, cat_name)
                for cn, cb in self._cat_filter_buttons.items():
                    if cn == cat_name:
                        cb.configure(fg_color=T['accent'], text_color=T['bg'])
                    else:
                        cb.configure(fg_color=T['bg_elevated'], text_color=T['text_sec'])

            all_btn = ctk.CTkButton(cat_row, text="All", width=55, height=28,
                                     corner_radius=14, fg_color=T['accent'],
                                     hover_color=T['accent_hover'],
                                     text_color=T['bg'],
                                     font=ctk.CTkFont(size=11),
                                     command=lambda: show_cat(None))
            all_btn.pack(side="left", padx=(0, 4))
            self._cat_filter_buttons[None] = all_btn

            for cat in CATEGORIES:
                if cat in available_cats:
                    cb = ctk.CTkButton(cat_row, text=cat, width=70, height=28,
                                        corner_radius=14, fg_color=T['bg_elevated'],
                                        hover_color=T['bg_surface'],
                                        text_color=T['text_sec'],
                                        font=ctk.CTkFont(size=11),
                                        command=lambda c=cat: show_cat(c))
                    cb.pack(side="left", padx=2)
                    self._cat_filter_buttons[cat] = cb

        # Format buttons area
        fmt_btn_area = ctk.CTkFrame(fmt_card, fg_color="transparent")
        fmt_btn_area.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self.format_buttons = {}
        self._render_format_buttons(fmt_btn_area, ext, None)

        # Bottom action row
        action_row = ctk.CTkFrame(self.page_frame, fg_color="transparent", height=52)
        action_row.pack(fill="x")
        action_row.pack_propagate(False)

        self.convert_btn = ctk.CTkButton(
            action_row, text="Convert", height=48,
            corner_radius=12, fg_color=T['accent'],
            hover_color=T['accent_hover'],
            text_color=T['bg'],
            font=ctk.CTkFont(size=15, weight="bold"),
            state="disabled",
            command=self._start_convert
        )
        self.convert_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.kill_btn = ctk.CTkButton(
            action_row, text="Kill", width=90, height=48,
            corner_radius=12, fg_color=T['error'],
            hover_color=T['error_hover'],
            text_color=T['text'],
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self._kill
        )
        self.kill_btn.pack(side="right")

    def _render_format_buttons(self, container, ext, category_filter):
        for w in container.winfo_children():
            w.destroy()
        self.format_buttons = {}

        available = FORMATS.get(ext, {}).get('to', [])
        filtered = []
        for fmt in available:
            if category_filter:
                if FORMATS.get(fmt, {}).get('category', '') == category_filter:
                    filtered.append(fmt)
            else:
                filtered.append(fmt)

        if not filtered:
            ctk.CTkLabel(container, text="No formats in this category",
                         font=ctk.CTkFont(size=12),
                         text_color=T['text_dim']).pack(pady=20)
            return

        row = None
        for i, fmt in enumerate(filtered):
            if i % 5 == 0:
                row = ctk.CTkFrame(container, fg_color="transparent")
                row.pack(fill="x", pady=3)

            fmt_cfg = FORMATS.get(fmt, {})
            display = f"{fmt_cfg.get('name', fmt.upper())}"

            btn = ctk.CTkButton(
                row, text=display,
                height=42, corner_radius=8,
                fg_color=T['bg_elevated'],
                hover_color=T['bg_surface'],
                text_color=T['text_sec'],
                font=ctk.CTkFont(size=12),
                border_width=1, border_color=T['border'],
                command=lambda fo=fmt: self._select_format(fo)
            )
            btn.pack(side="left", expand=True, fill="x", padx=3)
            self.format_buttons[fmt] = btn

        # Re-highlight if already selected
        if self.target_format in self.format_buttons:
            self.format_buttons[self.target_format].configure(
                fg_color=T['accent'], text_color=T['bg'],
                border_color=T['accent']
            )

    def _select_format(self, fmt):
        self.target_format = fmt
        for f, btn in self.format_buttons.items():
            if f == fmt:
                btn.configure(fg_color=T['accent'], text_color=T['bg'],
                              border_color=T['accent'])
            else:
                btn.configure(fg_color=T['bg_elevated'], text_color=T['text_sec'],
                              border_color=T['border'])
        self.convert_btn.configure(state="normal")
        self._set_status(f"Ready to convert to {fmt.upper()}")

    # ── File Handling ─────────────────────────────────────

    def _browse_single(self):
        ft = get_filetypes()
        path = filedialog.askopenfilename(title="Select a file", filetypes=ft)
        if path:
            self._load_file(path)

    def _load_file(self, path):
        path = str(path).strip()
        ext = Path(path).suffix.lower().lstrip('.')
        if ext not in FORMATS:
            self._show_banner(f".{ext} files are not supported", "error")
            return
        self.selected_file = {
            'path': path, 'name': Path(path).name,
            'ext': ext, 'size': Path(path).stat().st_size
        }
        self.target_format = None
        self._show_tab("convert")

    def _clear_file(self):
        self.selected_file = None
        self.target_format = None
        self._show_tab("convert")

    # ── Conversion ────────────────────────────────────────

    def _start_convert(self):
        if not self.selected_file or not self.target_format:
            return

        self.killed = False
        self.cancel_event.clear()
        self.convert_btn.configure(state="disabled", text="Converting...")
        self.kill_btn.configure(state="normal")
        self._set_status("Converting...")

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
                    self.after(0, lambda: self._update_progress(pct, msg))

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
            self.after(0, lambda: self._convert_success(out_path, duration))

        except ConversionError as e:
            if not self.killed:
                self.history.add(self.selected_file['path'], "", "failed", time.time() - start)
                self.after(0, lambda: self._convert_error(e.message))
        except Exception as e:
            if not self.killed:
                self.after(0, lambda: self._convert_error(str(e)))

    def _update_progress(self, pct, msg):
        if self.killed:
            return
        txt = f"Converting... {pct}%"
        if msg:
            txt = f"{msg} ({pct}%)"
        self.convert_btn.configure(text=txt)
        self._set_status(txt)

    def _convert_success(self, path, duration):
        name = Path(path).name
        self.convert_btn.configure(state="normal", text="Convert")
        self.kill_btn.configure(state="disabled")
        self._set_status(f"Converted in {duration:.1f}s")

        self._show_banner(
            f"Saved: {name}",
            "success", duration=10000,
            actions=[
                ("Open Folder", lambda: open_folder(self.output_dir)),
                ("Open File", lambda: open_file(path)),
            ]
        )
        self._clear_file()

    def _convert_error(self, error):
        self.convert_btn.configure(state="normal", text="Convert")
        self.kill_btn.configure(state="disabled")
        self._set_status("Conversion failed")
        self._show_banner(f"Failed: {error}", "error", duration=10000)

    def _kill(self):
        self.killed = True
        self.cancel_event.set()
        if self.batch_converter and self.batch_converter.is_running:
            self.batch_converter.kill()
        self.convert_btn.configure(state="normal", text="Convert")
        self.kill_btn.configure(state="disabled")
        self._set_status("Cancelled")
        self._show_banner("Conversion cancelled", "warning", duration=4000)

    # ── Batch Page ────────────────────────────────────────

    def _page_batch(self):
        # Header
        header = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(header, text="Batch Conversion",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=T['text']).pack(side="left")

        btn_row = ctk.CTkFrame(header, fg_color="transparent")
        btn_row.pack(side="right")

        if self._batch_files:
            ctk.CTkButton(btn_row, text="Clear All", width=80, height=32,
                          corner_radius=8, fg_color="transparent",
                          hover_color=T['error'], border_width=1,
                          border_color=T['border'],
                          text_color=T['text_sec'], font=ctk.CTkFont(size=11),
                          command=self._batch_clear).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_row, text="+ Add Files", width=100, height=32,
                      corner_radius=8, fg_color=T['accent'],
                      hover_color=T['accent_hover'],
                      text_color=T['bg'], font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._batch_browse).pack(side="left")

        # File table
        table_frame = ctk.CTkScrollableFrame(self.page_frame, fg_color=T['bg_card'],
                                              corner_radius=12, border_width=1,
                                              border_color=T['border'])
        table_frame.pack(fill="both", expand=True, pady=(0, 12))
        self._batch_table = table_frame

        if not self._batch_files:
            empty = ctk.CTkFrame(table_frame, fg_color="transparent")
            empty.pack(expand=True, pady=60)
            ctk.CTkLabel(empty, text="No files added",
                         font=ctk.CTkFont(size=16, weight="bold"),
                         text_color=T['text_dim']).pack()
            ctk.CTkLabel(empty, text="Click '+ Add Files' or drag & drop files here",
                         font=ctk.CTkFont(size=12),
                         text_color=T['text_dim']).pack(pady=(4, 0))
        else:
            # Table header
            th = ctk.CTkFrame(table_frame, fg_color=T['bg_elevated'], corner_radius=6,
                               height=32)
            th.pack(fill="x", padx=6, pady=(6, 2))
            th.pack_propagate(False)

            ctk.CTkLabel(th, text="File", font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=T['text_dim'], width=280).pack(side="left", padx=(12, 0))
            ctk.CTkLabel(th, text="Type", font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=T['text_dim'], width=60).pack(side="left", padx=8)
            ctk.CTkLabel(th, text="Size", font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=T['text_dim'], width=70).pack(side="left", padx=8)
            ctk.CTkLabel(th, text="Status", font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=T['text_dim'], width=80).pack(side="right", padx=12)

            for i, bf in enumerate(self._batch_files):
                bg = T['row_alt'] if i % 2 == 0 else "transparent"
                row = ctk.CTkFrame(table_frame, fg_color=bg, corner_radius=6, height=40)
                row.pack(fill="x", padx=6, pady=1)
                row.pack_propagate(False)

                name_text = bf['name']
                if len(name_text) > 36:
                    name_text = name_text[:33] + "..."
                ctk.CTkLabel(row, text=name_text,
                             font=ctk.CTkFont(size=12),
                             text_color=T['text'], width=280,
                             anchor="w").pack(side="left", padx=(12, 0))

                ctk.CTkLabel(row, text=bf['ext'].upper(),
                             font=ctk.CTkFont(size=11),
                             text_color=T['text_sec'], width=60).pack(side="left", padx=8)

                ctk.CTkLabel(row, text=get_file_size_str(bf['size']),
                             font=ctk.CTkFont(size=11),
                             text_color=T['text_sec'], width=70).pack(side="left", padx=8)

                status = bf.get('status', 'pending')
                status_colors = {
                    'pending': T['text_dim'],
                    'converting': T['warning'],
                    'done': T['success'],
                    'failed': T['error'],
                    'cancelled': T['text_dim'],
                }
                status_text = status.capitalize()
                if status == 'pending':
                    status_text = "Pending"

                status_frame = ctk.CTkFrame(row, fg_color="transparent")
                status_frame.pack(side="right", padx=8)

                if status == 'pending':
                    ctk.CTkButton(status_frame, text="x", width=24, height=24,
                                  corner_radius=12, fg_color="transparent",
                                  hover_color=T['error'], text_color=T['text_dim'],
                                  font=ctk.CTkFont(size=11),
                                  command=lambda idx=i: self._batch_remove(idx)
                                  ).pack(side="right", padx=(4, 0))

                ctk.CTkLabel(status_frame, text=status_text,
                             font=ctk.CTkFont(size=11),
                             text_color=status_colors.get(status, T['text_dim'])
                             ).pack(side="right")

        # Bottom bar
        bottom = ctk.CTkFrame(self.page_frame, fg_color="transparent", height=48)
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        # Format selector
        left = ctk.CTkFrame(bottom, fg_color="transparent")
        left.pack(side="left")

        ctk.CTkLabel(left, text="Convert all to:",
                     font=ctk.CTkFont(size=12),
                     text_color=T['text_sec']).pack(side="left", padx=(0, 8))

        all_targets = set()
        for bf in self._batch_files:
            for t in FORMATS.get(bf['ext'], {}).get('to', []):
                all_targets.add(t)
        target_list = sorted(all_targets) if all_targets else ["---"]

        self.batch_format_var = ctk.StringVar(value="")
        self.batch_format_menu = ctk.CTkOptionMenu(
            left, values=target_list, variable=self.batch_format_var,
            width=110, height=34, corner_radius=8,
            fg_color=T['bg_elevated'], button_color=T['accent'],
            button_hover_color=T['accent_hover'],
            text_color=T['text'])
        self.batch_format_menu.pack(side="left")

        # Buttons
        file_count = len(self._batch_files)
        self.batch_convert_btn = ctk.CTkButton(
            bottom, text=f"Convert All ({file_count})",
            height=42, corner_radius=10,
            fg_color=T['accent'], hover_color=T['accent_hover'],
            text_color=T['bg'],
            font=ctk.CTkFont(size=13, weight="bold"),
            state="normal" if file_count > 0 else "disabled",
            command=self._batch_start
        )
        self.batch_convert_btn.pack(side="left", fill="x", expand=True, padx=(12, 8))

        self.batch_kill_btn = ctk.CTkButton(
            bottom, text="Kill", width=70, height=42,
            corner_radius=10, fg_color=T['error'],
            hover_color=T['error_hover'],
            text_color=T['text'],
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled", command=self._kill
        )
        self.batch_kill_btn.pack(side="right")

    def _batch_browse(self):
        ft = get_filetypes()
        paths = filedialog.askopenfilenames(title="Select files", filetypes=ft)
        for p in paths:
            self._batch_add_file(p)
        if paths:
            self._show_tab("batch")

    def _batch_add_file(self, path):
        path = str(path).strip()
        ext = Path(path).suffix.lower().lstrip('.')
        if not is_supported(ext):
            return
        self._batch_files.append({
            'path': path, 'name': Path(path).name,
            'ext': ext, 'size': Path(path).stat().st_size,
            'status': 'pending'
        })

    def _batch_remove(self, idx):
        if 0 <= idx < len(self._batch_files):
            self._batch_files.pop(idx)
            self._show_tab("batch")

    def _batch_clear(self):
        self._batch_files.clear()
        self._show_tab("batch")

    def _batch_start(self):
        fmt = self.batch_format_var.get()
        if not fmt or fmt == "---" or not self._batch_files:
            self._show_banner("Add files and select a target format first", "warning", 4000)
            return

        self.killed = False
        self.cancel_event.clear()
        self.batch_convert_btn.configure(state="disabled", text="Converting...")
        self.batch_kill_btn.configure(state="normal")
        self._set_status("Batch converting...")

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
        # Re-render the table rows
        if hasattr(self, '_batch_table'):
            self._rebuild_batch_table()
        done = self.batch_converter.completed
        total = self.batch_converter.total
        self.batch_convert_btn.configure(text=f"Converting {done}/{total}...")
        self._set_status(f"Batch: {done}/{total} files processed")

    def _rebuild_batch_table(self):
        if not hasattr(self, '_batch_table'):
            return
        for w in self._batch_table.winfo_children():
            w.destroy()

        # Table header
        th = ctk.CTkFrame(self._batch_table, fg_color=T['bg_elevated'], corner_radius=6,
                           height=32)
        th.pack(fill="x", padx=6, pady=(6, 2))
        th.pack_propagate(False)

        ctk.CTkLabel(th, text="File", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=T['text_dim'], width=280).pack(side="left", padx=(12, 0))
        ctk.CTkLabel(th, text="Type", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=T['text_dim'], width=60).pack(side="left", padx=8)
        ctk.CTkLabel(th, text="Size", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=T['text_dim'], width=70).pack(side="left", padx=8)
        ctk.CTkLabel(th, text="Status", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=T['text_dim'], width=80).pack(side="right", padx=12)

        for i, bf in enumerate(self._batch_files):
            bg = T['row_alt'] if i % 2 == 0 else "transparent"
            row = ctk.CTkFrame(self._batch_table, fg_color=bg, corner_radius=6, height=40)
            row.pack(fill="x", padx=6, pady=1)
            row.pack_propagate(False)

            name_text = bf['name']
            if len(name_text) > 36:
                name_text = name_text[:33] + "..."
            ctk.CTkLabel(row, text=name_text,
                         font=ctk.CTkFont(size=12),
                         text_color=T['text'], width=280,
                         anchor="w").pack(side="left", padx=(12, 0))

            ctk.CTkLabel(row, text=bf['ext'].upper(),
                         font=ctk.CTkFont(size=11),
                         text_color=T['text_sec'], width=60).pack(side="left", padx=8)

            ctk.CTkLabel(row, text=get_file_size_str(bf['size']),
                         font=ctk.CTkFont(size=11),
                         text_color=T['text_sec'], width=70).pack(side="left", padx=8)

            status = bf.get('status', 'pending')
            status_colors = {
                'pending': T['text_dim'],
                'converting': T['warning'],
                'done': T['success'],
                'failed': T['error'],
                'cancelled': T['text_dim'],
            }
            ctk.CTkLabel(row, text=status.capitalize(),
                         font=ctk.CTkFont(size=11),
                         text_color=status_colors.get(status, T['text_dim'])
                         ).pack(side="right", padx=12)

    def _batch_finished(self):
        if self.killed:
            return
        done = sum(1 for it in self.batch_converter.items if it.status == 'done')
        failed = sum(1 for it in self.batch_converter.items if it.status == 'failed')
        total = len(self.batch_converter.items)

        self.batch_convert_btn.configure(state="normal",
                                          text=f"Done: {done}/{total}")
        self.batch_kill_btn.configure(state="disabled")
        self._rebuild_batch_table()
        self._set_status(f"Batch complete: {done} succeeded, {failed} failed")

        if done == total:
            self._show_banner(
                f"All {total} files converted successfully",
                "success", duration=8000,
                actions=[("Open Folder", lambda: open_folder(self.output_dir))]
            )
        else:
            self._show_banner(
                f"{done}/{total} files converted, {failed} failed",
                "warning", duration=8000,
                actions=[("Open Folder", lambda: open_folder(self.output_dir))]
            )

    # ── History Page ──────────────────────────────────────

    def _page_history(self):
        header = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(header, text="Conversion History",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=T['text']).pack(side="left")

        ctk.CTkButton(header, text="Clear All", width=80, height=32,
                      corner_radius=8, fg_color="transparent",
                      hover_color=T['error'], border_width=1,
                      border_color=T['border'],
                      text_color=T['text_sec'], font=ctk.CTkFont(size=11),
                      command=self._clear_history).pack(side="right")

        # Table
        table = ctk.CTkScrollableFrame(self.page_frame, fg_color=T['bg_card'],
                                        corner_radius=12, border_width=1,
                                        border_color=T['border'])
        table.pack(fill="both", expand=True)

        records = self.history.get_recent(50)

        if not records:
            empty = ctk.CTkFrame(table, fg_color="transparent")
            empty.pack(expand=True, pady=60)
            ctk.CTkLabel(empty, text="No conversions yet",
                         font=ctk.CTkFont(size=16, weight="bold"),
                         text_color=T['text_dim']).pack()
            ctk.CTkLabel(empty, text="Your conversion history will appear here",
                         font=ctk.CTkFont(size=12),
                         text_color=T['text_dim']).pack(pady=(4, 0))
            return

        # Table header
        th = ctk.CTkFrame(table, fg_color=T['bg_elevated'], corner_radius=6, height=32)
        th.pack(fill="x", padx=6, pady=(6, 2))
        th.pack_propagate(False)

        ctk.CTkLabel(th, text="Source", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=T['text_dim'], width=200).pack(side="left", padx=(12, 0))
        ctk.CTkLabel(th, text="Output", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=T['text_dim'], width=200).pack(side="left", padx=8)
        ctk.CTkLabel(th, text="Status", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=T['text_dim'], width=60).pack(side="left", padx=8)
        ctk.CTkLabel(th, text="Date", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=T['text_dim'], width=120).pack(side="right", padx=12)

        for i, rec in enumerate(records):
            bg = T['row_alt'] if i % 2 == 0 else "transparent"
            row = ctk.CTkFrame(table, fg_color=bg, corner_radius=6, height=38)
            row.pack(fill="x", padx=6, pady=1)
            row.pack_propagate(False)

            src = rec.get('source_name', '?')
            if len(src) > 28:
                src = src[:25] + "..."
            ctk.CTkLabel(row, text=src, font=ctk.CTkFont(size=11),
                         text_color=T['text'], width=200,
                         anchor="w").pack(side="left", padx=(12, 0))

            out = rec.get('output_name', '?')
            if len(out) > 28:
                out = out[:25] + "..."
            status = rec.get('status', 'success')
            out_color = T['success'] if status == 'success' else T['error']
            ctk.CTkLabel(row, text=out, font=ctk.CTkFont(size=11),
                         text_color=out_color, width=200,
                         anchor="w").pack(side="left", padx=8)

            status_text = "OK" if status == 'success' else "Fail"
            ctk.CTkLabel(row, text=status_text, font=ctk.CTkFont(size=11),
                         text_color=out_color, width=60).pack(side="left", padx=8)

            ctk.CTkLabel(row, text=rec.get('datetime', ''),
                         font=ctk.CTkFont(size=10),
                         text_color=T['text_dim'], width=120).pack(side="right", padx=12)

    def _clear_history(self):
        self.history.clear()
        self._show_tab("history")
        self._show_banner("History cleared", "info", 3000)

    # ── Settings Page ─────────────────────────────────────

    def _page_settings(self):
        ctk.CTkLabel(self.page_frame, text="Settings",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=T['text']).pack(anchor="w", pady=(0, 16))

        # Scrollable settings
        scroll = ctk.CTkScrollableFrame(self.page_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # ─ Output Folder ─
        self._settings_card(scroll, "Output Folder",
                             "Where converted files are saved", self._build_output_setting)

        # ─ After Conversion ─
        self._settings_card(scroll, "After Conversion",
                             "What happens when a file is converted", self._build_after_conv_setting)

        # ─ Image Quality ─
        self._settings_card(scroll, "Image Quality",
                             "JPEG and WebP output quality", self._build_quality_setting)

        # ─ Audio Bitrate ─
        self._settings_card(scroll, "Audio Bitrate",
                             "Default bitrate for audio conversions", self._build_bitrate_setting)

        # Reset
        ctk.CTkButton(scroll, text="Reset All Settings", height=40,
                      corner_radius=10, fg_color=T['bg_elevated'],
                      hover_color=T['error'], text_color=T['text_sec'],
                      border_width=1, border_color=T['border'],
                      font=ctk.CTkFont(size=12),
                      command=self._reset_settings).pack(fill="x", pady=(12, 0))

    def _settings_card(self, parent, title, subtitle, builder_fn):
        card = ctk.CTkFrame(parent, fg_color=T['bg_card'], corner_radius=12,
                             border_width=1, border_color=T['border'])
        card.pack(fill="x", pady=(0, 10))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(inner, text=title,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=T['text']).pack(anchor="w")
        ctk.CTkLabel(inner, text=subtitle,
                     font=ctk.CTkFont(size=11),
                     text_color=T['text_dim']).pack(anchor="w", pady=(2, 10))

        builder_fn(inner)

    def _build_output_setting(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")

        self.output_entry = ctk.CTkEntry(
            row, height=36, corner_radius=8,
            fg_color=T['bg_input'], border_color=T['border'],
            text_color=T['text'])
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.output_entry.insert(0, str(self.output_dir))

        ctk.CTkButton(row, text="Change", width=80, height=36,
                      corner_radius=8, fg_color=T['accent'],
                      hover_color=T['accent_hover'],
                      text_color=T['bg'],
                      command=self._change_output_folder).pack(side="right")

    def _build_after_conv_setting(self, parent):
        self.after_conv_var = ctk.StringVar(value=self.settings.get("after_conversion", "ask"))
        options = [("ask", "Ask me each time"), ("open_folder", "Open output folder"),
                   ("notify", "Show notification only")]
        for val, label in options:
            ctk.CTkRadioButton(parent, text=label, variable=self.after_conv_var,
                               value=val, text_color=T['text_sec'],
                               fg_color=T['accent'], hover_color=T['accent_hover'],
                               border_color=T['border'],
                               command=lambda: self.settings.set("after_conversion",
                                                                  self.after_conv_var.get())
                               ).pack(anchor="w", pady=2)

    def _build_quality_setting(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")

        self.quality_label = ctk.CTkLabel(row,
                                          text=f"{self.settings.get('image_quality', 85)}%",
                                          font=ctk.CTkFont(size=13, weight="bold"),
                                          text_color=T['accent'])
        self.quality_label.pack(side="right", padx=8)

        self.quality_slider = ctk.CTkSlider(
            row, from_=10, to=100, number_of_steps=18,
            fg_color=T['bg_elevated'], progress_color=T['accent'],
            button_color=T['accent'], button_hover_color=T['accent_hover'],
            command=self._on_quality_change)
        self.quality_slider.set(self.settings.get("image_quality", 85))
        self.quality_slider.pack(side="left", fill="x", expand=True)

    def _build_bitrate_setting(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")

        self.bitrate_var = ctk.StringVar(value=self.settings.get("audio_bitrate", "192k"))
        for br in ["128k", "192k", "256k", "320k"]:
            ctk.CTkRadioButton(row, text=br, variable=self.bitrate_var,
                               value=br, text_color=T['text_sec'],
                               fg_color=T['accent'], hover_color=T['accent_hover'],
                               border_color=T['border'],
                               command=lambda: self.settings.set("audio_bitrate",
                                                                  self.bitrate_var.get())
                               ).pack(side="left", padx=(0, 16))

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
        self._show_tab("settings")
        self._show_banner("Settings reset to defaults", "info", 3000)

    # ── Status Bar ────────────────────────────────────────

    def _set_status(self, text):
        self.status_label.configure(text=text)


if __name__ == "__main__":
    app = FileConverterPro()
    app.mainloop()
