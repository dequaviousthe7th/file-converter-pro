/**
 * File Converter Pro - Frontend Application
 * Handles drag-drop, file upload, conversion, and download functionality
 */

// Configuration
const API_BASE_URL = 'http://localhost:8000';
const SUPPORTED_FORMATS = {
    'pdf': { icon: '📄', name: 'PDF', color: '#EF4444' },
    'docx': { icon: '📝', name: 'Word', color: '#3B82F6' },
    'md': { icon: '📑', name: 'Markdown', color: '#8B5CF6' },
    'txt': { icon: '📃', name: 'Text', color: '#6B7280' },
    'png': { icon: '🖼️', name: 'PNG', color: '#10B981' },
    'jpg': { icon: '🖼️', name: 'JPG', color: '#10B981' },
    'jpeg': { icon: '🖼️', name: 'JPEG', color: '#10B981' },
    'webp': { icon: '🖼️', name: 'WebP', color: '#10B981' },
    'bmp': { icon: '🖼️', name: 'BMP', color: '#10B981' },
    'html': { icon: '🌐', name: 'HTML', color: '#F59E0B' }
};

// State
let uploadedFiles = [];
let availableFormats = [];
let selectedTargetFormat = 'pdf';
let isConverting = false;

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadSection = document.getElementById('uploadSection');
const filesSection = document.getElementById('filesSection');
const filesList = document.getElementById('filesList');
const convertSection = document.getElementById('convertSection');
const formatSelector = document.getElementById('formatSelector');
const convertBtn = document.getElementById('convertBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultsSection = document.getElementById('resultsSection');
const resultsList = document.getElementById('resultsList');
const clearAllBtn = document.getElementById('clearAllBtn');
const convertMoreBtn = document.getElementById('convertMoreBtn');
const serverStatus = document.getElementById('serverStatus');
const toastContainer = document.getElementById('toastContainer');

// Initialize
function init() {
    setupEventListeners();
    checkServerStatus();
    loadSupportedFormats();
}

// Event Listeners
function setupEventListeners() {
    // Drag and Drop
    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('dragleave', handleDragLeave);
    dropZone.addEventListener('drop', handleDrop);
    dropZone.addEventListener('click', () => fileInput.click());
    
    // File Input
    fileInput.addEventListener('change', handleFileSelect);
    
    // Format Selection
    formatSelector.addEventListener('click', handleFormatSelect);
    
    // Convert Button
    convertBtn.addEventListener('click', startConversion);
    
    // Clear/Reset Buttons
    clearAllBtn.addEventListener('click', clearAllFiles);
    convertMoreBtn.addEventListener('click', resetForNewConversion);
}

// Drag and Drop Handlers
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('dragover');
    
    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    processFiles(files);
}

// File Processing
function processFiles(files) {
    if (files.length === 0) return;
    
    // Filter supported files
    const supportedFiles = files.filter(file => {
        const ext = getFileExtension(file.name);
        return SUPPORTED_FORMATS[ext] !== undefined;
    });
    
    if (supportedFiles.length === 0) {
        showToast('error', 'Unsupported Files', 'Please upload PDF, Word, Markdown, Image, or Text files.');
        return;
    }
    
    if (supportedFiles.length !== files.length) {
        showToast('warning', 'Some Files Skipped', `${files.length - supportedFiles.length} unsupported file(s) were skipped.`);
    }
    
    // Upload each file
    supportedFiles.forEach(file => uploadFile(file));
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const data = await response.json();
        
        const fileInfo = {
            id: data.file_id,
            originalName: data.original_name,
            storedName: data.stored_name,
            extension: data.extension,
            size: data.size,
            availableConversions: data.available_conversions,
            status: 'ready'
        };
        
        uploadedFiles.push(fileInfo);
        updateUI();
        showToast('success', 'File Uploaded', `${file.name} is ready for conversion.`);
        
    } catch (error) {
        console.error('Upload error:', error);
        showToast('error', 'Upload Failed', error.message);
    }
}

// UI Updates
function updateUI() {
    if (uploadedFiles.length === 0) {
        filesSection.style.display = 'none';
        convertSection.style.display = 'none';
        return;
    }
    
    filesSection.style.display = 'block';
    convertSection.style.display = 'block';
    
    renderFilesList();
    updateFormatSelector();
}

function renderFilesList() {
    filesList.innerHTML = uploadedFiles.map(file => `
        <div class="file-item" data-id="${file.id}">
            <div class="file-icon">${SUPPORTED_FORMATS[file.extension]?.icon || '📄'}</div>
            <div class="file-info">
                <div class="file-name">${escapeHtml(file.originalName)}</div>
                <div class="file-meta">${formatFileSize(file.size)} • ${file.extension.toUpperCase()}</div>
            </div>
            <div class="file-status ${file.status}">
                ${getStatusIcon(file.status)}
            </div>
            <div class="file-actions">
                <button class="btn-icon" onclick="removeFile('${file.id}')" title="Remove">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
        </div>
    `).join('');
}

function updateFormatSelector() {
    // Get common available conversions across all files
    if (uploadedFiles.length === 0) return;
    
    let commonFormats = new Set(uploadedFiles[0].availableConversions);
    
    for (let i = 1; i < uploadedFiles.length; i++) {
        const fileFormats = new Set(uploadedFiles[i].availableConversions);
        commonFormats = new Set([...commonFormats].filter(x => fileFormats.has(x)));
    }
    
    availableFormats = Array.from(commonFormats);
    
    // Update button states
    const buttons = formatSelector.querySelectorAll('.format-btn');
    buttons.forEach(btn => {
        const format = btn.dataset.format;
        const isAvailable = availableFormats.includes(format);
        btn.disabled = !isAvailable;
        
        if (!isAvailable) {
            btn.classList.remove('active');
        } else if (format === selectedTargetFormat) {
            btn.classList.add('active');
        }
    });
    
    // If current selection is not available, select first available
    if (!availableFormats.includes(selectedTargetFormat) && availableFormats.length > 0) {
        selectedTargetFormat = availableFormats[0];
        updateActiveFormatButton();
    }
}

