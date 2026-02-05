"""
Word Converter Module
Handles conversions from DOCX to other formats
"""

import os
import re
from pathlib import Path

try:
    from docx import Document
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False

try:
    import docx2pdf
    DOCX2PDF_AVAILABLE = True
except ImportError:
    DOCX2PDF_AVAILABLE = False


class WordConverter:
    """Convert Word (DOCX) files to various formats"""
    
    SUPPORTED_OUTPUTS = ['pdf', 'txt', 'md']
    
    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        """
        Convert DOCX to target format
        
        Args:
            input_path: Path to input DOCX file
            output_path: Path to output file
            target_format: Target format extension
            
        Returns:
            bool: True if conversion successful
        """
        if target_format == 'pdf':
            return self._to_pdf(input_path, output_path)
        elif target_format in ['txt', 'md']:
            return self._to_text(input_path, output_path, target_format)
        else:
            raise ValueError(f"Unsupported target format: {target_format}")
    
    def _to_pdf(self, input_path: str, output_path: str) -> bool:
        """Convert DOCX to PDF"""
        if not DOCX2PDF_AVAILABLE:
            raise ImportError("docx2pdf library not installed")
        
        try:
            docx2pdf.convert(input_path, output_path)
            return True
        except Exception as e:
            print(f"DOCX to PDF conversion error: {e}")
            # Fallback: try using LibreOffice
            return self._convert_with_libreoffice(input_path, output_path)
    
    def _convert_with_libreoffice(self, input_path: str, output_path: str) -> bool:
        """Fallback conversion using LibreOffice command line"""
        try:
            import subprocess
            output_dir = os.path.dirname(output_path)
            cmd = [
                'libreoffice', '--headless', '--convert-to', 'pdf',
                '--outdir', output_dir, input_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # Rename the output file if needed
                base_name = Path(input_path).stem
                expected_output = os.path.join(output_dir, f"{base_name}.pdf")
                if os.path.exists(expected_output) and expected_output != output_path:
                    os.rename(expected_output, output_path)
                return True
            return False
        except Exception as e:
            print(f"LibreOffice conversion error: {e}")
            return False
    
    def _to_text(self, input_path: str, output_path: str, format_type: str) -> bool:
        """Convert DOCX to text or markdown"""
        if not PYTHON_DOCX_AVAILABLE:
            raise ImportError("python-docx library not installed")
        
        try:
            doc = Document(input_path)
            content_parts = []
            
            # Process paragraphs with style information
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                if format_type == 'md':
                    # Apply markdown formatting based on style
                    style_name = para.style.name.lower() if para.style else ""
                    
                    if 'heading 1' in style_name or para.style.name.startswith('Heading 1'):
                        content_parts.append(f"# {text}")
                    elif 'heading 2' in style_name or para.style.name.startswith('Heading 2'):
                        content_parts.append(f"## {text}")
                    elif 'heading 3' in style_name or para.style.name.startswith('Heading 3'):
                        content_parts.append(f"### {text}")
                    elif 'heading' in style_name:
                        level = re.search(r'\d+', style_name)
                        if level:
                            hashes = '#' * min(int(level.group()), 6)
                            content_parts.append(f"{hashes} {text}")
                        else:
                            content_parts.append(f"## {text}")
                    else:
                        # Check for bold/italic in runs
                        formatted_text = ""
                        for run in para.runs:
                            run_text = run.text
                            if run.bold and run.italic:
                                run_text = f"***{run_text}***"
                            elif run.bold:
                                run_text = f"**{run_text}**"
                            elif run.italic:
                                run_text = f"*{run_text}*"
                            formatted_text += run_text
                        
                        content_parts.append(formatted_text if formatted_text else text)
                else:
                    content_parts.append(text)
            
            # Process tables
            for table in doc.tables:
                if format_type == 'md':
                    content_parts.append("\n")  # Add spacing before table
                    
                    # Convert table to markdown
                    for i, row in enumerate(table.rows):
                        row_text = "| " + " | ".join(
                            cell.text.strip().replace('\n', ' ') for cell in row.cells
                        ) + " |"
                        content_parts.append(row_text)
                        
                        # Add separator after header row
                        if i == 0:
                            separator = "|" + "|".join(
                                " --- " for _ in row.cells
                            ) + "|"
                            content_parts.append(separator)
                    
                    content_parts.append("\n")  # Add spacing after table
                else:
                    # Plain text table
                    for row in table.rows:
                        row_text = " | ".join(
                            cell.text.strip() for cell in row.cells
                        )
                        content_parts.append(row_text)
                    content_parts.append("-" * 50)
            
            full_content = "\n\n".join(content_parts)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            return True
            
        except Exception as e:
            print(f"DOCX to text conversion error: {e}")
            return False
