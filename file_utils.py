import datetime
import os
from typing import Optional


def generate_timestamped_filename(base_name: str, 
                                extension: str = ".xml",
                                directory: str = "data",
                                timestamp_format: str = "%Y%m%d_%H%M%S") -> str:
    """
    Generate a timestamped filename to avoid overwriting previous files.
    
    Args:
        base_name: Base name for the file (e.g., "dividends_furs")
        extension: File extension (default: ".xml")
        directory: Directory to save in (default: "data")
        timestamp_format: Format for timestamp (default: YYYYMMDD_HHMMSS)
        
    Returns:
        Full path with timestamp
    """
    timestamp = datetime.datetime.now().strftime(timestamp_format)
    filename = f"{base_name}_{timestamp}{extension}"
    return os.path.join(directory, filename)


def get_output_filename(user_specified: Optional[str],
                       default_base: str,
                       file_type: str = "tax report",
                       use_timestamp: bool = True) -> str:
    """
    Get the output filename, either user-specified or auto-generated with timestamp.
    
    Args:
        user_specified: User-specified filename (from --output flag)
        default_base: Default base name for the file
        file_type: Description of file type for logging
        use_timestamp: Whether to add timestamp to default filename
        
    Returns:
        Final output filename to use
    """
    if user_specified:
        print(f"Using user-specified output file: {user_specified}")
        return user_specified
    elif use_timestamp:
        timestamped_file = generate_timestamped_filename(default_base)
        print(f"Generated timestamped {file_type} file: {timestamped_file}")
        return timestamped_file
    else:
        simple_file = os.path.join("data", f"{default_base}.xml")
        print(f"Using default {file_type} file: {simple_file}")
        return simple_file


def ensure_directory_exists(file_path: str):
    """
    Ensure the directory for a file path exists, creating it if necessary.
    
    Args:
        file_path: Path to a file
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")


def backup_existing_file(file_path: str) -> Optional[str]:
    """
    If a file already exists, create a backup with timestamp.
    
    Args:
        file_path: Path to the file that might be overwritten
        
    Returns:
        Path to backup file if created, None if no backup was needed
    """
    if os.path.exists(file_path):
        # Extract directory, base name, and extension
        directory = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        
        # Split extension
        if '.' in base_name:
            name_part, ext_part = base_name.rsplit('.', 1)
            ext_part = '.' + ext_part
        else:
            name_part = base_name
            ext_part = ''
        
        # Generate backup filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name_part}_backup_{timestamp}{ext_part}"
        backup_path = os.path.join(directory, backup_name)
        
        # Create backup
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"Backed up existing file to: {backup_path}")
        return backup_path
    
    return None