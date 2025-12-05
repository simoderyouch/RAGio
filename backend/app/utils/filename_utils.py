"""
Filename utilities for normalizing and validating file names.
Ensures consistent, safe file names across the application.
"""

import os
import re
import unicodedata
from datetime import datetime
from typing import Tuple, Optional


def normalize_filename(filename: str, preserve_extension: bool = True) -> str:
    """
    Normalize a filename to be safe and consistent.
    
    - Removes/replaces unsafe characters
    - Handles unicode normalization (NFD → NFC)
    - Trims whitespace
    - Preserves extension
    - Never returns generic names like 'file1' or 'document'
    
    Args:
        filename: The original filename
        preserve_extension: Whether to keep the file extension
        
    Returns:
        Normalized filename
    """
    if not filename or not filename.strip():
        # Generate timestamp-based name only as absolute fallback
        return f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Strip whitespace
    filename = filename.strip()
    
    # Normalize unicode (convert decomposed chars to composed)
    filename = unicodedata.normalize('NFC', filename)
    
    # Split name and extension
    name, ext = os.path.splitext(filename)
    
    # Clean the name part
    name = name.strip()
    
    # Replace problematic characters with underscores
    # Keep: letters, numbers, underscores, hyphens, spaces, dots (internal)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    
    # Replace multiple spaces/underscores with single underscore
    name = re.sub(r'[\s_]+', '_', name)
    
    # Remove leading/trailing underscores and dots
    name = name.strip('_.')
    
    # Ensure name is not empty after cleaning
    if not name:
        name = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Check for generic/invalid names and reject them
    generic_patterns = [
        r'^file\d*$',
        r'^document\s*\d*$',
        r'^untitled\d*$',
        r'^new\s*file\d*$',
        r'^\d+$',  # Just numbers
    ]
    
    name_lower = name.lower().replace('_', ' ').replace('-', ' ')
    for pattern in generic_patterns:
        if re.match(pattern, name_lower):
            # Don't replace with generic - keep original but mark it
            name = f"uploaded_{name}_{datetime.now().strftime('%H%M%S')}"
            break
    
    # Normalize extension
    if preserve_extension and ext:
        ext = ext.lower().strip()
        # Ensure extension starts with dot
        if not ext.startswith('.'):
            ext = '.' + ext
        return f"{name}{ext}"
    
    return name


def extract_file_info(filename: str) -> Tuple[str, str, str]:
    """
    Extract file information from a filename.
    
    Args:
        filename: The filename to parse
        
    Returns:
        Tuple of (normalized_name, extension, original_name)
    """
    original = filename
    normalized = normalize_filename(filename)
    _, ext = os.path.splitext(normalized)
    
    return normalized, ext.lstrip('.').upper(), original


def sanitize_for_metadata(filename: str) -> str:
    """
    Sanitize filename for use in metadata/payloads.
    More aggressive cleaning for JSON/database storage.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        Sanitized filename safe for metadata
    """
    if not filename:
        return "unknown"
    
    # First normalize
    clean = normalize_filename(filename)
    
    # Remove any remaining problematic chars for JSON
    clean = re.sub(r'[^\w\s\-_.]', '', clean)
    
    # Limit length
    if len(clean) > 200:
        name, ext = os.path.splitext(clean)
        clean = name[:195] + ext
    
    return clean


def validate_filename(filename: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a filename is acceptable.
    
    Args:
        filename: The filename to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename or not filename.strip():
        return False, "Filename cannot be empty"
    
    # Check length
    if len(filename) > 255:
        return False, "Filename too long (max 255 characters)"
    
    # Check for path traversal attempts
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        return False, "Invalid filename: path traversal detected"
    
    # Check for null bytes
    if '\x00' in filename:
        return False, "Invalid filename: null bytes detected"
    
    return True, None


def generate_unique_filename(original: str, existing_names: set = None) -> str:
    """
    Generate a unique filename, adding suffix if needed.
    
    Args:
        original: The original filename
        existing_names: Set of existing filenames to avoid collision
        
    Returns:
        Unique filename
    """
    normalized = normalize_filename(original)
    
    if existing_names is None:
        return normalized
    
    if normalized not in existing_names:
        return normalized
    
    # Add counter suffix
    name, ext = os.path.splitext(normalized)
    counter = 1
    
    while True:
        new_name = f"{name}_{counter}{ext}"
        if new_name not in existing_names:
            return new_name
        counter += 1
        
        # Safety limit
        if counter > 1000:
            return f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

