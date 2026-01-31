from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from database.models.organization import Organization
from database.models.organization_member import OrganizationMember
from database.schemas.authorization_schemas import Token
from database.schemas.organization_schemas import OrganizationCreate, OrganizationOut, SelectOrganization
from database.db.base import get_db
from core.utils import slugify, audit_logs
from core.oauth2 import create_access_token, get_current_user, get_organization, get_user_and_org

router = APIRouter(
    prefix="/organization",
    tags=['Organizations']
)

# JWT Protected
@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=OrganizationOut)
def register_organization(organization: OrganizationCreate, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    
    slug_name = slugify(organization.name)
    
    # Check if organization with the same name already exists
    existing_organization = db.query(Organization).filter(Organization.slug == slug_name).first()
    if existing_organization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already registered"
        )
    
    new_organization = organization.model_dump()
    new_organization['slug'] = slug_name
    new_organization = Organization(**new_organization)

    try:
        db.add(new_organization)
        db.flush()
        
        membership = OrganizationMember(
            user_id = current_user.id,
            organization_id = new_organization.id,
            role = "owner"
        )
        db.add(membership)
        db.commit()
        db.refresh(new_organization)
    except Exception:
        db.rollback()
        raise

    return new_organization

# JWT Protected
@router.post("/select", status_code=status.HTTP_202_ACCEPTED, response_model=Token)
def select_organization(organization: SelectOrganization, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    
    user_id = current_user.id
    org_id = organization.org_id
    member = db.query(OrganizationMember).filter(OrganizationMember.organization_id == org_id, OrganizationMember.user_id == user_id).first()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not member of the organization")
    
    jwt_data = {
        "user_id" : user_id,
        "org_id" : org_id,
    }
    
    jwt_token = create_access_token(jwt_data)
    
    return {"access_token" : jwt_token, "token_type" : "bearer"}