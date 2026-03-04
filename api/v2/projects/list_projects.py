from fastapi import Query, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.projects_schema import (
    ListProjects,
)
from core.rate_limiter import RateLimiter
from database.models.projects import Project

from database.db.session import get_db
from core.oauth2 import get_user_and_membership

# router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])
router = APIRouter()

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
            status_code=status.HTTP_404_NOT_FOUND, detail="No projects in Organization"
        )

    # List out the organizations the user is part of for frontend to select

    project_details = [
        {"project_id": project.id, "name": project.name} for project in projects
    ]

    return {"page": page, "page_size": page_size, "project_details": project_details}
