from fastapi import Request, status, HTTPException, Depends, APIRouter
from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from api.v1.schemas.projects_schema import AddProjectsOut, AddProjectsIn
from database.models.projects import Project

from database.db.base import get_db
from core.utils import audit_logs
from core.oauth2 import get_user_and_membership

router = APIRouter(
    prefix="/projects",
    tags=['Projects']
)

@router.post("/create_project", response_model=AddProjectsOut, status_code=status.HTTP_201_CREATED)
def create_project(request: Request, project_in: AddProjectsIn, db: Session = Depends(get_db), current_user_and_membership = Depends(get_user_and_membership)):
    
    user, membership = current_user_and_membership
    
    if membership.role.value not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add projects to organization")
    
    project = db.query(Project).filter(Project.name == project_in.name, Project.organization_id == membership.organization_id).first()
    
    if project:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project already exists")
    
    new_project = Project(name=project_in.name, organization_id=membership.organization_id, created_by=user.id)
    
    try:
        db.add(new_project)
        db.flush()
        
        logs = audit_logs(
                    db=db,
                    actor_user_id=user.id,
                    organization_id=membership.organization_id,
                    action="project.created",
                    resource_type="projects",
                    resource_id=str(new_project.id),
                    meta_data={"name": project_in.name},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    endpoint="/create_project",
                )
        
        db.add(logs)
        db.commit()
    
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project already exists")
    
    return new_project