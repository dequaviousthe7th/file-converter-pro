"""
Audio Converter Module
Handles conversions between audio formats using pydub (ffmpeg wrapper).
Requires ffmpeg to be installed on the system.
"""

import os
from pathlib import Path
from backend.converters.base_converter import BaseConverter, ConversionError

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


class AudioConverter(BaseConverter):
    """Convert between audio formats"""

    SUPPORTED_OUTPUTS = ['mp3', 'wav', 'flac', 'ogg', 'aac', 'm4a', 'wma']

    FORMAT_MAP = {
        'mp3': {'format': 'mp3', 'codec': 'libmp3lame'},
        'wav': {'format': 'wav', 'codec': 'pcm_s16le'},
        'flac': {'format': 'flac', 'codec': 'flac'},
        'ogg': {'format': 'ogg', 'codec': 'libvorbis'},
        'aac': {'format': 'adts', 'codec': 'aac'},
        'm4a': {'format': 'ipod', 'codec': 'aac'},
        'wma': {'format': 'asf', 'codec': 'wmav2'},
    }

    def convert(self, input_path: str, output_path: str, target_format: str,
                bitrate: str = "192k") -> bool:
        if not PYDUB_AVAILABLE:
            raise ConversionError("pydub not installed", "pip install pydub")

        from utils.platform_utils import check_ffmpeg
        if not check_ffmpeg():
            raise ConversionError(
                "ffmpeg is required for audio conversion",
                "Install ffmpeg: https://ffmpeg.org/download.html"
            )

        self.check_cancel()

        if target_format not in self.FORMAT_MAP:
            raise ConversionError(f"Unsupported audio format: {target_format}")

        try:
            self.report_progress(10, "Loading audio file...")
            ext = Path(input_path).suffix.lower().lstrip('.')

            # Load the audio file
            if ext == 'mp3':
                audio = AudioSegment.from_mp3(input_path)
            elif ext == 'wav':
                audio = AudioSegment.from_wav(input_path)
            elif ext == 'ogg':
                audio = AudioSegment.from_ogg(input_path)
            elif ext == 'flac':
                audio = AudioSegment.from_file(input_path, format='flac')
            else:
                audio = AudioSegment.from_file(input_path)

            self.check_cancel()
            self.report_progress(50, f"Converting to {target_format.upper()}...")

            fmt_info = self.FORMAT_MAP[target_format]
            export_params = {
                'format': fmt_info['format'],
                'codec': fmt_info['codec'],
            }

            # Add bitrate for lossy formats
            if target_format in ['mp3', 'ogg', 'aac', 'm4a', 'wma']:
                export_params['bitrate'] = bitrate

            # Preserve tags if possible
            if hasattr(audio, 'tags') and audio.tags:
                export_params['tags'] = audio.tags

            self.check_cancel()
            self.report_progress(70, "Exporting...")
            audio.export(output_path, **export_params)

            self.report_progress(100, "Done")
            return True

        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"Audio conversion failed: {e}")
