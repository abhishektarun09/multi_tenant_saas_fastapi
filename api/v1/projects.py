from fastapi import Request, status, HTTPException, Depends, APIRouter
from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from api.v1.schemas.projects_schema import AddProjectsOut, AddProjectsIn, AddUsersIn, AddUsersOut, ListProjects, UpdateProjectsIn, UpdateProjectsOut
from database.models.organization_member import OrganizationMember
from database.models.project_member import ProjectMember
from database.models.projects import Project

from database.db.base import get_db
from core.utils import audit_logs
from core.oauth2 import get_user_and_membership
from database.models.users import Users

router = APIRouter(
    prefix="/projects",
    tags=['Projects']
)

@router.post("/create_project", response_model=AddProjectsOut, status_code=status.HTTP_201_CREATED)
def create_project(request: Request, project_in: AddProjectsIn, db: Session = Depends(get_db), current_user_and_membership = Depends(get_user_and_membership)):
    
    user, membership = current_user_and_membership
    
    if membership.role.value not in ("owner", "admin"):
        audit_logs(
                db=db,
                actor_user_id=user.id,
                organization_id=membership.organization_id,
                action="creation.failed",
                resource_type="projects",
                status="failed",
                meta_data={"project_name": project_in.name, "role": membership.role.value},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                endpoint="/create_project",
            )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add projects to organization")
    
    project = db.query(Project).filter(Project.name == project_in.name, Project.organization_id == membership.organization_id).first()
    if project:
        audit_logs(
                db=db,
                actor_user_id=user.id,
                organization_id=membership.organization_id,
                action="creation.failed",
                resource_type="projects",
                status="failed",
                meta_data={"project_name": project_in.name, "role": membership.role.value},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                endpoint="/create_project",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project already exists")
    
    new_project = Project(name=project_in.name, organization_id=membership.organization_id, created_by=user.id)

    db.add(new_project)
    db.flush()
    
    audit_logs(
                db=db,
                actor_user_id=user.id,
                organization_id=membership.organization_id,
                action="project.created",
                resource_type="projects",
                resource_id=str(new_project.id),
                meta_data={"project_name": project_in.name},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                endpoint="/create_project",
            )
    
    return new_project

@router.post("/add_user", response_model=AddUsersOut, status_code=status.HTTP_201_CREATED)
def add_user(request: Request, payload: AddUsersIn, db: Session = Depends(get_db), current_user_and_membership = Depends(get_user_and_membership)):
    
    current_user, membership = current_user_and_membership
    
    # 1. Authorization
    if membership.role.value not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add users to projects")
    
    # 2. Fetch user
    user = db.query(Users).filter(Users.email == payload.email).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    
    # 3. Verify user belongs to the organization
    org_mem_exists = db.query(OrganizationMember.id).filter(OrganizationMember.organization_id == membership.organization_id, 
                                                  OrganizationMember.user_id == user.id,
                                                  ).scalar()
    if not org_mem_exists:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not exist in organization")
    
    # 4. Validate project belongs to organization
    project = db.query(Project).filter(
        Project.id == payload.project_id,
        Project.organization_id == membership.organization_id,
        ).first()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project does not exist")
    
    # 5. Check member exists in project
    existing_member = db.query(ProjectMember.id).filter(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == user.id,
        ).scalar()
    
    if existing_member:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists in project")

    
    # 5. Create project member
    new_project_member = ProjectMember(user_id = user.id,
                                       project_id = payload.project_id,
                                       )

    db.add(new_project_member)
    db.flush() # needed for audit log resource_id
    
    audit_logs(
                db=db,
                actor_user_id=current_user.id,
                organization_id=membership.organization_id,
                action="user.added",
                resource_type="projects",
                resource_id=str(new_project_member.id),
                meta_data={"project_id": payload.project_id,
                            "project_name": project.name},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                endpoint="projects//add_user",
            )
    
    return new_project_member

@router.put("/update_project{project_id}", response_model=UpdateProjectsOut, status_code=status.HTTP_200_OK)
def update_project(project_id: int, request: Request, payload: UpdateProjectsIn, db: Session = Depends(get_db), current_user_and_membership = Depends(get_user_and_membership)):
    
    current_user, membership = current_user_and_membership
    
    # Check whether user is authorized or not
    if membership.role.value not in ("owner", "admin"):
        
        audit_logs(
                    db=db,
                    actor_user_id=current_user.id,
                    organization_id=membership.organization_id,
                    action="update.failed",
                    resource_type="projects",
                    resource_id=str(project_id),
                    status="failed",
                    meta_data={"new_name": payload.new_name, "role" : membership.role.value},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    endpoint="/update_project",
                )
        
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update projects of the organization")
    
    # Check if project exists in current organization or not
    project = db.query(Project).filter(Project.id == project_id, Project.organization_id == membership.organization_id).first()
    
    if not project:
        
        audit_logs(
                    db=db,
                    actor_user_id=current_user.id,
                    organization_id=membership.organization_id,
                    action="update.failed",
                    resource_type="projects",
                    resource_id=str(project_id),
                    status="failed",
                    meta_data={"new_name": payload.new_name, "role" : membership.role.value},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    endpoint="/update_project",
                )
        
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project does not exist")
    
    # Update Project details
    project.name = payload.new_name   
       
    audit_logs(
                db=db,
                actor_user_id=current_user.id,
                organization_id=membership.organization_id,
                action="update.success",
                resource_type="projects",
                resource_id=str(project.id),
                meta_data={"new_name": payload.new_name, "role" : membership.role.value},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                endpoint="/update_project",
            )
    
    return {"response" : "Project updated successfully"}

@router.get("/list_projects", response_model=ListProjects, status_code=status.HTTP_200_OK)
def list_projects(db: Session = Depends(get_db), current_user_and_membership = Depends(get_user_and_membership)):
    
    current_user, membership = current_user_and_membership
    
    projects = db.query(Project.id, Project.name).filter(Project.organization_id == membership.organization_id).all()
    
    if not projects:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No projects in Organization")
    
    # List out the organizations the user is part of for frontend to select
    
    project_details = [
        {"id": project.id, "name": project.name}
        for project in projects
    ]
    
    return {"project_details" : project_details}