from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.projects_schema import (
    UpdateProjectsIn,
    UpdateProjectsOut,
)
from database.models.projects import Project

from database.db.session import get_db
from core.utils import audit_logs
from core.oauth2 import get_user_and_membership

router = APIRouter()


@router.put(
    "/{project_id}",
    response_model=UpdateProjectsOut,
    status_code=status.HTTP_200_OK,
)
async def update_project(
    project_id: int,
    request: Request,
    payload: UpdateProjectsIn,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    # Check whether user is authorized or not
    if membership.role.value not in ("owner", "admin"):

        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="update.failed",
            resource_type="projects",
            resource_id=str(project_id),
            status="failed",
            meta_data={"new_name": payload.new_name, "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/project/update",
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update projects of the organization",
        )

    # Check if project exists in current organization or not
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

        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="update.failed",
            resource_type="projects",
            resource_id=str(project_id),
            status="failed",
            meta_data={"new_name": payload.new_name, "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/project/update",
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Project does not exist"
        )

    # Check if project with same name exists
    existing_project = (
        (
            await db.execute(
                select(Project).where(
                    Project.name == payload.new_name,
                    Project.organization_id == membership.organization_id,
                    Project.is_deleted == False,
                )
            )
        )
        .scalars()
        .first()
    )

    if existing_project:

        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="update.failed",
            resource_type="projects",
            resource_id=str(project_id),
            status="failed",
            meta_data={"new_name": payload.new_name, "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/project/update",
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with same name already exists",
        )

    # Update Project details
    project.name = payload.new_name

    await audit_logs(
        db=db,
        actor_user_id=current_user.id,
        organization_id=membership.organization_id,
        action="update.success",
        status="success",
        resource_type="projects",
        resource_id=str(project.id),
        meta_data={"new_name": payload.new_name, "role": membership.role.value},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="/project/update",
    )

    return {"response": "Project updated successfully"}
