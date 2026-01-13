# OCR Setup Guide

## Overview

The CandidateHire system includes OCR (Optical Character Recognition) support as a fallback for image-based PDFs. OCR is automatically used when regular PDF text extraction yields too few characters (below the configured threshold).

## How It Works

1. **Regular Extraction First**: The system first attempts standard PDF text extraction
2. **Threshold Check**: If extracted text is below the threshold (default: 100 characters), OCR is triggered
3. **OCR Fallback**: PDF pages are converted to images and processed with Tesseract OCR
4. **Best Result**: The system returns the best available extraction result

This approach ensures:
- ✅ Text-based PDFs are processed quickly (no OCR overhead)
- ✅ Image-based PDFs are automatically handled via OCR
- ✅ No manual intervention required

## Installation

### 1. Install Python Dependencies

The OCR dependencies are already listed in `requirements.txt`:

```bash
pip install pytesseract pdf2image Pillow
```

### 2. Install Tesseract OCR Engine

#### macOS
```bash
brew install tesseract
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### Windows
1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install Tesseract (default location: `C:\Program Files\Tesseract-OCR`)
3. Add to PATH or configure `pytesseract.pytesseract.tesseract_cmd` in code

### 3. Verify Installation

```python
import pytesseract
print(pytesseract.get_tesseract_version())  # Should print version number
```

## Configuration

OCR settings are in `app/core/config.py`:

```python
# OCR Configuration
OCR_MIN_CHAR_THRESHOLD = 100  # Minimum characters to avoid OCR (text-based PDFs)
OCR_ENABLED = True  # Set to False to disable OCR fallback
```

### Adjusting the Threshold

- **Lower threshold (e.g., 50)**: More PDFs will use OCR (slower, but catches edge cases)
- **Higher threshold (e.g., 200)**: Fewer PDFs will use OCR (faster, but may miss some image-based PDFs)

### Disabling OCR

Set `OCR_ENABLED = False` to disable OCR fallback entirely. The system will only use regular PDF extraction.

## Usage

OCR is automatically integrated into Phase 2 processing. No code changes needed!

### Phase 2 Processing Flow

1. Upload resumes via Phase 1
2. Process collection via Phase 2 API
3. System automatically:
   - Extracts text from text-based PDFs (fast)
   - Uses OCR for image-based PDFs (automatic fallback)
   - Logs OCR usage for monitoring

### Monitoring OCR Usage

Check processing logs for OCR activity:

```
INFO: Regular extraction yielded 45 chars for resume.pdf, attempting OCR fallback
INFO: Starting OCR extraction for resume.pdf
INFO: OCR extraction completed: 1234 characters extracted from 2 pages
```

## API Integration

OCR is transparent to API consumers. The same endpoints work:

```bash
# Phase 2: Process (OCR happens automatically if needed)
POST /collections/{collection_id}/process
{
  "company_id": "acme_corp"
}
```

## Performance Considerations

- **Text-based PDFs**: No performance impact (OCR not used)
- **Image-based PDFs**: 
  - ~1-3 seconds per page (depending on image quality)
  - Multi-page PDFs take proportionally longer
  - Consider batch processing for large collections

## Troubleshooting

### OCR Not Available

If you see warnings like:
```
WARNING: OCR dependencies not available...
```

1. Install Python packages: `pip install pytesseract pdf2image Pillow`
2. Install Tesseract OCR engine (see Installation section)
3. Verify: `pytesseract.get_tesseract_version()`

### OCR Fails for Specific PDFs

- Check PDF quality (low resolution images may fail)
- Verify Tesseract language packs (for non-English resumes)
- Check logs for specific error messages

### Adjusting OCR Settings

For better OCR results, you can modify `app/utils/ocr_extraction.py`:

```python
# Higher DPI for better quality (slower)
images = convert_from_path(pdf_path, dpi=400)

# Different language
page_text = pytesseract.image_to_string(image, lang='eng+fra')  # English + French
```

## Language Support

Default language is English (`eng`). For other languages:

1. Install Tesseract language packs:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr-fra  # French
   sudo apt-get install tesseract-ocr-spa  # Spanish
   ```

2. Modify `ocr_extraction.py` to use different language:
   ```python
   extract_text_with_ocr(pdf_path, lang='fra')  # French
   ```

## Integration with Existing Code

The OCR functionality is integrated into `app/utils/text_extraction.py`:

```python
from app.utils.text_extraction import extract_text

# OCR is automatic - no code changes needed!
text = extract_text(pdf_path)
```

The function signature remains the same, ensuring backward compatibility.

## Testing

To test OCR functionality:

1. Create a test PDF with scanned images
2. Process via Phase 2 API
3. Check logs for OCR activity
4. Verify extracted text in `processed/` directory

## Support

For issues or questions:
1. Check logs for specific error messages
2. Verify Tesseract installation
3. Test with a known-good PDF
4. Review configuration settings

