import re

from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from sqlalchemy import select

from core.logger import logger
from core.oauth2 import verify_token
from database.db.session import AsyncSessionLocal
from database.models.audit_log import AuditLog
from database.models.jti_blocklist import JtiBlocklist
from core.redis.redis_config import redis_client as redis

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


async def audit_logs(
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
    async with AsyncSessionLocal() as db:
        try:
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

            db.add(entry)
            await db.commit()

        except Exception as e:
            await db.rollback()

            log_context = {
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "status": status,
                "actor_user_id": actor_user_id,
                "organization_id": organization_id,
                "ip_address": ip_address,
                "endpoint": endpoint,
            }
            logger.error(
                "Audit log failed",
                extra={"error": str(e), **log_context},
            )

            raise


async def get_valid_refresh_payload(request: Request, db: AsyncSession):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token missing"
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token, credentials_exception)

    if payload.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )

    result = await db.execute(
        select(JtiBlocklist).where(JtiBlocklist.jti == payload.jti)
    )

    if result.scalars().first():
        raise HTTPException(status_code=401, detail="Token expired or blocklisted")

    return payload


async def invalidate_redis_keys_on_mem_change(org_id, user_id):
    org_version_key = f"org_id:{org_id}:version"
    await redis.incr(org_version_key)

    user_version_key = f"user_id:{user_id}:version"
    await redis.incr(user_version_key)


async def invalidate_redis_keys_on_org_delete(org_id):
    global_version_key = "global:version"
    await redis.incr(global_version_key)

    org_version_key = f"org_id:{org_id}:version"
    await redis.incr(org_version_key)


async def invalidate_redis_keys_on_project_add_delete_update(org_id, project_id):
    project_version_key = f"org_id:{org_id}:project_version"
    await redis.incr(project_version_key)
    
    project_version_key = f"project_id:{project_id}:version"
    await redis.incr(project_version_key)
    

async def invalidate_redis_keys_on_project_mem_change(project_id):    
    project_version_key = f"project_id:{project_id}:version"
    await redis.incr(project_version_key)
