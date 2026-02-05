"""
File Converter Backend - FastAPI Application
Main entry point for the file conversion API
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from converters.pdf_converter import PDFConverter
from converters.word_converter import WordConverter
from converters.markdown_converter import MarkdownConverter
from converters.image_converter import ImageConverter
from converters.text_converter import TextConverter

# Configuration
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
CONVERTED_DIR = BASE_DIR / "converted"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
CONVERTED_DIR.mkdir(exist_ok=True)

# Supported formats mapping
SUPPORTED_FORMATS = {
    'pdf': {
        'converters': ['docx', 'txt', 'md', 'png', 'jpg'],
        'mime': 'application/pdf',
        'icon': '📄'
    },
    'docx': {
        'converters': ['pdf', 'txt', 'md'],
        'mime': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'icon': '📝'
    },
    'md': {
        'converters': ['pdf', 'docx', 'txt', 'html'],
        'mime': 'text/markdown',
        'icon': '📑'
    },
    'txt': {
        'converters': ['pdf', 'docx', 'md'],
        'mime': 'text/plain',
        'icon': '📃'
    },
    'png': {
        'converters': ['pdf', 'jpg', 'webp', 'bmp'],
        'mime': 'image/png',
        'icon': '🖼️'
    },
    'jpg': {
        'converters': ['pdf', 'png', 'webp', 'bmp'],
        'mime': 'image/jpeg',
        'icon': '🖼️'
    },
    'jpeg': {
        'converters': ['pdf', 'png', 'webp', 'bmp'],
        'mime': 'image/jpeg',
        'icon': '🖼️'
    },
    'webp': {
        'converters': ['pdf', 'png', 'jpg', 'bmp'],
        'mime': 'image/webp',
        'icon': '🖼️'
    },
    'bmp': {
        'converters': ['pdf', 'png', 'jpg', 'webp'],
        'mime': 'image/bmp',
        'icon': '🖼️'
    },
    'html': {
        'converters': ['pdf', 'md'],
        'mime': 'text/html',
        'icon': '🌐'
    }
}

app = FastAPI(
    title="File Converter API",
    description="Professional file conversion service supporting PDF, Word, Markdown, Images, and more",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for converted downloads
app.mount("/files", StaticFiles(directory=str(CONVERTED_DIR)), name="files")


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    return Path(filename).suffix.lower().lstrip('.')


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file"""
    if not file.filename:
        return False, "No filename provided"
    
    ext = get_file_extension(file.filename)
    if ext not in SUPPORTED_FORMATS:
        return False, f"Unsupported file format: {ext}"
    
    return True, ""


def cleanup_old_files():
    """Clean up files older than 1 hour"""
    try:
        current_time = datetime.now().timestamp()
        for directory in [UPLOAD_DIR, CONVERTED_DIR]:
            for file_path in directory.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > 3600:  # 1 hour
                        file_path.unlink()
    except Exception as e:
        print(f"Cleanup error: {e}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "File Converter API",
        "version": "1.0.0",
        "supported_formats": list(SUPPORTED_FORMATS.keys())
    }


@app.get("/formats")
async def get_formats():
    """Get all supported formats and their conversion options"""
    return SUPPORTED_FORMATS


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for conversion"""
    is_valid, error_msg = validate_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Generate unique filename
    file_id = str(uuid.uuid4())[:8]
    ext = get_file_extension(file.filename)
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            file_path.unlink()
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")
        
        return {
            "success": True,
            "file_id": file_id,
            "original_name": file.filename,
            "stored_name": safe_filename,
            "extension": ext,
            "size": file_size,
            "available_conversions": SUPPORTED_FORMATS[ext]['converters']
        }
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/convert")
async def convert_file(
    background_tasks: BackgroundTasks,
    stored_name: str,
    target_format: str
):
    """Convert an uploaded file to target format"""
    source_path = UPLOAD_DIR / stored_name
    
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found")
    
    source_ext = get_file_extension(stored_name)
    
    # Validate conversion
    if source_ext not in SUPPORTED_FORMATS:
        raise HTTPException(status_code=400, detail="Unsupported source format")
    
    if target_format not in SUPPORTED_FORMATS[source_ext]['converters']:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot convert {source_ext} to {target_format}"
        )
    
    # Generate output filename
    base_name = Path(stored_name).stem
    output_name = f"{base_name}_converted.{target_format}"
    output_path = CONVERTED_DIR / output_name
    
    try:
        # Select and execute converter
        converter = None
        
        if source_ext == 'pdf':
            converter = PDFConverter()
        elif source_ext == 'docx':
            converter = WordConverter()
        elif source_ext == 'md':
            converter = MarkdownConverter()
        elif source_ext in ['png', 'jpg', 'jpeg', 'webp', 'bmp']:
            converter = ImageConverter()
        elif source_ext == 'txt':
            converter = TextConverter()
        elif source_ext == 'html':
            converter = MarkdownConverter()
        
        if not converter:
            raise HTTPException(status_code=400, detail="No converter available")
        
        # Perform conversion
        success = converter.convert(str(source_path), str(output_path), target_format)
        
        if not success:
            raise HTTPException(status_code=500, detail="Conversion failed")
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_old_files)
        
        return {
            "success": True,
            "message": f"File converted successfully",
            "original_name": stored_name,
            "converted_name": output_name,
            "download_url": f"/download/{output_name}",
            "source_format": source_ext,
            "target_format": target_format
        }
        
    except Exception as e:
        if output_path.exists():
            output_path.unlink()
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a converted file"""
    file_path = CONVERTED_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    ext = get_file_extension(filename)
    media_type = SUPPORTED_FORMATS.get(ext, {}).get('mime', 'application/octet-stream')
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )


@app.delete("/files/{filename}")
async def delete_file(filename: str, directory: str = "converted"):
    """Delete a file from uploads or converted directory"""
    if directory == "uploads":
        file_path = UPLOAD_DIR / filename
    else:
        file_path = CONVERTED_DIR / filename
    
    if file_path.exists():
        file_path.unlink()
        return {"success": True, "message": "File deleted"}
    
    raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
