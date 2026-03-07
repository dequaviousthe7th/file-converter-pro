#!/usr/bin/env python3
"""
File Converter Pro - Installation Wizard
Cross-platform installer using only standard library (no dependencies needed).
Users just run this script and the wizard handles everything.
"""

import os
import sys
import platform
import subprocess
import threading
import shutil
import json
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

APP_NAME = "File Converter Pro"
VERSION = "2.0.0"
AUTHOR = "Dequavious"

# Support running as PyInstaller bundle or normal script
if getattr(sys, 'frozen', False):
    # Running as compiled exe — assets bundled inside
    BUNDLE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).parent.resolve()
else:
    BUNDLE_DIR = Path(__file__).parent.resolve()
    APP_DIR = BUNDLE_DIR

SYSTEM = platform.system()  # Windows, Darwin, Linux


# ── Utility Functions ─────────────────────────────────────

def find_python():
    """Find the best Python executable available."""
    candidates = ["python3", "python", sys.executable]
    if SYSTEM == "Windows":
        candidates = ["python", "python3", sys.executable]
    for cmd in candidates:
        try:
            result = subprocess.run(
                [cmd, "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                ver = result.stdout.strip() or result.stderr.strip()
                if "3." in ver:
                    return cmd, ver
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None, None


def check_ffmpeg():
    """Check if ffmpeg is installed."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            first_line = result.stdout.split('\n')[0] if result.stdout else "found"
            return True, first_line
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False, "Not found"


def check_pandoc():
    """Check if pandoc is installed."""
    try:
        result = subprocess.run(
            ["pandoc", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            first_line = result.stdout.split('\n')[0] if result.stdout else "found"
            return True, first_line
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False, "Not found"


def get_venv_python():
    """Get the Python executable path inside the venv."""
    if SYSTEM == "Windows":
        return str(APP_DIR / "venv" / "Scripts" / "python.exe")
    return str(APP_DIR / "venv" / "bin" / "python3")


def get_venv_pip():
    """Get the pip executable path inside the venv."""
    if SYSTEM == "Windows":
        return str(APP_DIR / "venv" / "Scripts" / "pip.exe")
    return str(APP_DIR / "venv" / "bin" / "pip3")


# ── Styling ───────────────────────────────────────────────

COLORS = {
    'bg':       '#f8f9fa',
    'card':     '#ffffff',
    'accent':   '#2563eb',
    'accent_h': '#1d4ed8',
    'success':  '#16a34a',
    'error':    '#dc2626',
    'warning':  '#d97706',
    'text':     '#111827',
    'text_sec': '#6b7280',
    'text_dim': '#9ca3af',
    'border':   '#e5e7eb',
    'step_done':'#16a34a',
    'step_cur': '#2563eb',
    'step_todo':'#d1d5db',
    'input_bg': '#f3f4f6',
    'bar_bg':   '#e5e7eb',
}


# ── Installation Wizard ──────────────────────────────────

class InstallWizard:
    STEPS = ["Welcome", "Choose UI", "Configure", "Install", "Complete"]

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - Setup")
        self.root.geometry("700x520")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS['bg'])

        # Set icon if available (look in bundle dir for assets)
        icon_path = BUNDLE_DIR / "assets" / "logo.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass
        self._logo_img = None
        try:
            logo_path = BUNDLE_DIR / "assets" / "logo.png"
            if logo_path.exists():
                img = tk.PhotoImage(file=str(logo_path))
                self.root.iconphoto(True, img)
                # Subsample for welcome page display (~80px)
                factor = max(1, img.width() // 80)
                self._logo_img = img.subsample(factor, factor)
                self._logo_img_full = img  # keep reference
        except Exception:
            pass

        self._center()

        # State
        self.current_step = 0
        self.ui_choice = tk.StringVar(value="advanced")
        self.output_dir = tk.StringVar(value=str(APP_DIR / "converted"))
        self.create_shortcut = tk.BooleanVar(value=True)
        self.install_log = []
        self.install_success = False

        # Preview images
        self._adv_img = None
        self._simple_img = None
        self._load_previews()

        # Build UI
        self._build_step_bar()
        self._build_content()
        self._build_nav()
        self._show_step(0)

    def _center(self):
        self.root.update_idletasks()
        w, h = 700, 520
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _load_previews(self):
        """Try to load preview images for UI selection."""
        try:
            adv_path = BUNDLE_DIR / "assets" / "Advanced-UI.png"
            simple_path = BUNDLE_DIR / "assets" / "Simple-UI.png"
            if adv_path.exists():
                self._adv_img = tk.PhotoImage(file=str(adv_path))
                # Subsample to fit (roughly 280px wide)
                w = self._adv_img.width()
                factor = max(1, w // 280)
                self._adv_img = self._adv_img.subsample(factor, factor)
            if simple_path.exists():
                self._simple_img = tk.PhotoImage(file=str(simple_path))
                w = self._simple_img.width()
                factor = max(1, w // 180)
                self._simple_img = self._simple_img.subsample(factor, factor)
        except Exception:
            pass

    # ── Layout ────────────────────────────────────────────

    def _build_step_bar(self):
        """Step indicator bar at the top."""
        self.step_bar = tk.Frame(self.root, bg=COLORS['card'], height=70)
        self.step_bar.pack(fill="x")
        self.step_bar.pack_propagate(False)

        # Separator line
        tk.Frame(self.root, bg=COLORS['border'], height=1).pack(fill="x")

        self.step_labels = []
        self.step_circles = []

        bar_inner = tk.Frame(self.step_bar, bg=COLORS['card'])
        bar_inner.place(relx=0.5, rely=0.5, anchor="center")

        for i, name in enumerate(self.STEPS):
            if i > 0:
                line = tk.Frame(bar_inner, bg=COLORS['step_todo'], width=50, height=2)
                line.pack(side="left", padx=0, pady=(0, 14))
                # Store reference for color updates
                if not hasattr(self, '_step_lines'):
                    self._step_lines = []
                self._step_lines.append(line)

            step_frame = tk.Frame(bar_inner, bg=COLORS['card'])
            step_frame.pack(side="left", padx=8)

            canvas = tk.Canvas(step_frame, width=28, height=28,
                               bg=COLORS['card'], highlightthickness=0)
            canvas.pack()

            circle = canvas.create_oval(2, 2, 26, 26, fill=COLORS['step_todo'],
                                         outline=COLORS['step_todo'])
            text = canvas.create_text(14, 14, text=str(i + 1),
                                       fill="white", font=("Segoe UI", 10, "bold"))
            self.step_circles.append((canvas, circle, text))

            lbl = tk.Label(step_frame, text=name, bg=COLORS['card'],
                           fg=COLORS['text_dim'], font=("Segoe UI", 9))
            lbl.pack(pady=(2, 0))
            self.step_labels.append(lbl)

    def _build_content(self):
        """Main content area."""
        self.content = tk.Frame(self.root, bg=COLORS['bg'])
        self.content.pack(fill="both", expand=True, padx=40, pady=(20, 10))

    def _build_nav(self):
        """Bottom navigation buttons."""
        tk.Frame(self.root, bg=COLORS['border'], height=1).pack(fill="x")

        self.nav = tk.Frame(self.root, bg=COLORS['card'], height=60)
        self.nav.pack(fill="x", side="bottom")
        self.nav.pack_propagate(False)

        self.btn_back = tk.Button(
            self.nav, text="Back", font=("Segoe UI", 11),
            bg=COLORS['input_bg'], fg=COLORS['text'], relief="flat",
            padx=20, pady=6, cursor="hand2",
            activebackground=COLORS['border'],
            command=self._go_back
        )
        self.btn_back.pack(side="left", padx=20, pady=12)

        self.btn_next = tk.Button(
            self.nav, text="Next", font=("Segoe UI", 11, "bold"),
            bg=COLORS['accent'], fg="white", relief="flat",
            padx=24, pady=6, cursor="hand2",
            activebackground=COLORS['accent_h'],
            command=self._go_next
        )
        self.btn_next.pack(side="right", padx=20, pady=12)

    # ── Step Navigation ───────────────────────────────────

    def _update_step_bar(self):
        """Update the step indicator colors."""
        for i, (canvas, circle, text) in enumerate(self.step_circles):
            if i < self.current_step:
                canvas.itemconfig(circle, fill=COLORS['step_done'], outline=COLORS['step_done'])
                canvas.itemconfig(text, text="\u2713")
                self.step_labels[i].configure(fg=COLORS['step_done'])
            elif i == self.current_step:
                canvas.itemconfig(circle, fill=COLORS['step_cur'], outline=COLORS['step_cur'])
                canvas.itemconfig(text, text=str(i + 1))
                self.step_labels[i].configure(fg=COLORS['step_cur'])
            else:
                canvas.itemconfig(circle, fill=COLORS['step_todo'], outline=COLORS['step_todo'])
                canvas.itemconfig(text, text=str(i + 1))
                self.step_labels[i].configure(fg=COLORS['text_dim'])

        if hasattr(self, '_step_lines'):
            for i, line in enumerate(self._step_lines):
                if i < self.current_step:
                    line.configure(bg=COLORS['step_done'])
                else:
                    line.configure(bg=COLORS['step_todo'])

    def _show_step(self, step):
        self.current_step = step
        self._update_step_bar()

        for w in self.content.winfo_children():
            w.destroy()

        steps = [
            self._step_welcome,
            self._step_choose_ui,
            self._step_configure,
            self._step_install,
            self._step_complete,
        ]
        steps[step]()

        # Update nav buttons
        self.btn_back.configure(state="normal" if step > 0 else "disabled")

        if step == 3:  # Install step
            self.btn_next.configure(text="Install", bg=COLORS['success'],
                                     activebackground="#15803d")
            self.btn_back.configure(state="normal")
        elif step == 4:  # Complete step
            self.btn_next.configure(text="Launch App", bg=COLORS['accent'],
                                     activebackground=COLORS['accent_h'])
            self.btn_back.configure(state="disabled")
        else:
            self.btn_next.configure(text="Next", bg=COLORS['accent'],
                                     activebackground=COLORS['accent_h'])

    def _go_next(self):
        if self.current_step == 3:
            self._run_install()
        elif self.current_step == 4:
            self._launch_app()
        elif self.current_step < len(self.STEPS) - 1:
            self._show_step(self.current_step + 1)

    def _go_back(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    # ── Step 1: Welcome ───────────────────────────────────

    def _step_welcome(self):
        # Logo
        if self._logo_img:
            tk.Label(self.content, image=self._logo_img,
                     bg=COLORS['bg']).pack(pady=(10, 6))

        tk.Label(self.content, text=f"Welcome to {APP_NAME}",
                 font=("Segoe UI", 22, "bold"), bg=COLORS['bg'],
                 fg=COLORS['text']).pack(pady=(4, 6))

        tk.Label(self.content, text=f"Version {VERSION}",
                 font=("Segoe UI", 12), bg=COLORS['bg'],
                 fg=COLORS['text_sec']).pack()

        tk.Label(self.content,
                 text="This wizard will set up everything you need to start\n"
                      "converting files. No coding required.",
                 font=("Segoe UI", 12), bg=COLORS['bg'],
                 fg=COLORS['text_sec'], justify="center").pack(pady=(24, 20))

        # What will be installed
        info_frame = tk.Frame(self.content, bg=COLORS['card'], relief="solid",
                               bd=1, padx=20, pady=16)
        info_frame.pack(fill="x", pady=(10, 0))

        tk.Label(info_frame, text="This installer will:",
                 font=("Segoe UI", 11, "bold"), bg=COLORS['card'],
                 fg=COLORS['text'], anchor="w").pack(fill="x", pady=(0, 8))

        items = [
            "Create a Python virtual environment",
            "Install all required packages",
            "Generate the app icon",
            "Check for optional tools (ffmpeg, pandoc)",
            "Create a desktop shortcut (optional)",
        ]
        for item in items:
            row = tk.Frame(info_frame, bg=COLORS['card'])
            row.pack(fill="x", pady=2)
            tk.Label(row, text="\u2022", font=("Segoe UI", 11),
                     bg=COLORS['card'], fg=COLORS['accent']).pack(side="left", padx=(0, 8))
            tk.Label(row, text=item, font=("Segoe UI", 11),
                     bg=COLORS['card'], fg=COLORS['text_sec']).pack(side="left")

        tk.Label(self.content, text=f"by {AUTHOR}",
                 font=("Segoe UI", 10), bg=COLORS['bg'],
                 fg=COLORS['text_dim']).pack(side="bottom", pady=(0, 0))

    # ── Step 2: Choose UI ─────────────────────────────────

    def _step_choose_ui(self):
        tk.Label(self.content, text="Choose Your Interface",
                 font=("Segoe UI", 18, "bold"), bg=COLORS['bg'],
                 fg=COLORS['text']).pack(pady=(10, 4))

        tk.Label(self.content,
                 text="Pick which UI mode you'd like to use as your default.\nYou can always switch later.",
                 font=("Segoe UI", 11), bg=COLORS['bg'],
                 fg=COLORS['text_sec'], justify="center").pack(pady=(0, 16))

        cards = tk.Frame(self.content, bg=COLORS['bg'])
        cards.pack(fill="both", expand=True)

        # Advanced UI card
        self._ui_card_adv = self._make_ui_card(
            cards, "Advanced UI",
            "Modern dark theme with tabs, history,\nsettings, and batch conversion page.",
            "advanced", self._adv_img
        )
        self._ui_card_adv.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Simple UI card
        self._ui_card_simple = self._make_ui_card(
            cards, "Simple UI",
            "Clean, lightweight classic interface.\nGreat for quick single conversions.",
            "simple", self._simple_img
        )
        self._ui_card_simple.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self._highlight_ui_cards()

    def _make_ui_card(self, parent, title, desc, value, image):
        """Create a clickable UI selection card."""
        card = tk.Frame(parent, bg=COLORS['card'], relief="solid", bd=2,
                         padx=12, pady=12, cursor="hand2")

        # Preview image
        if image:
            img_label = tk.Label(card, image=image, bg=COLORS['card'], cursor="hand2")
            img_label.pack(pady=(4, 8))
            img_label.bind("<Button-1>", lambda e, v=value: self._pick_ui(v))

        # Radio + title
        radio_row = tk.Frame(card, bg=COLORS['card'], cursor="hand2")
        radio_row.pack(fill="x")

        rb = tk.Radiobutton(radio_row, variable=self.ui_choice, value=value,
                             bg=COLORS['card'], activebackground=COLORS['card'],
                             selectcolor=COLORS['accent'],
                             command=self._highlight_ui_cards)
        rb.pack(side="left")

        tk.Label(radio_row, text=title, font=("Segoe UI", 13, "bold"),
                 bg=COLORS['card'], fg=COLORS['text'],
                 cursor="hand2").pack(side="left", padx=(4, 0))

        tk.Label(card, text=desc, font=("Segoe UI", 10),
                 bg=COLORS['card'], fg=COLORS['text_sec'],
                 justify="left", cursor="hand2").pack(anchor="w", pady=(6, 0))

        # Bind click on entire card
        for widget in [card, radio_row]:
            widget.bind("<Button-1>", lambda e, v=value: self._pick_ui(v))

        return card

    def _pick_ui(self, value):
        self.ui_choice.set(value)
        self._highlight_ui_cards()

    def _highlight_ui_cards(self):
        choice = self.ui_choice.get()
        for card, val in [(self._ui_card_adv, "advanced"), (self._ui_card_simple, "simple")]:
            if val == choice:
                card.configure(highlightbackground=COLORS['accent'],
                                relief="solid", bd=2)
                # Change border color via frame trick
                card.configure(bg=COLORS['card'])
                try:
                    card.config(highlightcolor=COLORS['accent'],
                                highlightthickness=2)
                except Exception:
                    pass
            else:
                card.configure(highlightthickness=0, relief="solid", bd=1)

    # ── Step 3: Configure ─────────────────────────────────

    def _step_configure(self):
        tk.Label(self.content, text="Configuration",
                 font=("Segoe UI", 18, "bold"), bg=COLORS['bg'],
                 fg=COLORS['text']).pack(pady=(10, 4))

        tk.Label(self.content,
                 text="Set your preferences. These can be changed later in Settings.",
                 font=("Segoe UI", 11), bg=COLORS['bg'],
                 fg=COLORS['text_sec']).pack(pady=(0, 20))

        # Output folder
        card1 = tk.Frame(self.content, bg=COLORS['card'], relief="solid",
                          bd=1, padx=20, pady=16)
        card1.pack(fill="x", pady=(0, 12))

        tk.Label(card1, text="Output Folder",
                 font=("Segoe UI", 12, "bold"), bg=COLORS['card'],
                 fg=COLORS['text']).pack(anchor="w")
        tk.Label(card1, text="Where converted files will be saved",
                 font=("Segoe UI", 10), bg=COLORS['card'],
                 fg=COLORS['text_sec']).pack(anchor="w", pady=(2, 8))

        folder_row = tk.Frame(card1, bg=COLORS['card'])
        folder_row.pack(fill="x")

        self.folder_entry = tk.Entry(folder_row, textvariable=self.output_dir,
                                      font=("Segoe UI", 10), relief="solid", bd=1,
                                      bg=COLORS['input_bg'])
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)

        tk.Button(folder_row, text="Browse", font=("Segoe UI", 10),
                  bg=COLORS['accent'], fg="white", relief="flat",
                  padx=12, cursor="hand2",
                  activebackground=COLORS['accent_h'],
                  command=self._browse_output).pack(side="right")

        # Desktop shortcut
        card2 = tk.Frame(self.content, bg=COLORS['card'], relief="solid",
                          bd=1, padx=20, pady=16)
        card2.pack(fill="x", pady=(0, 12))

        tk.Label(card2, text="Desktop Shortcut",
                 font=("Segoe UI", 12, "bold"), bg=COLORS['card'],
                 fg=COLORS['text']).pack(anchor="w")

        tk.Checkbutton(card2, text="Create a desktop shortcut for easy access",
                        variable=self.create_shortcut,
                        font=("Segoe UI", 11), bg=COLORS['card'],
                        fg=COLORS['text_sec'], activebackground=COLORS['card'],
                        selectcolor=COLORS['card']).pack(anchor="w", pady=(6, 0))

        # System check preview
        card3 = tk.Frame(self.content, bg=COLORS['card'], relief="solid",
                          bd=1, padx=20, pady=16)
        card3.pack(fill="x")

        tk.Label(card3, text="System Check",
                 font=("Segoe UI", 12, "bold"), bg=COLORS['card'],
                 fg=COLORS['text']).pack(anchor="w", pady=(0, 8))

        python_cmd, python_ver = find_python()
        ffmpeg_ok, ffmpeg_ver = check_ffmpeg()
        pandoc_ok, pandoc_ver = check_pandoc()

        checks = [
            ("Python", python_ver or "Not found!", python_cmd is not None),
            ("ffmpeg", ffmpeg_ver if ffmpeg_ok else "Not found (audio/video won't work)", ffmpeg_ok),
            ("Pandoc", pandoc_ver if pandoc_ok else "Not found (optional)", pandoc_ok),
        ]

        for name, info, ok in checks:
            row = tk.Frame(card3, bg=COLORS['card'])
            row.pack(fill="x", pady=2)
            color = COLORS['success'] if ok else (COLORS['warning'] if name != "Python" else COLORS['error'])
            symbol = "\u2713" if ok else ("\u26A0" if name != "Python" else "\u2717")
            tk.Label(row, text=symbol, font=("Segoe UI", 11),
                     bg=COLORS['card'], fg=color).pack(side="left", padx=(0, 6))
            tk.Label(row, text=f"{name}: ", font=("Segoe UI", 11, "bold"),
                     bg=COLORS['card'], fg=COLORS['text']).pack(side="left")
            tk.Label(row, text=info, font=("Segoe UI", 10),
                     bg=COLORS['card'], fg=COLORS['text_sec']).pack(side="left")

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_dir.set(folder)

    # ── Step 4: Install ───────────────────────────────────

    def _step_install(self):
        tk.Label(self.content, text="Ready to Install",
                 font=("Segoe UI", 18, "bold"), bg=COLORS['bg'],
                 fg=COLORS['text']).pack(pady=(10, 4))

        tk.Label(self.content,
                 text="Click Install to set everything up. This may take a few minutes.",
                 font=("Segoe UI", 11), bg=COLORS['bg'],
                 fg=COLORS['text_sec']).pack(pady=(0, 20))

        # Summary
        summary = tk.Frame(self.content, bg=COLORS['card'], relief="solid",
                            bd=1, padx=20, pady=16)
        summary.pack(fill="x", pady=(0, 16))

        tk.Label(summary, text="Installation Summary",
                 font=("Segoe UI", 12, "bold"), bg=COLORS['card'],
                 fg=COLORS['text']).pack(anchor="w", pady=(0, 8))

        ui_name = "Advanced UI" if self.ui_choice.get() == "advanced" else "Simple UI"
        items = [
            ("Default UI", ui_name),
            ("Output Folder", self.output_dir.get()),
            ("Desktop Shortcut", "Yes" if self.create_shortcut.get() else "No"),
            ("Install Location", str(APP_DIR)),
        ]
        for label, value in items:
            row = tk.Frame(summary, bg=COLORS['card'])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{label}:", font=("Segoe UI", 10, "bold"),
                     bg=COLORS['card'], fg=COLORS['text'], width=16,
                     anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI", 10),
                     bg=COLORS['card'], fg=COLORS['text_sec']).pack(side="left")

        # Progress area (initially hidden, shown during install)
        self.progress_frame = tk.Frame(self.content, bg=COLORS['bg'])
        self.progress_frame.pack(fill="both", expand=True)

        self.progress_status = tk.Label(self.progress_frame, text="",
                                         font=("Segoe UI", 11), bg=COLORS['bg'],
                                         fg=COLORS['text_sec'])
        self.progress_status.pack(pady=(10, 6))

        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate",
                                              maximum=100, length=500)
        self.progress_bar.pack(pady=(0, 10))

        self.log_text = tk.Text(self.progress_frame, height=6, font=("Consolas", 9),
                                 bg=COLORS['input_bg'], fg=COLORS['text_sec'],
                                 relief="solid", bd=1, state="disabled")
        self.log_text.pack(fill="both", expand=True)

    def _run_install(self):
        """Run the actual installation in a background thread."""
        self.btn_next.configure(state="disabled", text="Installing...")
        self.btn_back.configure(state="disabled")
        thread = threading.Thread(target=self._install_worker, daemon=True)
        thread.start()

    def _log(self, msg):
        """Append message to the install log."""
        self.install_log.append(msg)
        self.root.after(0, lambda: self._update_log(msg))

    def _update_log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_progress(self, pct, status=""):
        self.root.after(0, lambda: self._do_set_progress(pct, status))

    def _do_set_progress(self, pct, status):
        self.progress_bar["value"] = pct
        if status:
            self.progress_status.configure(text=status)

    def _install_worker(self):
        """Background thread that does the actual installation."""
        try:
            python_cmd, _ = find_python()
            if not python_cmd:
                self._log("ERROR: Python 3 not found! Please install Python 3.8+ first.")
                self._install_failed("Python 3 not found")
                return

            # Step 1: Create virtual environment
            self._set_progress(5, "Creating virtual environment...")
            self._log(f"Using Python: {python_cmd}")
            venv_path = APP_DIR / "venv"

            if not venv_path.exists():
                self._log("Creating virtual environment...")
                result = subprocess.run(
                    [python_cmd, "-m", "venv", str(venv_path)],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode != 0:
                    self._log(f"ERROR: {result.stderr}")
                    self._install_failed("Failed to create virtual environment")
                    return
                self._log("Virtual environment created.")
            else:
                self._log("Virtual environment already exists.")

            self._set_progress(15, "Installing Python packages...")

            # Step 2: Install requirements
            pip_cmd = get_venv_pip()
            venv_python = get_venv_python()

            # Upgrade pip first
            self._log("Upgrading pip...")
            subprocess.run(
                [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True, text=True, timeout=120
            )

            self._set_progress(20, "Installing packages (this may take a few minutes)...")
            self._log("Installing packages from requirements.txt...")

            result = subprocess.run(
                [pip_cmd, "install", "-r", str(APP_DIR / "requirements.txt")],
                capture_output=True, text=True, timeout=600,
                cwd=str(APP_DIR)
            )

            if result.returncode != 0:
                # Show last few lines of error
                err_lines = result.stderr.strip().split('\n')[-5:]
                for line in err_lines:
                    self._log(f"  {line}")
                self._log("WARNING: Some packages may have failed to install.")
                self._log("The app may still work for most conversions.")
            else:
                self._log("All packages installed successfully.")

            self._set_progress(70, "Generating app icon...")

            # Step 3: Generate logo
            self._log("Generating app logo...")
            logo_script = APP_DIR / "assets" / "generate_logo.py"
            if logo_script.exists():
                result = subprocess.run(
                    [venv_python, str(logo_script)],
                    capture_output=True, text=True, timeout=30,
                    cwd=str(APP_DIR)
                )
                if result.returncode == 0:
                    self._log("Logo generated.")
                else:
                    self._log("Logo generation skipped (non-critical).")
            else:
                self._log("Logo script not found, skipping.")

            self._set_progress(80, "Saving settings...")

            # Step 4: Save settings
            self._log("Saving preferences...")
            settings_dir = Path.home() / ".file-converter-pro"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_file = settings_dir / "settings.json"

            settings = {
                "output_dir": self.output_dir.get(),
                "last_ui": self.ui_choice.get(),
                "after_conversion": "ask",
                "audio_bitrate": "192k",
                "image_quality": 85,
                "theme": "dark",
            }
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            self._log("Settings saved.")

            # Ensure output dir exists
            out = Path(self.output_dir.get())
            out.mkdir(parents=True, exist_ok=True)

            self._set_progress(90, "Creating shortcut...")

            # Step 5: Desktop shortcut
            if self.create_shortcut.get():
                self._create_desktop_shortcut()
            else:
                self._log("Desktop shortcut skipped.")

            self._set_progress(100, "Installation complete!")
            self._log("\nInstallation complete!")
            self.install_success = True
            self.root.after(500, lambda: self._show_step(4))

        except Exception as e:
            self._log(f"\nERROR: {str(e)}")
            self._install_failed(str(e))

    def _install_failed(self, error):
        self._set_progress(0, f"Installation failed: {error}")
        self.root.after(0, lambda: self.btn_next.configure(
            state="normal", text="Retry", bg=COLORS['error']))
        self.root.after(0, lambda: self.btn_back.configure(state="normal"))

    def _create_desktop_shortcut(self):
        """Create a desktop shortcut (platform-specific)."""
        ui = self.ui_choice.get()
        app_script = "app.py" if ui == "advanced" else "app_simple.py"

        if SYSTEM == "Windows":
            self._create_windows_shortcut(app_script)
        elif SYSTEM == "Darwin":
            self._create_macos_shortcut(app_script)
        else:
            self._create_linux_shortcut(app_script)

    def _create_windows_shortcut(self, app_script):
        """Create a .lnk shortcut on Windows desktop."""
        try:
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                # Try OneDrive desktop
                desktop = Path.home() / "OneDrive" / "Desktop"
            if not desktop.exists():
                self._log("Could not find Desktop folder, shortcut skipped.")
                return

            bat_name = "START.bat" if app_script == "app.py" else "START_SIMPLE.bat"
            target = APP_DIR / bat_name

            # Use VBScript to create shortcut
            vbs = f'''Set WshShell = WScript.CreateObject("WScript.Shell")
Set Shortcut = WshShell.CreateShortcut("{desktop / 'File Converter Pro.lnk'}")
Shortcut.TargetPath = "{target}"
Shortcut.WorkingDirectory = "{APP_DIR}"
Shortcut.Description = "{APP_NAME} - Convert files easily"
'''
            # Add icon if available
            ico_path = APP_DIR / "assets" / "logo.ico"
            if ico_path.exists():
                vbs += f'Shortcut.IconLocation = "{ico_path}"\n'

            vbs += 'Shortcut.Save\n'

            vbs_path = Path(os.environ.get('TEMP', '/tmp')) / "fc_shortcut.vbs"
            with open(vbs_path, 'w') as f:
                f.write(vbs)

            subprocess.run(["cscript", "//nologo", str(vbs_path)],
                           capture_output=True, timeout=10)
            vbs_path.unlink(missing_ok=True)
            self._log(f"Desktop shortcut created.")
        except Exception as e:
            self._log(f"Shortcut creation failed: {e}")

    def _create_macos_shortcut(self, app_script):
        """Create a .command file on macOS desktop."""
        try:
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                self._log("Desktop folder not found, shortcut skipped.")
                return

            venv_python = get_venv_python()
            script_path = desktop / "File Converter Pro.command"
            with open(script_path, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(f'cd "{APP_DIR}"\n')
                f.write(f'"{venv_python}" "{app_script}"\n')
            os.chmod(str(script_path), 0o755)
            self._log("Desktop shortcut created.")
        except Exception as e:
            self._log(f"Shortcut creation failed: {e}")

    def _create_linux_shortcut(self, app_script):
        """Create a .desktop file on Linux desktop."""
        try:
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                desktop = Path.home()

            venv_python = get_venv_python()
            ico_path = APP_DIR / "assets" / "logo.png"

            desktop_entry = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Convert files easily
Exec={venv_python} {APP_DIR / app_script}
Path={APP_DIR}
Terminal=false
"""
            if ico_path.exists():
                desktop_entry += f"Icon={ico_path}\n"

            entry_path = desktop / "file-converter-pro.desktop"
            with open(entry_path, 'w') as f:
                f.write(desktop_entry)
            os.chmod(str(entry_path), 0o755)
            self._log("Desktop shortcut created.")
        except Exception as e:
            self._log(f"Shortcut creation failed: {e}")

    # ── Step 5: Complete ──────────────────────────────────

    def _step_complete(self):
        tk.Label(self.content, text="\u2713",
                 font=("Segoe UI", 48), bg=COLORS['bg'],
                 fg=COLORS['success']).pack(pady=(20, 0))

        tk.Label(self.content, text="Installation Complete!",
                 font=("Segoe UI", 22, "bold"), bg=COLORS['bg'],
                 fg=COLORS['text']).pack(pady=(4, 6))

        tk.Label(self.content,
                 text=f"{APP_NAME} is ready to use.",
                 font=("Segoe UI", 12), bg=COLORS['bg'],
                 fg=COLORS['text_sec']).pack(pady=(0, 24))

        # Info card
        card = tk.Frame(self.content, bg=COLORS['card'], relief="solid",
                         bd=1, padx=20, pady=16)
        card.pack(fill="x", pady=(0, 16))

        ui_name = "Advanced UI" if self.ui_choice.get() == "advanced" else "Simple UI"
        tips = [
            f"Your default UI is set to {ui_name}",
            f"Converted files will be saved to: {self.output_dir.get()}",
            "You can change settings anytime inside the app",
        ]

        ffmpeg_ok, _ = check_ffmpeg()
        if not ffmpeg_ok:
            tips.append("Install ffmpeg to enable audio and video conversion")

        for tip in tips:
            row = tk.Frame(card, bg=COLORS['card'])
            row.pack(fill="x", pady=2)
            tk.Label(row, text="\u2022", font=("Segoe UI", 11),
                     bg=COLORS['card'], fg=COLORS['accent']).pack(side="left", padx=(0, 8))
            tk.Label(row, text=tip, font=("Segoe UI", 11),
                     bg=COLORS['card'], fg=COLORS['text_sec']).pack(side="left")

        tk.Label(self.content, text="Click 'Launch App' to start converting!",
                 font=("Segoe UI", 11), bg=COLORS['bg'],
                 fg=COLORS['text_dim']).pack(pady=(10, 0))

    def _launch_app(self):
        """Launch the chosen UI and close the wizard."""
        venv_python = get_venv_python()
        app_script = "app.py" if self.ui_choice.get() == "advanced" else "app_simple.py"

        try:
            if SYSTEM == "Windows":
                subprocess.Popen(
                    [venv_python, str(APP_DIR / app_script)],
                    cwd=str(APP_DIR),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                subprocess.Popen(
                    [venv_python, str(APP_DIR / app_script)],
                    cwd=str(APP_DIR),
                    start_new_session=True
                )
        except Exception:
            pass

        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    wizard = InstallWizard()
    wizard.run()
