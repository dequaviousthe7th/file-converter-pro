#!/usr/bin/env python3
"""
File Converter Pro - Simple UI (WinRAR Style)
Basic, clean, functional. Design preserved exactly.
v2.0 additions: batch mode, drag-drop, safe cancel, all new formats.
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import FORMATS, VERSION, APP_NAME, AUTHOR, get_filetypes
from backend.converter_registry import get_converter, get_json_converter, is_supported
from backend.converters.base_converter import ConversionError
from backend.batch_converter import BatchConverter, BatchItem
from utils.platform_utils import open_folder
from utils.file_utils import get_file_size_str
import subprocess

# Try to import drag-and-drop support
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


class SimpleConverter:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("400x530")
        self.root.resizable(True, True)
        self.root.minsize(350, 530)

        # Set window icon
        self._set_icon()

        self.center_window()

        self.selected_file = None
        self.target_format = None
        self.conversion_thread = None
        self.cancel_event = threading.Event()
        self.killed = False
        self.output_dir = Path(__file__).parent / "converted"
        self.output_dir.mkdir(exist_ok=True)

        # Batch mode
        self.batch_mode = False
        self.batch_files = []  # list of dicts: {path, name, ext, size, target}
        self.batch_converter = None

        self.create_ui()
        self._setup_drag_drop()

    def _set_icon(self):
        """Set the window icon using multiple methods for reliability."""
        assets = Path(__file__).parent / "assets"
        try:
            ico = assets / "logo.ico"
            if ico.exists():
                self.root.iconbitmap(str(ico))
        except Exception:
            pass
        try:
            png = assets / "logo.png"
            if png.exists():
                icon_img = tk.PhotoImage(file=str(png))
                self.root.iconphoto(True, icon_img)
                self._icon_ref = icon_img
        except Exception:
            pass

    def center_window(self):
        self.root.update_idletasks()
        w, h = 400, 530
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def _setup_drag_drop(self):
        """Setup whole-window drag-and-drop overlay."""
        if not DND_AVAILABLE:
            return

        # Create overlay frame (hidden initially)
        self.drop_overlay = tk.Frame(self.root, bg='#cccccc')
        self.drop_label = tk.Label(
            self.drop_overlay, text="Drop file here",
            font=("Segoe UI", 18, "bold"), bg='#cccccc', fg='#555555'
        )
        self.drop_label.place(relx=0.5, rely=0.5, anchor="center")

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<DropEnter>>', self._on_drag_enter)
        self.root.dnd_bind('<<DropLeave>>', self._on_drag_leave)
        self.root.dnd_bind('<<Drop>>', self._on_drop)

    def _on_drag_enter(self, event):
        txt = "Drop files here" if self.batch_mode else "Drop file here"
        self.drop_label.configure(text=txt)
        self.drop_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _on_drag_leave(self, event):
        self.drop_overlay.place_forget()

    def _on_drop(self, event):
        self.drop_overlay.place_forget()
        # Parse dropped file paths (tkdnd returns space-separated, braces for paths with spaces)
        raw = event.data
        files = []
        if '{' in raw:
            import re
            files = re.findall(r'\{([^}]+)\}', raw)
            remaining = re.sub(r'\{[^}]+\}', '', raw).strip()
            if remaining:
                files.extend(remaining.split())
        else:
            files = raw.split()

        if self.batch_mode:
            for f in files:
                self._add_batch_file(f)
        else:
            if files:
                self._load_file(files[0])

    def create_ui(self):
        # Create a canvas with scrollbar for scrolling
        canvas = tk.Canvas(self.root, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)

        main = ttk.Frame(canvas, padding="15")

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        scrollbar.pack_forget()
        canvas.pack(side="left", fill="both", expand=True)

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

        canvas_window = canvas.create_window((0, 0), window=main, anchor="nw", width=400)

        def configure_canvas(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            update_scrollbar()
        main.bind("<Configure>", configure_canvas)

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
            update_scrollbar()
        canvas.bind("<Configure>", on_canvas_configure)

        # Header with title and credit
        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 15))

        header_left = ttk.Frame(header)
        header_left.pack(side="left")

        logo_title_row = ttk.Frame(header_left)
        logo_title_row.pack(anchor="w")

        logo_canvas = tk.Canvas(logo_title_row, width=40, height=40, bg="#f0f0f0",
                                highlightthickness=0, bd=0)
        logo_canvas.pack(side="left", padx=(0, 10))
        logo_canvas.create_polygon(20, 5, 35, 20, 25, 20, 25, 35, 15, 35, 15, 20, 5, 20,
                                   fill="#5ba3e8", outline="#5ba3e8")

        header_right = ttk.Frame(header)
        header_right.pack(side="right")

        switch_btn = tk.Button(header_right, text="Switch to Advanced UI",
                               font=("Segoe UI", 7), fg="#666666", bg="#e8e8e8",
                               activebackground="#d0d0d0", activeforeground="#333333",
                               relief="flat", cursor="hand2", bd=0,
                               command=self._switch_to_advanced)
        switch_btn.pack(anchor="ne", pady=(8, 0))
        switch_btn.bind("<Enter>", lambda e: switch_btn.configure(fg="#333333", bg="#d8d8d8"))
        switch_btn.bind("<Leave>", lambda e: switch_btn.configure(fg="#666666", bg="#e8e8e8"))

        ttk.Label(header_right, text=f"Version: {VERSION}", font=("Segoe UI", 8),
                  foreground="gray").pack(anchor="ne", pady=(4, 0))

        title_frame = ttk.Frame(logo_title_row)
        title_frame.pack(side="left")

        ttk.Label(title_frame, text=APP_NAME, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        credit_row = ttk.Frame(title_frame)
        credit_row.pack(anchor="w")

        ttk.Label(credit_row, text="Built by:", font=("Segoe UI", 8),
                  foreground="gray").pack(side="left", padx=(0, 2))

        author_link = tk.Label(credit_row, text=AUTHOR, font=("Segoe UI", 8),
                               fg="#5ba3e8", bg="#f0f0f0", cursor="hand2", padx=0)
        author_link.pack(side="left", padx=0)
        author_link.bind("<Enter>", lambda e: author_link.configure(fg="#3d8bd4"))
        author_link.bind("<Leave>", lambda e: author_link.configure(fg="#5ba3e8"))
        author_link.bind("<Button-1>", lambda e: __import__('webbrowser').open("https://github.com/dequaviousthe7th"))

        # Batch mode toggle
        batch_frame = ttk.Frame(main)
        batch_frame.pack(fill="x", pady=(0, 5))
        self.batch_var = tk.BooleanVar(value=False)
        self.batch_check = ttk.Checkbutton(
            batch_frame, text="Batch Mode (multiple files)",
            variable=self.batch_var, command=self._toggle_batch
        )
        self.batch_check.pack(side="left")

        # File selection
        file_frame = ttk.LabelFrame(main, text="Select File", padding="10")
        file_frame.pack(fill="x", pady=(0, 10))

        file_row = ttk.Frame(file_frame)
        file_row.pack(fill="x")

        self.file_entry = ttk.Entry(file_row, state="readonly")
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.browse_btn = ttk.Button(file_row, text="Browse...", command=self.browse_file, width=10)
        self.browse_btn.pack(side="right")

        self.file_info = ttk.Label(file_frame, text="No file selected", foreground="gray")
        self.file_info.pack(anchor="w", pady=(5, 0))

        # Batch file list (hidden by default)
        self.batch_list_frame = ttk.LabelFrame(main, text="Batch Files", padding="5")
        self.batch_listbox = tk.Listbox(self.batch_list_frame, height=5, font=("Segoe UI", 9))
        self.batch_listbox.pack(fill="x", expand=True)
        batch_btn_row = ttk.Frame(self.batch_list_frame)
        batch_btn_row.pack(fill="x", pady=(5, 0))
        ttk.Button(batch_btn_row, text="Remove", command=self._remove_batch_item, width=8).pack(side="left")
        ttk.Button(batch_btn_row, text="Clear All", command=self._clear_batch, width=8).pack(side="right")
        # batch_list_frame is packed/unpacked by _toggle_batch

        # Format selection
        self.format_frame = ttk.LabelFrame(main, text="Convert To", padding="10", height=90)
        self.format_frame.pack(fill="x", pady=(0, 10))
        self.format_frame.pack_propagate(False)

        self.format_var = tk.StringVar()
        self.format_buttons = []

        self.format_placeholder = ttk.Label(self.format_frame, text="Select a file first", foreground="gray")
        self.format_placeholder.pack(pady=15)

        # Convert button
        self.convert_btn = ttk.Button(main, text="Convert File", command=self.convert, state="disabled")
        self.convert_btn.pack(fill="x", pady=(0, 10), ipady=8)

        # Progress bar
        self.progress = ttk.Progressbar(main, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 5))
        self.progress["value"] = 0

        # Kill button
        self.stop_btn = ttk.Button(main, text="Kill", command=self.kill_conversion, state="disabled")
        self.stop_btn.pack(anchor="e", pady=(0, 10))

        # Status
        self.status = ttk.Label(main, text="Ready", foreground="gray")
        self.status.pack(anchor="w")

        # Separator
        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=15)

        # Output folder
        ttk.Button(main, text="Open Output Folder", command=self.open_output_folder).pack(fill="x")

    def _switch_to_advanced(self):
        """Launch Advanced UI and close this one."""
        kw = {'creationflags': 0x08000000} if os.name == 'nt' else {}
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
            adv_exe = exe_dir.parent / "Advanced" / "File Converter Pro.exe"
            if adv_exe.exists():
                subprocess.Popen([str(adv_exe)], cwd=str(adv_exe.parent), **kw)
                self.root.destroy()
                return
        python = sys.executable
        script = Path(__file__).parent / "app.py"
        if script.exists():
            subprocess.Popen([python, str(script)], cwd=str(script.parent), **kw)
            self.root.destroy()

    # --- Batch mode ---

    def _toggle_batch(self):
        self.batch_mode = self.batch_var.get()
        if self.batch_mode:
            self.batch_list_frame.pack(fill="x", pady=(0, 10),
                                       before=self.format_frame)
            self.convert_btn.configure(text="Convert All")
            self.drop_label_text = "Drop files here"
        else:
            self.batch_list_frame.pack_forget()
            self.batch_files.clear()
            self.batch_listbox.delete(0, tk.END)
            self.convert_btn.configure(text="Convert File")
            self.drop_label_text = "Drop file here"
        self.reset()

    def _add_batch_file(self, path):
        path = str(path).strip()
        ext = Path(path).suffix.lower().lstrip('.')
        if not is_supported(ext):
            return
        name = Path(path).name
        size = Path(path).stat().st_size
        self.batch_files.append({'path': path, 'name': name, 'ext': ext, 'size': size, 'target': None})
        self.batch_listbox.insert(tk.END, f"{name} ({get_file_size_str(size)})")
        # Show formats for first file type
        if len(self.batch_files) == 1:
            self.show_formats(ext)

    def _remove_batch_item(self):
        sel = self.batch_listbox.curselection()
        if sel:
            idx = sel[0]
            self.batch_files.pop(idx)
            self.batch_listbox.delete(idx)

    def _clear_batch(self):
        self.batch_files.clear()
        self.batch_listbox.delete(0, tk.END)

    # --- File handling ---

    def _load_file(self, path):
        """Load a single file (for non-batch mode)."""
        path = str(path).strip()
        ext = Path(path).suffix.lower().lstrip('.')
        if ext not in FORMATS:
            messagebox.showerror("Error", f".{ext} not supported")
            return

        self.selected_file = {
            'path': path, 'name': Path(path).name,
            'ext': ext, 'size': Path(path).stat().st_size
        }

        self.file_entry.configure(state="normal")
        self.file_entry.delete(0, "end")
        self.file_entry.insert(0, path)
        self.file_entry.configure(state="readonly")

        size_str = get_file_size_str(self.selected_file['size'])
        self.file_info.configure(text=f"{FORMATS[ext]['name']} | {size_str}")
        self.show_formats(ext)

    def browse_file(self):
        ft = get_filetypes()
        if self.batch_mode:
            paths = filedialog.askopenfilenames(title="Select files", filetypes=ft)
            for p in paths:
                self._add_batch_file(p)
        else:
            path = filedialog.askopenfilename(title="Select a file", filetypes=ft)
            if path:
                self._load_file(path)

    def show_formats(self, ext):
        self.format_placeholder.pack_forget()

        for widget in self.format_frame.winfo_children():
            widget.destroy()
        self.format_buttons.clear()

        fmt_info = FORMATS.get(ext, {})
        available = fmt_info.get('to', [])
        if not available:
            return

        # Adjust frame height based on number of formats
        rows_needed = (len(available) + 2) // 3
        height = max(90, rows_needed * 30 + 20)
        self.format_frame.configure(height=height)

        frame = ttk.Frame(self.format_frame)
        frame.pack(fill="x", pady=(2, 0))

        row, col = 0, 0
        for fmt in available:
            name = FORMATS.get(fmt, {}).get('name', fmt.upper())
            rb = ttk.Radiobutton(frame, text=name, variable=self.format_var, value=fmt,
                                 command=self.on_format_selected, takefocus=False)
            rb.grid(row=row, column=col, sticky="w", padx=10, pady=2)
            self.format_buttons.append(rb)
            col += 1
            if col > 2:
                col = 0
                row += 1

    def on_format_selected(self):
        self.target_format = self.format_var.get()
        self.convert_btn.configure(state="normal")
        self.status.configure(text=f"Ready to convert to {self.target_format.upper()}")

    # --- Conversion ---

    def convert(self):
        if self.batch_mode:
            self._convert_batch()
        else:
            self._convert_single()

    def _convert_single(self):
        if not self.selected_file or not self.target_format:
            return

        self.killed = False
        self.cancel_event.clear()

        self.convert_btn.configure(state="disabled", text="Converting...")
        self.stop_btn.configure(state="normal")
        self.status.configure(text="Converting...")
        self.progress["value"] = 0
        self.root.update()

        self.conversion_thread = threading.Thread(target=self.do_convert, daemon=True)
        self.conversion_thread.start()

    def _convert_batch(self):
        if not self.batch_files or not self.target_format:
            messagebox.showwarning("Batch", "Add files and select a format first.")
            return

        self.killed = False
        self.cancel_event.clear()
        total = len(self.batch_files)

        self.convert_btn.configure(state="disabled", text=f"Converting 0/{total}...")
        self.stop_btn.configure(state="normal")
        self.progress["value"] = 0

        def on_item_update(idx, item):
            pct = int(100 * (idx + (item.progress / 100)) / total)
            self.root.after(0, lambda: self._update_batch_ui(idx, item, pct, total))

        def on_complete():
            self.root.after(0, self._batch_done)

        self.batch_converter = BatchConverter(
            str(self.output_dir),
            on_item_update=on_item_update,
            on_batch_complete=on_complete
        )
        self.batch_converter._cancel_event = self.cancel_event

        for bf in self.batch_files:
            self.batch_converter.add(bf['path'], self.target_format)

        self.batch_converter.start()

    def _update_batch_ui(self, idx, item, pct, total):
        if self.killed:
            return
        done = sum(1 for it in self.batch_converter.items if it.status in ('done', 'failed', 'cancelled'))
        self.progress["value"] = pct
        self.convert_btn.configure(text=f"Converting {done}/{total}...")
        self.status.configure(text=f"{item.filename}: {item.message}")

    def _batch_done(self):
        if self.killed:
            return
        done = sum(1 for it in self.batch_converter.items if it.status == 'done')
        failed = sum(1 for it in self.batch_converter.items if it.status == 'failed')
        total = len(self.batch_converter.items)

        self.progress["value"] = 100
        self.stop_btn.configure(state="disabled")
        self.convert_btn.configure(state="normal", text="Convert All")
        self.status.configure(text=f"Batch complete: {done}/{total} succeeded, {failed} failed")

        if messagebox.askyesno("Batch Complete",
                               f"Done! {done}/{total} files converted.\n\nOpen output folder?"):
            self.open_output_folder()

    def kill_conversion(self):
        """Kill the conversion safely using cancel event."""
        self.killed = True
        self.cancel_event.set()
        self.status.configure(text="Killed")

        if self.batch_converter and self.batch_converter.is_running:
            self.batch_converter.kill()

        self.conversion_thread = None
        self.progress["value"] = 0
        self.convert_btn.configure(state="disabled",
                                   text="Convert All" if self.batch_mode else "Convert File")
        self.stop_btn.configure(state="disabled")

    def do_convert(self):
        start_time = time.time()
        try:
            if self.killed:
                return

            input_path = self.selected_file['path']
            target = self.target_format
            ext = self.selected_file['ext']

            output_name = f"{Path(input_path).stem}_converted.{target}"
            output_path = str(self.output_dir / output_name)

            def progress_cb(pct, msg=""):
                if not self.killed:
                    self.root.after(0, lambda: self._update_progress(pct, msg))

            # Handle JSON -> config format special case
            if ext == 'json' and target in ('yaml', 'toml'):
                converter = get_json_converter(target, self.cancel_event, progress_cb)
            else:
                converter = get_converter(ext, self.cancel_event, progress_cb)

            if self.killed:
                return

            converter.convert(input_path, output_path, target)

            if self.killed:
                return

            self.root.after(0, lambda: self.done(output_path))

        except ConversionError as e:
            if self.killed:
                return
            self.root.after(0, lambda msg=e.message: self.failed(msg))
        except Exception as e:
            if self.killed:
                return
            self.root.after(0, lambda msg=str(e): self.failed(msg))

    def _update_progress(self, pct, msg):
        if self.killed:
            return
        self.progress["value"] = pct
        if msg:
            self.status.configure(text=msg)

    def done(self, path):
        if self.killed:
            return
        self.progress["value"] = 100
        self.convert_btn.configure(text="Convert File")
        self.stop_btn.configure(state="disabled")
        name = Path(path).name
        self.status.configure(text=f"Saved: {name}")

        self.root.after(2000, lambda: self.progress.configure(value=0))

        if messagebox.askyesno("Success!", f"Converted!\n\nSaved as: {name}\n\nOpen folder?"):
            self.open_output_folder()
        self.reset()

    def failed(self, error=""):
        if self.killed:
            return
        self.progress["value"] = 0
        self.convert_btn.configure(state="normal", text="Convert File")
        self.stop_btn.configure(state="disabled")
        self.status.configure(text="Failed")
        messagebox.showerror("Error", f"Conversion failed.\n{error}")

    def reset(self):
        self.selected_file = None
        self.target_format = None
        self.format_var.set("")

        self.file_entry.configure(state="normal")
        self.file_entry.delete(0, "end")
        self.file_entry.configure(state="readonly")

        self.file_info.configure(text="No file selected", foreground="gray")

        for widget in self.format_frame.winfo_children():
            widget.destroy()
        self.format_buttons.clear()

        self.format_placeholder = ttk.Label(self.format_frame, text="Select a file first", foreground="gray")
        self.format_placeholder.pack(pady=15)

        btn_text = "Convert All" if self.batch_mode else "Convert File"
        self.convert_btn.configure(state="disabled", text=btn_text)
        self.stop_btn.configure(state="disabled")
        self.progress["value"] = 0
        self.status.configure(text="Ready", foreground="gray")
        self.killed = False
        self.cancel_event.clear()

        self.format_frame.focus_set()
        self.root.focus_set()

    def open_output_folder(self):
        open_folder(self.output_dir)


def main():
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = SimpleConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
