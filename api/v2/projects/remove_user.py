from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.projects_schema import (
    RemoveUsersIn,
    RemoveUsersOut,
)
from database.models.organization_member import OrganizationMember
from database.models.project_member import ProjectMember
from database.models.projects import Project

from database.db.session import get_db
from core.utils import audit_logs
from core.oauth2 import get_user_and_membership
from database.models.users import Users

router = APIRouter()


@router.delete(
    "/remove_user", response_model=RemoveUsersOut, status_code=status.HTTP_201_CREATED
)
async def remove_user(
    request: Request,
    payload: RemoveUsersIn,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    # 1. Authorization
    if membership.role.value not in ("owner", "admin"):
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="deletion.failed",
            resource_type="projects",
            status="failed",
            meta_data={
                "project_id": payload.project_id,
                "reason": "Not authorized",
                "role": membership.role.value,
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="project/remove_user",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove users from projects",
        )

    # 2. Fetch user
    user = (
        (
            await db.execute(
                select(Users).where(
                    Users.email == payload.email, Users.is_deleted == False
                )
            )
        )
        .scalars()
        .first()
    )

    if not user:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="deletion.failed",
            resource_type="projects",
            status="failed",
            meta_data={"project_id": payload.project_id},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="project/remove_user",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist"
        )

    # 3. Verify user belongs to the organization
    org_mem_exists = (
        (
            await db.execute(
                select(OrganizationMember.id).where(
                    OrganizationMember.organization_id == membership.organization_id,
                    OrganizationMember.user_id == user.id,
                )
            )
        )
        .scalars()
        .first()
    )

    if not org_mem_exists:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="deletion.failed",
            resource_type="projects",
            status="failed",
            resource_id=str(user.id),
            meta_data={"project_id": payload.project_id},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="project/remove_user",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not exist in organization",
        )

    # 4. Validate project belongs to organization
    project = (
        (
            await db.execute(
                select(Project).where(
                    Project.id == payload.project_id,
                    Project.organization_id == membership.organization_id,
                    Project.is_deleted == False,
                )
            )
        )
        .scalars()
        .first()
    )

    if not project:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="deletion.failed",
            resource_type="projects",
            status="failed",
            resource_id=str(user.id),
            meta_data={"project_id": payload.project_id},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="project/remove_user",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project does not exist"
        )

    # 5. Check member exists in project
    project_member = (
        (
            await db.execute(
                select(ProjectMember.id).where(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == user.id,
                )
            )
        )
        .scalars()
        .first()
    )

    if not project_member:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="deletion.failed",
            resource_type="projects",
            status="failed",
            resource_id=str(user.id),
            meta_data={"project_id": payload.project_id, "project_name": project.name},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="project/remove_user",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User does not exist in project",
        )

    # 5. Delete project member
    db.delete(project_member)

    await audit_logs(
        db=db,
        actor_user_id=current_user.id,
        organization_id=membership.organization_id,
        action="user.removed",
        resource_type="projects",
        status="success",
        resource_id=str(user.id),
        meta_data={"project_id": payload.project_id, "project_name": project.name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="project/remove_user",
    )

    return {"response": "Member removed from the project"}
