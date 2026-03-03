from fastapi import BackgroundTasks, Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from core.logger import logger
from core.rate_limiter import RateLimiter
from database.models.organization import Organization
from api.v2.schemas.organization_schemas import (
    UpdateOrgIn,
    UpdateOrgOut,
)
from database.db.session import get_db
from core.utils import slugify, audit_logs
from core.oauth2 import get_user_and_membership

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.put("/update", status_code=status.HTTP_201_CREATED, response_model=UpdateOrgOut)
async def update(
    request: Request,
    payload: UpdateOrgIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    user, membership = current_user_and_membership

    if membership.role not in ("owner", "admin"):
        background_tasks.add_task(
            audit_logs,
            actor_user_id=user.id,
            action="update.failed",
            resource_type="organizations",
            organization_id=membership.organization_id,
            resource_id=str(membership.organization_id),
            status="failed",
            meta_data={"new_name": payload.new_name, "role": membership.role},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/update",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to add users to organization",
        )

    new_slug_name = slugify(payload.new_name)

    existing_organization = (
        (
            await db.execute(
                select(Organization).where(
                    Organization.slug == new_slug_name,
                    Organization.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .first()
    )

    if existing_organization:
        background_tasks.add_task(
            audit_logs,
            actor_user_id=user.id,
            action="update.failed",
            resource_type="organizations",
            organization_id=membership.organization_id,
            resource_id=str(membership.organization_id),
            status="failed",
            meta_data={"new_name": payload.new_name, "role": membership.role},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/update",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already registered",
        )

    try:
        updated_org = Organization(name=payload.new_name, slug=new_slug_name)

        db.add(updated_org)
        await db.commit()

    except SQLAlchemyError as e:
        await db.rollback()

        logger.exception(
            "Database error",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )

    background_tasks.add_task(
        audit_logs,
        actor_user_id=user.id,
        action="org.updated",
        resource_type="organizations",
        organization_id=membership.organization_id,
        resource_id=str(membership.organization_id),
        status="success",
        meta_data={"new_name": payload.new_name, "role": membership.role},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="/organization/update",
    )

    return {"message": "Organization details updated"}
