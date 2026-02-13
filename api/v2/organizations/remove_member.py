from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from core.rate_limiter import RateLimiter
from core.utils import audit_logs
from database.models.organization_member import OrganizationMember
from api.v2.schemas.organization_schemas import RemoveMemberIn, RemoveMemberOut
from database.db.session import get_db
from core.oauth2 import get_user_and_membership
from database.models.project_member import ProjectMember
from database.models.projects import Project
from database.models.users import Users

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.delete(
    "/member", status_code=status.HTTP_200_OK, response_model=RemoveMemberOut
)
async def remove_member(
    payload: RemoveMemberIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    if membership.role.value not in ("owner", "admin"):
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="remove.member",
            resource_type="organizations",
            organization_id=membership.organization_id,
            status="failed",
            meta_data={"role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/delete/organization/member",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove the member from the organization",
        )

    existing_user = (
        (
            await db.execute(
                select(Users).where(
                    Users.email == payload.email,
                    Users.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .first()
    )

    if not existing_user:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="remove.member",
            resource_type="organizations",
            organization_id=membership.organization_id,
            status="failed",
            meta_data={"action": "soft_delete"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/delete/organization/member",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist"
        )

    user_in_org = (
        (
            await db.execute(
                select(OrganizationMember).where(
                    OrganizationMember.user_id == existing_user.id,
                    OrganizationMember.organization_id == membership.organization_id,
                )
            )
        )
        .scalars()
        .first()
    )

    if not user_in_org:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="remove.member",
            resource_type="organizations",
            organization_id=membership.organization_id,
            status="failed",
            meta_data={"action": "soft_delete"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/delete/organization/member",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist in the organization",
        )

    if membership.role.value == "admin" and user_in_org.role.value == "owner":
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="remove.member",
            resource_type="organizations",
            organization_id=membership.organization_id,
            status="failed",
            meta_data={"role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/delete/organization/member",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot remove organization owners",
        )

    if user_in_org.role.value == "owner":
        owners_count = (
            (
                await db.execute(
                    select(OrganizationMember).where(
                        OrganizationMember.organization_id
                        == membership.organization_id,
                        OrganizationMember.role == "owner",
                    )
                )
            )
            .scalars()
            .all()
        )

        if len(owners_count) <= 1:
            await audit_logs(
                db=db,
                actor_user_id=current_user.id,
                action="remove.member",
                resource_type="organizations",
                organization_id=membership.organization_id,
                status="failed",
                meta_data={"role": membership.role.value},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                endpoint="/delete/organization/member",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner of the organization",
            )

    # Delete member from projects
    await db.execute(
        delete(ProjectMember).where(
            ProjectMember.user_id == existing_user.id,
            ProjectMember.project_id.in_(
                select(Project.id).where(
                    Project.organization_id == membership.organization_id,
                    Project.is_deleted.is_(False),
                )
            ),
        )
    )

    # Delete member from the organization
    await db.execute(
        delete(OrganizationMember).where(
            OrganizationMember.organization_id == membership.organization_id,
            OrganizationMember.user_id == existing_user.id,
        )
    )

    await audit_logs(
        db=db,
        actor_user_id=current_user.id,
        action="remove.member",
        resource_type="organizations",
        organization_id=membership.organization_id,
        status="success",
        meta_data={"user_id": existing_user.id},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="/delete/organization/member",
    )
    return {"response": "User removed"}
