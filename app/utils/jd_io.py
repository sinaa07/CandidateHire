# app/utils/jd_io.py
from __future__ import annotations

from pathlib import Path
from typing import Optional
import shutil

from app.utils.text_extraction import extract_text


def save_jd_text(collection_root: Path, jd_text: str) -> Path:
    """
    Writes JD text to collection_root/input/jd.txt
    """
    input_dir = collection_root / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    jd_file = input_dir / "jd.txt"
    jd_file.write_text(jd_text.strip(), encoding="utf-8")
    return jd_file


def load_jd_text(collection_root: Path) -> str:
    """
    Reads collection_root/input/jd.txt
    """
    jd_file = collection_root / "input" / "jd.txt"
    if not jd_file.exists():
        raise ValueError("JD not found")
    return jd_file.read_text(encoding="utf-8", errors="ignore").strip()


def save_jd_file(
    collection_root: Path,
    filename: str,
    file_stream,
) -> Path:
    """
    Save an uploaded JD file (PDF/DOCX/TXT) into collection_root/input/.

    Args:
        collection_root: Collection root directory
        filename: Original uploaded filename (used for extension)
        file_stream: A binary file-like object (e.g., UploadFile.file)

    Returns:
        Path to saved JD file
    """
    input_dir = collection_root / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise ValueError("Unsupported JD file type. Allowed: .pdf, .docx, .txt")

    jd_path = input_dir / f"jd{suffix}"

    # Copy stream -> disk (safe for big files, doesn't load entire file in memory)
    with open(jd_path, "wb") as out:
        shutil.copyfileobj(file_stream, out)

    # Reset stream if possible (helps if caller reuses it)
    try:
        file_stream.seek(0)
    except Exception:
        pass

    return jd_path


def load_jd_text_from_any(collection_root: Path) -> str:
    """
    Load JD text from either:
    - input/jd.txt
    - input/jd.pdf
    - input/jd.docx
    - input/jd.txt (uploaded file also ends up here, but handled anyway)

    Priority:
    1) input/jd.txt (explicit text save)
    2) input/jd.pdf
    3) input/jd.docx
    4) input/jd.txt (already covered)

    Returns:
        Extracted JD text (stripped)

    Raises:
        ValueError: if no JD found or extracted JD is empty
    """
    input_dir = collection_root / "input"
    candidates = [
        input_dir / "jd.txt",
        input_dir / "jd.pdf",
        input_dir / "jd.docx",
    ]

    for path in candidates:
        if not path.exists():
            continue

        if path.suffix.lower() == ".txt":
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
        else:
            text = extract_text(path).strip()

        if text:
            return text

    raise ValueError("JD not found or JD has no extractable text")