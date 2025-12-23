from pydantic import BaseModel, Field, field_validator

class ProcessRequest(BaseModel):
    company_id: str

class RankRequest(BaseModel):
    company_id: str
    jd_text: str
    top_k: int | None = None
    
    @field_validator('jd_text')
    @classmethod
    def validate_jd_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("jd_text must be non-empty")
        return v.strip()
    
    @field_validator('top_k')
    @classmethod
    def validate_top_k(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("top_k must be >= 1")
        return v

class StandardResponse(BaseModel):
    status: str
    collection_id: str
    details: dict | None = None