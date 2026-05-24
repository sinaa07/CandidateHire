"""V2 company management routes."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_verified_company
from app.api.routes.v2.helpers import company_storage_path, slugify
from app.db.session import get_db
from app.models.schemas import CompanyCreate, CompanyRead
from app.models.tables import Company

router = APIRouter(prefix="/api/v2/companies", tags=["v2-companies"])


class CompanySettingsUpdate(BaseModel):
    settings: dict = Field(...)


@router.post("/", response_model=CompanyRead, status_code=201)
def create_company(body: CompanyCreate, db: Session = Depends(get_db)) -> CompanyRead:
    slug = (body.slug or slugify(body.name)).strip()
    if not slug:
        raise HTTPException(status_code=422, detail="slug could not be derived from name")

    api_key = body.api_key or str(uuid.uuid4())
    company = Company(
        name=body.name.strip(),
        slug=slug,
        api_key=api_key,
        settings=body.settings or {},
    )
    db.add(company)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Company slug or api_key already exists") from exc

    db.refresh(company)
    Path(company_storage_path(company.id)).mkdir(parents=True, exist_ok=True)
    return CompanyRead.model_validate(company)


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(
    company: Company = Depends(get_verified_company),
) -> CompanyRead:
    return CompanyRead.model_validate(company)


@router.patch("/{company_id}/settings", response_model=CompanyRead)
def update_company_settings(
    body: CompanySettingsUpdate,
    company: Company = Depends(get_verified_company),
    db: Session = Depends(get_db),
) -> CompanyRead:
    merged = {**(company.settings or {}), **body.settings}
    company.settings = merged
    db.commit()
    db.refresh(company)
    return CompanyRead.model_validate(company)
