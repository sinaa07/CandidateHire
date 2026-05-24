"""Shared FastAPI dependencies for v2 routes."""
from __future__ import annotations

import os
import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tables import Company

DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() in ("1", "true", "yes")


def get_verified_company(
    company_id: uuid.UUID,
    x_company_api_key: str | None = Header(None, alias="X-Company-API-Key"),
    db: Session = Depends(get_db),
) -> Company:
    """
    Verify X-Company-API-Key matches the company_id on the request path.
    Set DISABLE_AUTH=true to skip key check (development only).
    """
    if DISABLE_AUTH:
        company = db.get(Company, company_id)
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")
        return company

    if not x_company_api_key:
        raise HTTPException(status_code=401, detail="Missing X-Company-API-Key header")

    company = db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.api_key == x_company_api_key,
        )
    ).scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=401, detail="Invalid API key or company id")
    return company
