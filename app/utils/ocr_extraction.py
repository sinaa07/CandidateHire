"""
OCR-based text extraction for image-based PDFs.

This module provides OCR functionality as a fallback when regular PDF text extraction
fails or extracts too few characters. It uses pytesseract and pdf2image to convert
PDF pages to images and extract text via OCR.
"""

from pathlib import Path
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Optional imports - OCR dependencies
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR dependencies not available. Install pytesseract, pdf2image, and Pillow for OCR support.")


def is_ocr_available() -> bool:
    """Check if OCR dependencies are installed and available."""
    if not OCR_AVAILABLE:
        return False
    
    try:
        # Test if tesseract is installed
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        logger.warning("Tesseract OCR not found. Install Tesseract OCR engine.")
        return False


def extract_text_with_ocr(pdf_path: Path, dpi: int = 300, lang: str = 'eng') -> str:
    """
    Extract text from PDF using OCR (Optical Character Recognition).
    
    This function converts PDF pages to images and uses OCR to extract text.
    Use this as a fallback when regular PDF text extraction fails or extracts
    too few characters.
    
    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for image conversion (default: 300)
        lang: Tesseract language code (default: 'eng')
        
    Returns:
        Extracted text as a single string
        
    Raises:
        ValueError: If OCR is not available or extraction fails
        Exception: For other OCR-related errors
    """
    if not is_ocr_available():
        raise ValueError("OCR is not available. Install dependencies: pytesseract, pdf2image, Pillow, and Tesseract OCR engine.")
    
    try:
        logger.info(f"Starting OCR extraction for {pdf_path.name}")
        
        # Convert PDF pages to images
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            fmt='png',
            thread_count=1  # Single-threaded for stability
        )
        
        if not images:
            raise ValueError("Failed to convert PDF to images")
        
        # Extract text from each page
        extracted_texts = []
        for i, image in enumerate(images):
            try:
                # Perform OCR on the image
                page_text = pytesseract.image_to_string(image, lang=lang)
                if page_text and page_text.strip():
                    extracted_texts.append(page_text.strip())
                    logger.debug(f"OCR extracted {len(page_text)} characters from page {i+1}")
            except Exception as e:
                logger.warning(f"OCR failed for page {i+1} of {pdf_path.name}: {e}")
                continue
        
        if not extracted_texts:
            raise ValueError("OCR extraction produced no text")
        
        # Combine all pages
        result = ' '.join(extracted_texts).strip()
        logger.info(f"OCR extraction completed: {len(result)} characters extracted from {len(images)} pages")
        
        return result
        
    except Exception as e:
        error_msg = f"OCR extraction failed for {pdf_path.name}: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e


def should_use_ocr(extracted_text: str, min_char_threshold: int) -> bool:
    """
    Determine if OCR should be used based on extracted text length.
    
    Args:
        extracted_text: Text extracted via regular PDF extraction
        min_char_threshold: Minimum character threshold (below this, use OCR)
        
    Returns:
        True if OCR should be used, False otherwise
    """
    if not extracted_text:
        return True
    
    # Count non-whitespace characters
    char_count = len(extracted_text.replace(' ', '').replace('\n', '').replace('\t', ''))
    
    # Use OCR if character count is below threshold
    return char_count < min_char_threshold

