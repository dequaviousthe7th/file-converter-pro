"""
Image Converter Module
Handles conversions between image formats including TIFF, ICO, GIF, SVG, HEIC
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from backend.converters.base_converter import BaseConverter, ConversionError

try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except (ImportError, OSError):
    CAIROSVG_AVAILABLE = False

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_AVAILABLE = True
except (ImportError, OSError):
    HEIF_AVAILABLE = False


class ImageConverter(BaseConverter):
    """Convert between image formats and to PDF"""

    SUPPORTED_OUTPUTS = ['pdf', 'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'tif', 'gif', 'ico']

    FORMAT_MAP = {
        'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG', 'webp': 'WEBP',
        'bmp': 'BMP', 'tiff': 'TIFF', 'tif': 'TIFF', 'gif': 'GIF', 'ico': 'ICO',
    }

    def convert(self, input_path: str, output_path: str, target_format: str,
                quality: int = 95, resize: Optional[Tuple[int, int]] = None) -> bool:
        if not PIL_AVAILABLE:
            raise ConversionError("PIL/Pillow not installed", "pip install Pillow")

        self.check_cancel()
        ext = Path(input_path).suffix.lower().lstrip('.')

        # SVG needs special handling
        if ext == 'svg':
            return self._from_svg(input_path, output_path, target_format)

        if target_format == 'pdf':
            return self._to_pdf(input_path, output_path)
        elif target_format in self.SUPPORTED_OUTPUTS:
            return self._to_image(input_path, output_path, target_format, quality, resize)
        else:
            raise ConversionError(f"Unsupported target format: {target_format}")

    def _ensure_rgb(self, img):
        """Convert image to RGB, handling transparency with white background."""
        if img.mode in ('RGBA', 'LA', 'P', 'PA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA', 'PA'):
                background.paste(img, mask=img.split()[-1])
                return background
        if img.mode != 'RGB':
            return img.convert('RGB')
        return img

    def _to_pdf(self, input_path: str, output_path: str) -> bool:
        if not REPORTLAB_AVAILABLE:
            raise ConversionError("reportlab not installed")
        try:
            self.report_progress(10, "Opening image...")
            img = Image.open(input_path)
            img = self._ensure_rgb(img)

            self.check_cancel()
            self.report_progress(30, "Creating PDF...")

            img_width, img_height = img.size
            page_width, page_height = A4
            margin = 36
            avail_w = page_width - 2 * margin
            avail_h = page_height - 2 * margin
            aspect = img_height / img_width

            if (avail_w * aspect) > avail_h:
                new_h = avail_h
                new_w = avail_h / aspect
            else:
                new_w = avail_w
                new_h = avail_w * aspect

            x = (page_width - new_w) / 2
            y = (page_height - new_h) / 2

            c = canvas.Canvas(output_path, pagesize=A4)

            # Use temp file with proper cleanup
            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(tmp_fd)
            try:
                img.save(tmp_path, 'JPEG', quality=95)
                self.check_cancel()
                self.report_progress(70, "Embedding in PDF...")
                c.drawImage(tmp_path, x, y, width=new_w, height=new_h)
                c.save()
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            self.report_progress(100, "Done")
            return True
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"Image to PDF failed: {e}")

    def _to_image(self, input_path: str, output_path: str, target_format: str,
                  quality: int, resize: Optional[Tuple[int, int]]) -> bool:
        try:
            self.report_progress(10, "Opening image...")
            with Image.open(input_path) as img:
                self.check_cancel()

                # Convert mode for formats that don't support alpha
                if target_format in ['jpg', 'jpeg', 'bmp']:
                    img = self._ensure_rgb(img)
                elif target_format == 'ico':
                    # ICO needs specific sizes
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    img = img.resize((256, 256), Image.Resampling.LANCZOS)

                if resize and target_format != 'ico':
                    img = img.resize(resize, Image.Resampling.LANCZOS)

                self.report_progress(60, "Saving...")
                pil_format = self.FORMAT_MAP.get(target_format, target_format.upper())

                save_kwargs = {}
                if target_format in ['jpg', 'jpeg']:
                    save_kwargs = {'quality': quality, 'optimize': True}
                elif target_format == 'png':
                    save_kwargs = {'optimize': True}
                elif target_format == 'webp':
                    save_kwargs = {'quality': quality}
                elif target_format == 'tiff' or target_format == 'tif':
                    save_kwargs = {'compression': 'tiff_lzw'}

                img.save(output_path, pil_format, **save_kwargs)

            self.report_progress(100, "Done")
            return True
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"Image conversion failed: {e}")

    def _from_svg(self, input_path: str, output_path: str, target_format: str) -> bool:
        """Convert SVG to raster formats."""
        if not CAIROSVG_AVAILABLE:
            raise ConversionError("cairosvg not installed for SVG conversion",
                                  "pip install cairosvg")
        try:
            self.report_progress(20, "Rasterizing SVG...")
            self.check_cancel()

            if target_format == 'pdf':
                cairosvg.svg2pdf(url=input_path, write_to=output_path)
            elif target_format in ['png']:
                cairosvg.svg2png(url=input_path, write_to=output_path)
            else:
                # Convert via PNG intermediate
                tmp_fd, tmp_path = tempfile.mkstemp(suffix='.png')
                os.close(tmp_fd)
                try:
                    cairosvg.svg2png(url=input_path, write_to=tmp_path)
                    self.check_cancel()
                    with Image.open(tmp_path) as img:
                        if target_format in ['jpg', 'jpeg']:
                            img = self._ensure_rgb(img)
                        img.save(output_path, self.FORMAT_MAP.get(target_format, target_format.upper()))
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

            self.report_progress(100, "Done")
            return True
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"SVG conversion failed: {e}")
