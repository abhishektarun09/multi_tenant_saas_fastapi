from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.projects_schema import DeleteProjectOut
from core.utils import audit_logs
from database.db.session import get_db
from core.oauth2 import get_user_and_membership
from database.models.project_member import ProjectMember
from database.models.projects import Project


router = APIRouter()


@router.delete(
    "/{project_id}",
    response_model=DeleteProjectOut,
    status_code=status.HTTP_200_OK,
)
async def delete_project(
    project_id: int,
    request: Request,
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
                "project_id": project_id,
                "reason": "Not authorized",
                "role": membership.role.value,
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="project/delete",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete project from org",
        )

    # 2. Fetch project
    existing_project = (
        (
            await db.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.is_deleted == False,
                    Project.organization_id == membership.organization_id,
                )
            )
        )
        .scalars()
        .first()
    )

    if not existing_project:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="deletion.failed",
            resource_type="projects",
            status="failed",
            meta_data={
                "project_id": project_id,
                "role": membership.role.value,
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="project/delete",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project does not exist in organization",
        )

    existing_project.is_deleted = True

    await db.execute(
        delete(ProjectMember).where(ProjectMember.project_id == project_id)
    )

    await audit_logs(
        db=db,
        actor_user_id=current_user.id,
        organization_id=membership.organization_id,
        action="project.deleted",
        resource_type="projects",
        status="success",
        meta_data={
            "project_id": project_id,
            "role": membership.role.value,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="project/delete",
    )

    return {"response": "Project deleted"}
