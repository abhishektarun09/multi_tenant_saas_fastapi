import re

from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from core.oauth2 import verify_token
from database.models.audit_log import AuditLog
from database.models.jti_blocklist import JtiBlocklist

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash(password: str):
    return pwd_context.hash(password)


def verify(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def slugify(name: str):
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"^-+|-+$", "", name)
    return name


def audit_logs(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    status: str = "success",
    actor_user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    meta_data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    endpoint: Optional[str] = None,
):
    entry = AuditLog(
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        meta_data=meta_data,
        ip_address=ip_address,
        user_agent=user_agent,
        endpoint=endpoint,
    )

    try:
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
    

def get_valid_refresh_payload(request: Request, db: Session):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token missing")
    
    credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token, credentials_exception)

    if payload.token_type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    if db.query(JtiBlocklist).filter_by(jti=payload.jti).first():
        raise HTTPException(status_code=401, detail="Token expired or blocklisted")

    return payload
