from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services import collection_service
from app.core.logger import logger

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("/create")
async def create_collection(
    company_id: str = Form(...),
    zip_file: UploadFile = File(...)
):
    """Create a new resume collection from ZIP upload"""
    
    try:
        result = collection_service.create_collection(company_id, zip_file)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Collection creation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")