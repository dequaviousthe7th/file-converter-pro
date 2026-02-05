"""
Markdown Converter Module
Handles conversions from Markdown to other formats
"""

import os
import re
from pathlib import Path

try:
    import pypandoc
    PYPANDOC_AVAILABLE = True
except ImportError:
    PYPANDOC_AVAILABLE = False

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

# WeasyPrint - only try to import, don't fail if it's not properly installed
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except Exception:
    # Catch all exceptions including OSError for missing system libs
    WEASYPRINT_AVAILABLE = False

# Windows alternative for Markdown to PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from docx import Document
    from docx.shared import Pt
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False


class MarkdownConverter:
    """Convert Markdown files to various formats"""
    
    SUPPORTED_OUTPUTS = ['pdf', 'docx', 'txt', 'html']
    
    def convert(self, input_path: str, output_path: str, target_format: str) -> bool:
        """Convert Markdown to target format"""
        if target_format == 'pdf':
            return self._to_pdf(input_path, output_path)
        elif target_format == 'docx':
            return self._to_docx(input_path, output_path)
        elif target_format == 'html':
            return self._to_html(input_path, output_path)
        elif target_format == 'txt':
            return self._to_text(input_path, output_path)
        else:
            raise ValueError(f"Unsupported target format: {target_format}")
    
    def _to_pdf(self, input_path: str, output_path: str) -> bool:
        """Convert Markdown to PDF"""
        # Try WeasyPrint first if available
        if WEASYPRINT_AVAILABLE:
            try:
                return self._to_pdf_weasyprint(input_path, output_path)
            except Exception as e:
                print(f"WeasyPrint failed, trying fallback: {e}")
        
        # Fall back to ReportLab
        if REPORTLAB_AVAILABLE:
            return self._to_pdf_reportlab(input_path, output_path)
        
        # Last resort: pypandoc
        if PYPANDOC_AVAILABLE:
            return self._convert_with_pandoc(input_path, output_path, 'pdf')
        
        raise ImportError("No PDF library available")

    def _to_pdf_reportlab(self, input_path: str, output_path: str) -> bool:
        """Convert Markdown to PDF using ReportLab (Windows-friendly)"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Simple markdown to text conversion
            text = md_content
            text = re.sub(r'#{1,6}\s+', '', text)  # Headers
            text = re.sub(r'\*\*|\*|__|_', '', text)  # Bold/italic
            text = re.sub(r'`', '', text)  # Code
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
            text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'[Image: \1]', text)  # Images
            
            # Create PDF with ReportLab
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Add title
            title = Paragraph("Converted Document", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Add content paragraphs
            for paragraph in text.split('\n\n'):
                if paragraph.strip():
                    p = Paragraph(paragraph.replace('\n', '<br/>'), styles['Normal'])
                    story.append(p)
                    story.append(Spacer(1, 12))
            
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"ReportLab PDF conversion error: {e}")
            return False

    def _to_pdf_weasyprint(self, input_path: str, output_path: str) -> bool:
        """Convert Markdown to PDF using WeasyPrint"""
        with open(input_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        html_content = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'toc', 'nl2br']
        )
        
        css_style = """
        <style>
            @page { margin: 2cm; size: A4; }
            body { font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.6; }
            h1 { font-size: 24pt; color: #1a1a1a; }
            h2 { font-size: 18pt; color: #2a2a2a; }
            code { background: #f4f4f4; padding: 2px 6px; }
            pre { background: #f4f4f4; padding: 16px; }
        </style>
        """
        
        full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">{css_style}</head>
<body>{html_content}</body></html>"""
        
        HTML(string=full_html).write_pdf(output_path)
        return True
    
    def _to_docx(self, input_path: str, output_path: str) -> bool:
        """Convert Markdown to DOCX"""
        if PYPANDOC_AVAILABLE:
            return self._convert_with_pandoc(input_path, output_path, 'docx')
        
        if not PYTHON_DOCX_AVAILABLE:
            raise ImportError("python-docx not installed")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        doc = Document()
        
        for line in md_content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:], level=3)
            else:
                doc.add_paragraph(line)
        
        doc.save(output_path)
        return True
    
    def _to_html(self, input_path: str, output_path: str) -> bool:
        """Convert Markdown to HTML"""
        if not MARKDOWN_AVAILABLE:
            raise ImportError("markdown library not installed")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
        
        full_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Converted</title></head>
<body>{html_content}</body></html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        return True
    
    def _to_text(self, input_path: str, output_path: str) -> bool:
        """Convert Markdown to plain text"""
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Strip markdown syntax
        content = re.sub(r'```[\s\S]*?```', '', content)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'\*\*|__|\*|_', '', content)
        content = re.sub(r'^>\s?', '', content, flags=re.MULTILINE)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    
    def _convert_with_pandoc(self, input_path: str, output_path: str, target_format: str) -> bool:
        """Convert using pypandoc"""
        pypandoc.convert_file(input_path, target_format, outputfile=output_path)
        return True
