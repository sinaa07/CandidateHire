from pathlib import Path
import PyPDF2
from docx import Document

def extract_text(file_path: Path) -> str:
    """
    Extract plain text from resume files.
    
    Returns:
        str: Extracted text (empty string if no text found)
        
    Raises:
        Exception: If file is unreadable or unsupported
    """
    try:
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return _extract_pdf(file_path)
        elif suffix == '.docx':
            return _extract_docx(file_path)
        elif suffix == '.txt':
            return _extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    except Exception as e:
        raise Exception(f"Failed to extract text from {file_path.name}") from e

def _extract_pdf(file_path: Path) -> str:
    text = []
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return ' '.join(text).strip()

def _extract_docx(file_path: Path) -> str:
    doc = Document(file_path)
    text = [paragraph.text for paragraph in doc.paragraphs]
    return ' '.join(text).strip()

def _extract_txt(file_path: Path) -> str:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read().strip()