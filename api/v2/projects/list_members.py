from fastapi import status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.projects_schema import (
    ListMembers,
)
from core.rate_limiter import RateLimiter
from database.models.project_member import ProjectMember
from database.models.projects import Project

from database.db.session import get_db
from core.oauth2 import get_user_and_membership
from database.models.users import Users

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.get(
    "/{project_id}/members", response_model=ListMembers, status_code=status.HTTP_200_OK
)
async def list_members(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    if membership.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view project members",
        )

    project = (
        (
            await db.execute(
                select(Project).where(
                    Project.organization_id == membership.organization_id,
                    Project.id == project_id,
                    Project.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not in Organization"
        )

    members_in_project = (
        (
            await db.execute(
                select(Users)
                .join(ProjectMember, ProjectMember.user_id == Users.id)
                .join(Project, Project.id == ProjectMember.project_id)
                .where(
                    Project.organization_id == membership.organization_id,
                    Project.id == project_id,
                    Project.is_deleted.is_(False),
                    Users.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )

    if not members_in_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No member in the project"
        )

    member_details = [
        {"name": member.name, "email": member.email} for member in members_in_project
    ]

    return {"member_details": member_details}
