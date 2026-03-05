from fastapi import Query, status, HTTPException, Depends, APIRouter
from fastapi.responses import ORJSONResponse
import orjson
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.projects_schema import (
    ListProjects,
)
from core.rate_limiter import RateLimiter
from database.models.projects import Project

from database.db.session import get_db
from core.oauth2 import get_user_and_membership
from core.redis.redis_config import redis_client as redis

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.get("/", response_model=ListProjects, status_code=status.HTTP_200_OK)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    # get current version for this org from Redis (or default to 1)
    project_version_key = f"org_id:{membership.organization_id}:project_version"
    version = await redis.get(project_version_key)
    if not version:
        version = 1
        await redis.set(project_version_key, version)

    cache_key = f"org_id:{membership.organization_id}:project_v{version}:page:{page}:page_size:{page_size}/projects/"
    cached_projects_in_org = await redis.get(cache_key)

    if cached_projects_in_org:
        cached_data = orjson.loads(cached_projects_in_org)
        return ORJSONResponse(content=cached_data)

    else:
        offset = (page - 1) * page_size

        projects = (
            (
                await db.execute(
                    select(Project)
                    .where(
                        Project.organization_id == membership.organization_id,
                        Project.is_deleted.is_(False),
                    )
                    .order_by(Project.id.asc())
                    .offset(offset)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )

        if not projects:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No projects in Organization",
            )

        # List out the organizations the user is part of for frontend to select

        project_details = [
            {"project_id": project.id, "name": project.name} for project in projects
        ]

        projects_in_org = ListProjects(
            organization_id=membership.organization_id,
            page=page,
            page_size=page_size,
            project_details=project_details,
        )

        await redis.set(
            cache_key, orjson.dumps(projects_in_org.model_dump()), ex=60 * 5
        )

        return projects_in_org
