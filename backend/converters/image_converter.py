"""
Image Converter Module
Handles conversions between image formats
"""

import os
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class ImageConverter:
    """Convert between image formats and to PDF"""
    
    SUPPORTED_OUTPUTS = ['pdf', 'png', 'jpg', 'jpeg', 'webp', 'bmp']
    
    # Format mapping for PIL
    FORMAT_MAP = {
        'jpg': 'JPEG',
        'jpeg': 'JPEG',
        'png': 'PNG',
        'webp': 'WEBP',
        'bmp': 'BMP'
    }
    
    def convert(
        self, 
        input_path: str, 
        output_path: str, 
        target_format: str,
        quality: int = 95,
        resize: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        Convert image to target format
        
        Args:
            input_path: Path to input image
            output_path: Path to output file
            target_format: Target format extension
            quality: JPEG quality (1-100)
            resize: Optional (width, height) tuple
            
        Returns:
            bool: True if conversion successful
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL/Pillow library not installed")
        
        if target_format == 'pdf':
            return self._to_pdf(input_path, output_path)
        elif target_format in self.SUPPORTED_OUTPUTS:
            return self._to_image(input_path, output_path, target_format, quality, resize)
        else:
            raise ValueError(f"Unsupported target format: {target_format}")
    
    def _to_pdf(self, input_path: str, output_path: str) -> bool:
        """Convert image to PDF"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab library not installed")
        
        try:
            # Open image
            img = Image.open(input_path)
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                else:
                    img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get image dimensions
            img_width, img_height = img.size
            
            # Calculate aspect ratio and fit to page
            page_width, page_height = A4
            margin = 36  # 0.5 inch margin
            available_width = page_width - 2 * margin
            available_height = page_height - 2 * margin
            
            aspect = img_height / img_width
            
            if (available_width * aspect) > available_height:
                # Fit to height
                new_height = available_height
                new_width = available_height / aspect
            else:
                # Fit to width
                new_width = available_width
                new_height = available_width * aspect
            
            # Center the image
            x = (page_width - new_width) / 2
            y = (page_height - new_height) / 2
            
            # Create PDF
            c = canvas.Canvas(output_path, pagesize=A4)
            
            # Save image temporarily
            temp_img_path = output_path + '.temp.jpg'
            img.save(temp_img_path, 'JPEG', quality=95)
            
            # Draw image on PDF
            c.drawImage(temp_img_path, x, y, width=new_width, height=new_height)
            c.save()
            
            # Clean up temp file
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
            
            return True
            
        except Exception as e:
            print(f"Image to PDF conversion error: {e}")
            return False
    
    def _to_image(
        self, 
        input_path: str, 
        output_path: str, 
        target_format: str,
        quality: int,
        resize: Optional[Tuple[int, int]]
    ) -> bool:
        """Convert image to another image format"""
        try:
            with Image.open(input_path) as img:
                # Convert mode if necessary
                if target_format in ['jpg', 'jpeg']:
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        if img.mode in ('RGBA', 'LA'):
                            background.paste(img, mask=img.split()[-1])
                            img = background
                        else:
                            img = img.convert('RGB')
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                
                # Resize if requested
                if resize:
                    img = img.resize(resize, Image.Resampling.LANCZOS)
                
                # Get PIL format name
                pil_format = self.FORMAT_MAP.get(target_format, target_format.upper())
                
                # Save with appropriate options
                save_kwargs = {}
                if target_format in ['jpg', 'jpeg']:
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                elif target_format == 'png':
                    save_kwargs['optimize'] = True
                elif target_format == 'webp':
                    save_kwargs['quality'] = quality
                
                img.save(output_path, pil_format, **save_kwargs)
            
            return True
            
        except Exception as e:
            print(f"Image conversion error: {e}")
            return False
    
    def get_image_info(self, input_path: str) -> dict:
        """Get information about an image"""
        if not PIL_AVAILABLE:
            raise ImportError("PIL/Pillow library not installed")
        
        try:
            with Image.open(input_path) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'width': img.width,
                    'height': img.height,
                    'size_bytes': os.path.getsize(input_path)
                }
        except Exception as e:
            print(f"Error getting image info: {e}")
            return {}
