"""
File format validation utilities for CSV, TXT, and MD files.
Provides robust validation to ensure file integrity and correct format.
"""

import io
from typing import Tuple, Optional


def validate_md(file_content: bytes) -> Tuple[bool, Optional[str]]:
    """
    Validate Markdown file format.
    Basic validation: checks if file is readable text.
    
    Args:
        file_content: The file content as bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_content:
        return False, "File is empty"
    
    try:
        # Try to decode as UTF-8 (most common encoding for Markdown)
        try:
            text = file_content.decode('utf-8')
        except UnicodeDecodeError:
            # Try other common encodings
            try:
                text = file_content.decode('latin-1')
            except UnicodeDecodeError:
                return False, "Markdown file contains invalid characters (not UTF-8 or Latin-1)"
        
        # Check if file has some content
        if not text.strip():
            return False, "Markdown file is empty or contains only whitespace"
        
        return True, None
    except Exception as e:
        return False, f"Error validating Markdown: {str(e)}"


def validate_csv(file_content: bytes) -> Tuple[bool, Optional[str]]:
    """
    Validate CSV file format.
    Basic validation: checks if file is readable text and has some structure.
    
    Args:
        file_content: The file content as bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_content:
        return False, "File is empty"
    
    try:
        # Try to decode as UTF-8 (most common encoding for CSV)
        try:
            text = file_content.decode('utf-8')
        except UnicodeDecodeError:
            # Try other common encodings
            try:
                text = file_content.decode('latin-1')
            except UnicodeDecodeError:
                return False, "CSV file contains invalid characters (not UTF-8 or Latin-1)"
        
        # Check if file has at least one line
        lines = text.strip().split('\n')
        if not lines or not any(line.strip() for line in lines):
            return False, "CSV file is empty or contains no data"
        
        # Check if file has some structure (at least one delimiter)
        # Common CSV delimiters: comma, semicolon, tab
        has_delimiter = any(
            ',' in line or ';' in line or '\t' in line
            for line in lines[:10]  # Check first 10 lines
        )
        
        if not has_delimiter and len(lines) > 1:
            return False, "CSV file does not appear to have proper delimiter structure"
        
        return True, None
    except Exception as e:
        return False, f"Error validating CSV: {str(e)}"


def validate_txt(file_content: bytes) -> Tuple[bool, Optional[str]]:
    """
    Validate TXT file format.
    Basic validation: checks if file is readable text.
    
    Args:
        file_content: The file content as bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_content:
        return False, "File is empty"
    
    try:
        # Try to decode as UTF-8 (most common encoding for TXT)
        try:
            text = file_content.decode('utf-8')
        except UnicodeDecodeError:
            # Try other common encodings
            try:
                text = file_content.decode('latin-1')
            except UnicodeDecodeError:
                # For TXT, we're more lenient - allow binary if it's small
                if len(file_content) < 1000:
                    return True, None  # Small binary file might be acceptable
                return False, "TXT file contains invalid characters (not UTF-8 or Latin-1)"
        
        # Check if file has some content
        if not text.strip():
            return False, "TXT file is empty or contains only whitespace"
        
        return True, None
    except Exception as e:
        return False, f"Error validating TXT: {str(e)}"


def validate_file_format(file_content: bytes, file_extension: str) -> Tuple[bool, Optional[str]]:
    """
    Validate file format based on extension.
    
    Args:
        file_content: The file content as bytes
        file_extension: The file extension (lowercase, without dot)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    extension = file_extension.lower().lstrip('.')
    
    validators = {
        'csv': validate_csv,
        'txt': validate_txt,
        'md': validate_md,
    }
    
    validator = validators.get(extension)
    if not validator:
        # If no validator, assume valid (for other formats)
        return True, None
    
    return validator(file_content)

