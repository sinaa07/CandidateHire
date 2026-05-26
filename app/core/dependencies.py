"""FastAPI dependencies for authentication and tenant isolation."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.tables import Company, User

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active == True,  # noqa: E712
        )
        .first()
    )

    if not user:
        raise credentials_exception

    return user


async def get_verified_company(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Company:
    if str(current_user.company_id) != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    company = (
        db.query(Company)
        .filter(
            Company.id == company_id,
            Company.is_active == True,  # noqa: E712
        )
        .first()
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return company
