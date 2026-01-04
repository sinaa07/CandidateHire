from pathlib import Path
from pypdf import PdfReader
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
    try:
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            if len(reader.pages) == 0:
                raise ValueError("PDF has no pages")
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text.append(page_text.strip())
        result = ' '.join(text).strip()
        # If result is empty or only whitespace, PDF might be image-based
        if not result:
            raise ValueError("PDF appears to be image-based (no extractable text). OCR required.")
        return result
    except Exception as e:
        if "image-based" in str(e).lower() or "no extractable text" in str(e).lower():
            raise
        raise Exception(f"PDF extraction error: {str(e)}") from e

def _extract_docx(file_path: Path) -> str:
    try:
        doc = Document(file_path)
        text = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
        result = ' '.join(text).strip()
        if not result:
            raise ValueError("DOCX file appears to be empty or contains no extractable text")
        return result
    except Exception as e:
        if "empty" in str(e).lower() or "no extractable text" in str(e).lower():
            raise
        raise Exception(f"DOCX extraction error: {str(e)}") from e

def _extract_txt(file_path: Path) -> str:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read().strip()