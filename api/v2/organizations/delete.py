from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from core.rate_limiter import RateLimiter
from core.utils import audit_logs
from database.models.organization import Organization
from database.models.organization_member import OrganizationMember
from api.v2.schemas.organization_schemas import DeleteOrganizationOut
from database.db.session import get_db
from core.oauth2 import get_user_and_membership
from database.models.project_member import ProjectMember
from database.models.projects import Project

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.delete(
    "/", status_code=status.HTTP_200_OK, response_model=DeleteOrganizationOut
)
async def delete_organization(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    if membership.role.value != "owner":
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="org.deletion",
            resource_type="organizations",
            organization_id=membership.organization_id,
            status="failed",
            meta_data={"action": "soft_delete", "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/delete",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete the organization",
        )

    existing_org = (
        (
            await db.execute(
                select(Organization).where(
                    Organization.id == membership.organization_id,
                    Organization.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .first()
    )

    if not existing_org:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="org.deletion",
            resource_type="organizations",
            organization_id=membership.organization_id,
            status="failed",
            meta_data={"action": "soft_delete"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/delete",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization already deleted"
        )

    # Soft delete Organization

    existing_org.is_deleted = True

    # Delete members of the organization
    await db.execute(
        delete(OrganizationMember).where(
            OrganizationMember.organization_id == membership.organization_id
        )
    )

    # Soft delete the projects
    await db.execute(
        update(Project)
        .where(Project.organization_id == membership.organization_id)
        .values(is_deleted=True)
    )

    # Delete project members
    await db.execute(
        delete(ProjectMember).where(
            ProjectMember.project_id.in_(
                select(Project.id).where(
                    Project.organization_id == membership.organization_id
                )
            )
        )
    )

    await audit_logs(
        db=db,
        actor_user_id=current_user.id,
        action="org.deleted",
        resource_type="organizations",
        organization_id=membership.organization_id,
        status="success",
        meta_data={"action": "soft_delete"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="/organization/delete",
    )
    return {"response": "Organization deleted", "action": "logout the user"}
