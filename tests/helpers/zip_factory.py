from pathlib import Path
import zipfile
import os

def make_zip_with_files(tmp_path: Path, files: dict[str, bytes]) -> Path:
    """
    Creates a ZIP file with specified files.
    
    Args:
        tmp_path: Temporary directory path
        files: Mapping of filename to content bytes
        
    Returns:
        Path to created ZIP file
    """
    zip_path = tmp_path / "upload.zip"
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    
    return zip_path

def make_invalid_zip(tmp_path: Path) -> Path:
    """
    Creates a file with .zip extension but invalid content.
    
    Args:
        tmp_path: Temporary directory path
        
    Returns:
        Path to invalid ZIP file
    """
    zip_path = tmp_path / "invalid.zip"
    zip_path.write_bytes(os.urandom(100))
    return zip_path

def make_empty_zip(tmp_path: Path) -> Path:
    """
    Creates a valid ZIP with no files inside.
    
    Args:
        tmp_path: Temporary directory path
        
    Returns:
        Path to empty ZIP file
    """
    zip_path = tmp_path / "empty.zip"
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        pass  # Create empty zip
    
    return zip_path

