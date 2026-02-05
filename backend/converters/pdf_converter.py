"""
PDF Converter Module
Handles conversions from PDF to other formats
"""

import os
from pathlib import Path
from typing import Optional

try:
    from pdf2docx import Converter as PDF2DocxConverter
    PDF2DOCX_AVAILABLE = True
except ImportError:
    PDF2DOCX_AVAILABLE = False

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class PDFConverter:
    """Convert PDF files to various formats"""
    
    SUPPORTED_OUTPUTS = ['docx', 'txt', 'md', 'png', 'jpg']
    
    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        """
        Convert PDF to target format
        
        Args:
            input_path: Path to input PDF file
            output_path: Path to output file
            target_format: Target format extension
            
        Returns:
            bool: True if conversion successful
        """
        if target_format == 'docx':
            return self._to_docx(input_path, output_path)
        elif target_format in ['txt', 'md']:
            return self._to_text(input_path, output_path, target_format)
        elif target_format in ['png', 'jpg']:
            return self._to_image(input_path, output_path, target_format)
        else:
            raise ValueError(f"Unsupported target format: {target_format}")
    
    def _to_docx(self, input_path: str, output_path: str) -> bool:
        """Convert PDF to DOCX"""
        if not PDF2DOCX_AVAILABLE:
            raise ImportError("pdf2docx library not installed")
        
        try:
            cv = PDF2DocxConverter(input_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()
            return True
        except Exception as e:
            print(f"PDF to DOCX conversion error: {e}")
            return False
    
    def _to_text(self, input_path: str, output_path: str, format_type: str) -> bool:
        """Convert PDF to text or markdown"""
        if not PYPDF_AVAILABLE:
            raise ImportError("pypdf library not installed")
        
        try:
            reader = PdfReader(input_path)
            text_content = []
            
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
            
            full_text = "\n\n".join(text_content)
            
            # If markdown, add some basic formatting
            if format_type == 'md':
                full_text = f"# Converted Document\n\n{full_text}"
                # Convert multiple newlines to markdown paragraphs
                full_text = full_text.replace('\n\n\n', '\n\n')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            return True
        except Exception as e:
            print(f"PDF to text conversion error: {e}")
            return False
    
    def _to_image(self, input_path: str, output_path: str, image_format: str) -> bool:
        """
        Convert first page of PDF to image
        Note: This is a basic implementation. For production, use pdf2image.
        """
        try:
            # For now, create a placeholder or use pdf2image if available
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(input_path, first_page=1, last_page=1)
                if images:
                    images[0].save(output_path, format=image_format.upper())
                    return True
            except ImportError:
                pass
            
            # Fallback: create a text-based placeholder
            if not PYPDF_AVAILABLE:
                raise ImportError("pypdf library not installed")
            
            reader = PdfReader(input_path)
            if len(reader.pages) > 0:
                text = reader.pages[0].extract_text()[:500]
            else:
                text = "Empty PDF"
            
            # Create a simple text-based image as fallback
            if PIL_AVAILABLE:
                from PIL import Image, ImageDraw, ImageFont
                
                # Create image with white background
                img = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(img)
                
                # Try to use a default font, fallback to default if not available
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
                except:
                    font = ImageFont.load_default()
                
                # Draw text
                y_position = 50
                draw.text((50, y_position), "PDF Preview (Text Extraction)", fill='black', font=font)
                y_position += 50
                
                # Wrap text
                words = text.split()
                line = ""
                for word in words:
                    test_line = line + word + " "
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    if bbox[2] <= 700:
                        line = test_line
                    else:
                        draw.text((50, y_position), line, fill='black', font=font)
                        y_position += 30
                        line = word + " "
                if line:
                    draw.text((50, y_position), line, fill='black', font=font)
                
                img.save(output_path, format=image_format.upper())
                return True
            
            return False
            
        except Exception as e:
            print(f"PDF to image conversion error: {e}")
            return False
