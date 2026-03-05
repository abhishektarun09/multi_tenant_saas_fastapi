import orjson

from fastapi import status, HTTPException, Depends, APIRouter
from fastapi.responses import ORJSONResponse
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
from core.redis.redis_config import redis_client as redis

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

    if membership.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view project members",
        )

    org_version_key = f"org_id:{membership.organization_id}:version"
    org_version = await redis.get(org_version_key)
    if not org_version:
        org_version = 1
        await redis.set(org_version_key, org_version)

    project_version_key = f"project_id:{project_id}:version"
    project_version = await redis.get(project_version_key)
    if not project_version:
        project_version = 1
        await redis.set(project_version_key, project_version)

    cache_key = f"org_id:{membership.organization_id}:org_v{org_version}:project_id:{project_id}:project_v{project_version}:/projects/members"
    cached_users_in_project = await redis.get(cache_key)

    if cached_users_in_project:
        cached_data = orjson.loads(cached_users_in_project)
        return ORJSONResponse(content=cached_data)

    else:
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not in Organization",
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
            {"name": member.name, "email": member.email}
            for member in members_in_project
        ]

        users_in_project = ListMembers(
            organization_id=membership.organization_id,
            project_id=project_id,
            member_details=member_details,
        )

        await redis.set(
            cache_key, orjson.dumps(users_in_project.model_dump()), ex=60 * 5
        )

        return users_in_project
