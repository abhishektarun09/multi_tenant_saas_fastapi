from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.projects_schema import (
    AddUsersIn,
    AddUsersOut,
)
from database.models.organization_member import OrganizationMember
from database.models.project_member import ProjectMember
from database.models.projects import Project

from database.db.session import get_db
from core.utils import audit_logs
from core.oauth2 import get_user_and_membership
from database.models.users import Users

router = APIRouter()


@router.post(
    "/{project_id}/member",
    response_model=AddUsersOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_user(
    project_id: int,
    request: Request,
    payload: AddUsersIn,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    # 1. Authorization
    if membership.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add users to projects",
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not exist in organization",
        )

    # 4. Validate project belongs to organization
    project = (
        (
            await db.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.organization_id == membership.organization_id,
                    Project.is_deleted == False,
                )
            )
        )
        .scalars()
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project does not exist"
        )

    # 5. Check member exists in project
    existing_member = (
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

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists in project",
        )

    # 5. Create project member
    new_project_member = ProjectMember(
        user_id=user.id,
        project_id=project_id,
    )

    db.add(new_project_member)
    await db.flush()  # needed for audit log resource_id

    await audit_logs(
        db=db,
        actor_user_id=current_user.id,
        organization_id=membership.organization_id,
        action="user.added",
        resource_type="projects",
        resource_id=str(new_project_member.id),
        meta_data={"project_id": project_id, "project_name": project.name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="project/add_user",
    )

    return new_project_member
