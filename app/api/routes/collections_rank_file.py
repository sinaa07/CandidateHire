from fastapi import APIRouter, File, Form, UploadFile
from app.models.api_schemas import StandardResponse
from app.utils.paths import get_collection_root, assert_collection_exists
from app.core.errors import to_http_error
from app.utils.jd_io import save_jd_file
from app.utils.text_extraction import extract_text
from app.services.ranking_service import rank_collection

router = APIRouter(prefix="/collections", tags=["ranking"])


@router.post("/{collection_id}/rank-file")
async def rank_collection_from_file(
    collection_id: str,
    company_id: str = Form(...),
    jd_file: UploadFile = File(...),
    top_k: int | None = Form(None),
) -> StandardResponse:
    """
    Rank resumes using a JD uploaded as PDF/DOCX/TXT.

    Form fields:
      - company_id (required)
      - jd_file (required): .pdf, .docx, or .txt
      - top_k (optional): integer >= 1

    Saves JD to:
      collection_root/input/jd.<ext>
    """
    try:
        # Validate top_k early
        if top_k is not None and top_k < 1:
            raise ValueError("top_k must be >= 1")

        # 1) Resolve + validate collection
        collection_root = get_collection_root(company_id, collection_id)
        assert_collection_exists(collection_root)

        # 2) Guard: require processed resumes
        processed_dir = collection_root / "processed"
        if not processed_dir.exists() or not list(processed_dir.glob("*.txt")):
            raise ValueError("Run processing first - no processed resumes found")

        # 3) Save JD file to input/jd.<ext>
        saved_jd_path = save_jd_file(
            collection_root=collection_root,
            filename=jd_file.filename or "jd.txt",
            file_stream=jd_file.file,
        )

        # 4) Extract JD text
        jd_text = extract_text(saved_jd_path).strip()
        if not jd_text:
            raise ValueError("JD has no extractable text")

        # 5) Reuse existing ranking service (Phase 3)
        result = rank_collection(
            company_id=company_id,
            collection_id=collection_id,
            jd_text=jd_text,
            top_k=top_k,
        )

        return StandardResponse(
            status="completed",
            collection_id=collection_id,
            details={
                **result,
                "jd_saved_as": str(saved_jd_path.name),  # e.g. "jd.pdf"
            },
        )

    except Exception as exc:
        raise to_http_error(exc)