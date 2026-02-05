"""
Text Converter Module
Handles conversions from plain text to other formats
"""

import os
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from docx import Document
    from docx.shared import Pt, Inches as DocxInches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False


class TextConverter:
    """Convert text files to various formats"""
    
    SUPPORTED_OUTPUTS = ['pdf', 'docx', 'md']
    
    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        """
        Convert text to target format
        
        Args:
            input_path: Path to input text file
            output_path: Path to output file
            target_format: Target format extension
            
        Returns:
            bool: True if conversion successful
        """
        if target_format == 'pdf':
            return self._to_pdf(input_path, output_path)
        elif target_format == 'docx':
            return self._to_docx(input_path, output_path)
        elif target_format == 'md':
            return self._to_markdown(input_path, output_path)
        else:
            raise ValueError(f"Unsupported target format: {target_format}")
    
    def _to_pdf(self, input_path: str, output_path: str) -> bool:
        """Convert text to PDF"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab library not installed")
        
        try:
            # Read text content
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Container for the 'Flowable' objects
            story = []
            
            # Get styles
            styles = getSampleStyleSheet()
            normal_style = styles['Normal']
            normal_style.fontSize = 11
            normal_style.leading = 14
            normal_style.wordWrap = True
            
            # Split content into paragraphs
            paragraphs = content.split('\n\n')
            
            for para_text in paragraphs:
                if not para_text.strip():
                    story.append(Spacer(1, 12))
                    continue
                
                # Escape special characters for ReportLab
                para_text = para_text.replace('&', '&amp;')
                para_text = para_text.replace('<', '&lt;')
                para_text = para_text.replace('>', '&gt;')
                
                # Replace newlines with <br/> for ReportLab
                para_text = para_text.replace('\n', '<br/>')
                
                p = Paragraph(para_text, normal_style)
                story.append(p)
                story.append(Spacer(1, 12))
            
            # Build PDF
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"Text to PDF conversion error: {e}")
            return False
    
    def _to_docx(self, input_path: str, output_path: str) -> bool:
        """Convert text to DOCX"""
        if not PYTHON_DOCX_AVAILABLE:
            raise ImportError("python-docx library not installed")
        
        try:
            # Read text content
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create document
            doc = Document()
            
            # Set default font
            style = doc.styles['Normal']
            font = style.font
            font.name = 'Calibri'
            font.size = Pt(11)
            
            # Split content into paragraphs
            paragraphs = content.split('\n\n')
            
            for para_text in paragraphs:
                if not para_text.strip():
                    continue
                
                # Handle single newlines within paragraphs
                lines = para_text.split('\n')
                for i, line in enumerate(lines):
                    p = doc.add_paragraph(line)
                    if i < len(lines) - 1:
                        p.add_run().add_break()
            
            # Save document
            doc.save(output_path)
            return True
            
        except Exception as e:
            print(f"Text to DOCX conversion error: {e}")
            return False
    
    def _to_markdown(self, input_path: str, output_path: str) -> bool:
        """Convert text to Markdown (basic conversion)"""
        try:
            # Read text content
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Add markdown title
            filename = Path(input_path).stem
            md_content = f"# {filename}\n\n"
            
            # Convert paragraphs
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    # Escape markdown special characters
                    para = para.replace('*', '\\*')
                    para = para.replace('_', '\\_')
                    para = para.replace('`', '\\`')
                    md_content += para + "\n\n"
            
            # Write markdown
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            return True
            
        except Exception as e:
            print(f"Text to Markdown conversion error: {e}")
            return False
