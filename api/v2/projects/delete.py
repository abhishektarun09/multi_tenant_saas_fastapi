from fastapi import BackgroundTasks, Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.projects_schema import DeleteProjectOut
from core.logger import logger
from core.rate_limiter import RateLimiter
from core.utils import audit_logs, invalidate_redis_keys_on_project_add_delete_update
from database.db.session import get_db
from core.oauth2 import get_user_and_membership
from database.models.project_member import ProjectMember
from database.models.projects import Project


router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.delete(
    "/{project_id}",
    response_model=DeleteProjectOut,
    status_code=status.HTTP_200_OK,
)
async def delete_project(
    project_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):
    current_user, membership = current_user_and_membership

    # 1. Authorization
    if membership.role not in ("owner", "admin"):
        background_tasks.add_task(
            audit_logs,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="deletion.failed",
            resource_type="projects",
            status="failed",
            meta_data={
                "project_id": project_id,
                "reason": "Not authorized",
                "role": membership.role,
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
                    Project.is_deleted.is_(False),
                    Project.organization_id == membership.organization_id,
                )
            )
        )
        .scalars()
        .first()
    )

    if not existing_project:
        background_tasks.add_task(
            audit_logs,
            actor_user_id=current_user.id,
            organization_id=membership.organization_id,
            action="deletion.failed",
            resource_type="projects",
            status="failed",
            meta_data={
                "project_id": project_id,
                "role": membership.role,
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="project/delete",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project does not exist in organization",
        )
    try:
        existing_project.is_deleted = True

        await db.execute(
            delete(ProjectMember).where(ProjectMember.project_id == project_id)
        )

        await db.commit()

    except SQLAlchemyError as e:
        await db.rollback()

        logger.exception(
            "Database error",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )

    background_tasks.add_task(
        audit_logs,
        actor_user_id=current_user.id,
        organization_id=membership.organization_id,
        action="project.deleted",
        resource_type="projects",
        status="success",
        meta_data={
            "project_id": project_id,
            "role": membership.role,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="project/delete",
    )

    await invalidate_redis_keys_on_project_add_delete_update(
        org_id=membership.organization_id, project_id=project_id
    )

    return {"response": "Project deleted"}