function updateActiveFormatButton() {
    const buttons = formatSelector.querySelectorAll('.format-btn');
    buttons.forEach(btn => {
        if (btn.dataset.format === selectedTargetFormat) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

function handleFormatSelect(e) {
    const btn = e.target.closest('.format-btn');
    if (!btn || btn.disabled) return;
    
    selectedTargetFormat = btn.dataset.format;
    updateActiveFormatButton();
}

// Conversion
async function startConversion() {
    if (uploadedFiles.length === 0 || isConverting) return;
    
    isConverting = true;
    convertBtn.disabled = true;
    convertBtn.innerHTML = `
        <div class="progress-spinner" style="width: 16px; height: 16px; border-width: 2px;"></div>
        Converting...
    `;
    
    // Show progress section
    filesSection.style.display = 'none';
    convertSection.style.display = 'none';
    progressSection.style.display = 'block';
    resultsSection.style.display = 'none';
    
    const results = [];
    const totalFiles = uploadedFiles.length;
    
    for (let i = 0; i < uploadedFiles.length; i++) {
        const file = uploadedFiles[i];
        
        // Update progress
        progressText.textContent = `Processing ${i + 1} of ${totalFiles} files`;
        progressFill.style.width = `${((i) / totalFiles) * 100}%`;
        
        try {
            const result = await convertFile(file);
            results.push({ ...file, ...result, status: 'success' });
        } catch (error) {
            results.push({ ...file, error: error.message, status: 'error' });
        }
    }
    
    // Complete progress
    progressFill.style.width = '100%';
    
    // Show results after brief delay
    setTimeout(() => {
        showResults(results);
    }, 500);
}

async function convertFile(file) {
    const response = await fetch(`${API_BASE_URL}/convert`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            stored_name: file.storedName,
            target_format: selectedTargetFormat
        })
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Conversion failed');
    }
    
    return await response.json();
}

function showResults(results) {
    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';
    
    const successCount = results.filter(r => r.status === 'success').length;
    
    resultsList.innerHTML = results.map(result => `
        <div class="result-item">
            <div class="result-icon">
                ${result.status === 'success' 
                    ? `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                       </svg>`
                    : `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="15" y1="9" x2="9" y2="15"/>
                        <line x1="9" y1="9" x2="15" y2="15"/>
                       </svg>`
                }
            </div>
            <div class="result-info">
                <div class="result-name">${escapeHtml(result.originalName)}</div>
                <div class="result-meta">
                    ${result.status === 'success' 
                        ? `Converted to ${selectedTargetFormat.toUpperCase()}` 
                        : `Error: ${escapeHtml(result.error)}`
                    }
                </div>
            </div>
            ${result.status === 'success' ? `
                <a href="${API_BASE_URL}${result.download_url}" 
                   download 
                   class="btn-secondary">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Download
                </a>
            ` : ''}
        </div>
    `).join('');
    
    if (successCount > 0) {
        showToast('success', 'Conversion Complete!', `${successCount} file(s) converted successfully.`);
    }
    
    isConverting = false;
    convertBtn.disabled = false;
    convertBtn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 0 1-9 9m9-9a9 9 0 0 0-9-9m9 9H3m9 9a9 9 0 0 1-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 0 1 9-9"/>
        </svg>
        Convert Files
    `;
}

function resetForNewConversion() {
    uploadedFiles = [];
    selectedTargetFormat = 'pdf';
    isConverting = false;
    
    uploadSection.style.display = 'block';
    filesSection.style.display = 'none';
    convertSection.style.display = 'none';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    
    fileInput.value = '';
    updateActiveFormatButton();
}

function clearAllFiles() {
    uploadedFiles = [];
    updateUI();
    fileInput.value = '';
}

function removeFile(id) {
    uploadedFiles = uploadedFiles.filter(f => f.id !== id);
    updateUI();
}

// Utilities
function getFileExtension(filename) {
    return filename.split('.').pop().toLowerCase();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getStatusIcon(status) {
    switch (status) {
        case 'ready':
            return 'Ready';
        case 'processing':
            return 'Processing...';
        case 'success':
            return '✓ Done';
        case 'error':
            return '✗ Failed';
        default:
            return '';
    }
}

// Toast Notifications
function showToast(type, title, message) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const iconSvg = {
        success: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
        error: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        warning: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        info: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">${iconSvg[type]}</div>
        <div class="toast-content">
            <div class="toast-title">${escapeHtml(title)}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        </button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 250);
    }, 5000);
}

// Server Status
async function checkServerStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/`, { method: 'GET' });
        if (response.ok) {
            serverStatus.textContent = 'Online';
            serverStatus.className = 'status-online';
        } else {
            throw new Error('Server error');
        }
    } catch (error) {
        serverStatus.textContent = 'Offline - Start the server';
        serverStatus.className = 'status-offline';
    }
}

async function loadSupportedFormats() {
    try {
        const response = await fetch(`${API_BASE_URL}/formats`);
        if (response.ok) {
            const formats = await response.json();
            console.log('Supported formats loaded:', formats);
        }
    } catch (error) {
        console.warn('Could not load supported formats');
    }
}

// Global function for inline onclick handlers
window.removeFile = removeFile;

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', init);
