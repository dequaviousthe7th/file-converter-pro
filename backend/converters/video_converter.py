"""
Video Converter Module
Handles conversions between video formats using ffmpeg.
Requires ffmpeg to be installed on the system.
"""

import os
import subprocess
import re
from pathlib import Path
from backend.converters.base_converter import BaseConverter, ConversionError

_NW = {'creationflags': 0x08000000} if os.name == 'nt' else {}


class VideoConverter(BaseConverter):
    """Convert between video formats using ffmpeg"""

    SUPPORTED_OUTPUTS = ['mp4', 'avi', 'mkv', 'mov', 'webm', 'gif']

    # Sensible codec defaults per container format
    FORMAT_SETTINGS = {
        'mp4':  {'-c:v': 'libx264', '-c:a': 'aac', '-movflags': '+faststart'},
        'avi':  {'-c:v': 'libx264', '-c:a': 'mp3'},
        'mkv':  {'-c:v': 'libx264', '-c:a': 'aac'},
        'mov':  {'-c:v': 'libx264', '-c:a': 'aac', '-movflags': '+faststart'},
        'webm': {'-c:v': 'libvpx-vp9', '-c:a': 'libopus', '-b:v': '2M'},
        'gif':  {},  # Special handling
    }

    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        from utils.platform_utils import check_ffmpeg
        if not check_ffmpeg():
            raise ConversionError(
                "ffmpeg is required for video conversion",
                "Install ffmpeg: https://ffmpeg.org/download.html"
            )

        self.check_cancel()

        if target_format not in self.FORMAT_SETTINGS:
            raise ConversionError(f"Unsupported video format: {target_format}")

        try:
            if target_format == 'gif':
                return self._to_gif(input_path, output_path)
            return self._convert_video(input_path, output_path, target_format)
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"Video conversion failed: {e}")

    def _get_duration(self, input_path: str) -> float:
        """Get video duration in seconds using ffprobe."""
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', input_path],
                capture_output=True, text=True, timeout=10, **_NW
            )
            return float(result.stdout.strip())
        except Exception:
            return 0

    def _convert_video(self, input_path: str, output_path: str, target_format: str) -> bool:
        self.report_progress(5, "Analyzing video...")
        duration = self._get_duration(input_path)

        settings = self.FORMAT_SETTINGS[target_format]
        cmd = ['ffmpeg', '-i', input_path, '-y']

        for key, val in settings.items():
            cmd.extend([key, val])

        cmd.append(output_path)

        self.report_progress(10, f"Converting to {target_format.upper()}...")

        process = subprocess.Popen(
            cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
            universal_newlines=True, **_NW
        )

        # Parse ffmpeg progress output
        while True:
            self.check_cancel()
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
            if 'time=' in line and duration > 0:
                match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                if match:
                    h, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
                    current = h * 3600 + m * 60 + s
                    pct = min(int(10 + 85 * current / duration), 95)
                    self.report_progress(pct, f"Converting... {int(current)}s / {int(duration)}s")

        if process.returncode != 0:
            stderr = process.stderr.read() if process.stderr else ""
            raise ConversionError(f"ffmpeg exited with code {process.returncode}",
                                  stderr[:500])

        self.report_progress(100, "Done")
        return True

    def _to_gif(self, input_path: str, output_path: str) -> bool:
        """Convert video to GIF with reasonable defaults."""
        self.report_progress(10, "Creating GIF...")

        # Two-pass approach for better quality GIFs
        # Pass 1: Generate palette
        palette_path = output_path + '.palette.png'
        try:
            cmd_palette = [
                'ffmpeg', '-i', input_path, '-y',
                '-vf', 'fps=10,scale=480:-1:flags=lanczos,palettegen',
                palette_path
            ]
            result = subprocess.run(cmd_palette, capture_output=True, text=True, timeout=120, **_NW)
            if result.returncode != 0:
                raise ConversionError("Failed to generate GIF palette")

            self.check_cancel()
            self.report_progress(50, "Generating GIF frames...")

            # Pass 2: Generate GIF using palette
            cmd_gif = [
                'ffmpeg', '-i', input_path, '-i', palette_path, '-y',
                '-lavfi', 'fps=10,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse',
                output_path
            ]
            result = subprocess.run(cmd_gif, capture_output=True, text=True, timeout=300, **_NW)
            if result.returncode != 0:
                raise ConversionError("Failed to create GIF")

        finally:
            if os.path.exists(palette_path):
                os.remove(palette_path)

        self.report_progress(100, "Done")
        return True
