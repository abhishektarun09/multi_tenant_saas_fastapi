from fastapi import status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.projects_schema import (
    ListProjects,
)
from core.rate_limiter import RateLimiter
from database.models.projects import Project

from database.db.session import get_db
from core.oauth2 import get_user_and_membership

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.get("/", response_model=ListProjects, status_code=status.HTTP_200_OK)
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    projects = (
        (
            await db.execute(
                select(Project).where(
                    Project.organization_id == membership.organization_id,
                    Project.is_deleted.is_(False),
                )
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

    project_details = [{"id": project.id, "name": project.name} for project in projects]

    return {"project_details": project_details}
