from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.organization import Organization
from database.models.organization_member import OrganizationMember
from api.v2.schemas.organization_schemas import (
    OrganizationCreate,
    OrganizationOut,
)
from database.db.session import get_db
from core.utils import slugify, audit_logs
from core.oauth2 import get_current_user

router = APIRouter()


@router.post(
    "/register", status_code=status.HTTP_201_CREATED, response_model=OrganizationOut
)
async def register_organization(
    request: Request,
    organization: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: int = Depends(get_current_user),
):

    slug_name = slugify(organization.name)

    # Check if organization with the same name already exists
    existing_organization = (
        (
            await db.execute(
                select(Organization).where(
                    Organization.slug == slug_name,
                    Organization.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .first()
    )

    if existing_organization:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="creation.failed",
            resource_type="organizations",
            status="failed",
            meta_data={"org_slug": slug_name},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/register",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already registered",
        )

    new_organization = organization.model_dump()
    new_organization["slug"] = slug_name
    new_organization = Organization(**new_organization)

    db.add(new_organization)
    await db.flush()

    membership = OrganizationMember(
        user_id=current_user.id, organization_id=new_organization.id, role="owner"
    )
    db.add(membership)

    await audit_logs(
        db=db,
        actor_user_id=current_user.id,
        action="org.registered",
        resource_type="organizations",
        resource_id=str(new_organization.id),
        status="success",
        meta_data={"org_slug": slug_name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="/organization/register",
    )

    return new_organization
