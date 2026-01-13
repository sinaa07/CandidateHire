from pathlib import Path
import logging
from pypdf import PdfReader
from docx import Document
import app.core.config as config
from app.utils.ocr_extraction import (
    extract_text_with_ocr,
    should_use_ocr,
    is_ocr_available
)

logger = logging.getLogger(__name__)

def extract_text(file_path: Path, use_ocr_fallback: bool = True) -> str:
    """
    Extract plain text from resume files.
    
    For PDFs, this function:
    1. First attempts regular text extraction
    2. Checks if extracted text is below threshold
    3. Falls back to OCR if needed (when use_ocr_fallback=True)
    
    Args:
        file_path: Path to the file
        use_ocr_fallback: Whether to use OCR as fallback for PDFs (default: True)
    
    Returns:
        str: Extracted text (empty string if no text found)
        
    Raises:
        Exception: If file is unreadable or unsupported
    """
    try:
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return _extract_pdf(file_path, use_ocr_fallback=use_ocr_fallback)
        elif suffix == '.docx':
            return _extract_docx(file_path)
        elif suffix == '.txt':
            return _extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    except Exception as e:
        raise Exception(f"Failed to extract text from {file_path.name}") from e

def _extract_pdf(file_path: Path, use_ocr_fallback: bool = True) -> str:
    """
    Extract text from PDF with OCR fallback for image-based PDFs.
    
    Process:
    1. Try regular PDF text extraction
    2. If text is below threshold, attempt OCR
    3. Return best available result
    
    Args:
        file_path: Path to PDF file
        use_ocr_fallback: Whether to use OCR if regular extraction is insufficient
        
    Returns:
        Extracted text string
    """
    # Step 1: Try regular PDF text extraction
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
        
        # Step 2: Check if we need OCR fallback
        if use_ocr_fallback and config.OCR_ENABLED:
            if not result or should_use_ocr(result, config.OCR_MIN_CHAR_THRESHOLD):
                logger.info(f"Regular extraction yielded {len(result)} chars for {file_path.name}, attempting OCR fallback")
                
                if is_ocr_available():
                    try:
                        ocr_result = extract_text_with_ocr(file_path)
                        if ocr_result and len(ocr_result) > len(result):
                            logger.info(f"OCR extraction successful: {len(ocr_result)} characters (vs {len(result)} from regular extraction)")
                            return ocr_result
                        elif ocr_result:
                            logger.info(f"OCR extracted {len(ocr_result)} characters, but regular extraction was better")
                            # Return OCR result if regular extraction was empty/too short
                            if not result or len(result) < config.OCR_MIN_CHAR_THRESHOLD:
                                return ocr_result
                    except Exception as ocr_error:
                        logger.warning(f"OCR fallback failed for {file_path.name}: {ocr_error}")
                        # Continue with regular extraction result if OCR fails
                        if result:
                            return result
                else:
                    logger.warning(f"OCR not available for {file_path.name}, using regular extraction result")
        
        # Step 3: Return regular extraction result (or raise if empty)
        if not result:
            if use_ocr_fallback and config.OCR_ENABLED and is_ocr_available():
                # Last attempt with OCR
                try:
                    return extract_text_with_ocr(file_path)
                except Exception as e:
                    raise ValueError(f"PDF appears to be image-based (no extractable text). OCR failed: {str(e)}")
            else:
                raise ValueError("PDF appears to be image-based (no extractable text). OCR required but not available or disabled.")
        
        return result
        
    except ValueError as e:
        # Re-raise ValueError (empty PDF, image-based, etc.)
        raise
    except Exception as e:
        # For other errors, try OCR if enabled
        if use_ocr_fallback and config.OCR_ENABLED and is_ocr_available():
            logger.warning(f"Regular PDF extraction failed for {file_path.name}: {e}. Attempting OCR fallback.")
            try:
                return extract_text_with_ocr(file_path)
            except Exception as ocr_error:
                raise Exception(f"PDF extraction error: {str(e)}. OCR fallback also failed: {str(ocr_error)}") from e
        else:
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