from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.projects_schema import (
    AddProjectsOut,
    AddProjectsIn,
)
from core.rate_limiter import RateLimiter
from database.models.projects import Project

from database.db.session import get_db
from core.utils import audit_logs
from core.oauth2 import get_user_and_membership

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.post("/", response_model=AddProjectsOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    project_in: AddProjectsIn,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    user, membership = current_user_and_membership

    if membership.role.value not in ("owner", "admin"):
        await audit_logs(
            db=db,
            actor_user_id=user.id,
            organization_id=membership.organization_id,
            action="creation.failed",
            resource_type="projects",
            status="failed",
            meta_data={"project_name": project_in.name, "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/project/create",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add projects to organization",
        )

    project = (
        (
            await db.execute(
                select(Project).where(
                    Project.name == project_in.name,
                    Project.organization_id == membership.organization_id,
                    Project.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .first()
    )
    if project:
        await audit_logs(
            db=db,
            actor_user_id=user.id,
            organization_id=membership.organization_id,
            action="creation.failed",
            resource_type="projects",
            status="failed",
            meta_data={"project_name": project_in.name, "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/project/create",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Project already exists"
        )

    new_project = Project(
        name=project_in.name,
        organization_id=membership.organization_id,
        created_by=user.id,
    )

    db.add(new_project)
    await db.flush()

    await audit_logs(
        db=db,
        actor_user_id=user.id,
        organization_id=membership.organization_id,
        action="project.created",
        resource_type="projects",
        resource_id=str(new_project.id),
        meta_data={"project_name": project_in.name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="/project/create",
    )

    return new_project
