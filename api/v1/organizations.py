from fastapi import status, HTTPException, Depends, APIRouter
from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from database.models.organization import Organization
from database.models.organization_member import OrganizationMember
from api.v1.schemas.authorization_schemas import Token
from api.v1.schemas.organization_schemas import OrganizationCreate, OrganizationOut, SelectOrganization, AddUsers, AddUsersOut
from database.models.users import Users
from database.db.base import get_db
from core.utils import slugify, audit_logs
from core.oauth2 import create_access_token, get_current_user, get_user_and_membership

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
        "token_type" : "access"
    }
    
    jwt_token = create_access_token(jwt_data)
    
    return {"access_token" : jwt_token, "token_type" : "bearer"}

# JWT Protected
@router.post("/add_users", status_code=status.HTTP_201_CREATED, response_model=AddUsersOut)
def add_users(input: AddUsers, db: Session = Depends(get_db), current_user_and_membership = Depends(get_user_and_membership)):
    
    user, membership = current_user_and_membership
        
    if membership.role.value not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized to add users to organization")
    
    if membership.role.value == "admin" and input.role == "owner":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized to add owner")
            
    user = db.query(Users).filter(Users.email == input.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    
    member = db.query(Users).join(OrganizationMember, OrganizationMember.user_id == Users.id).filter(Users.email == input.email, OrganizationMember.organization_id == membership.organization_id).first()
    
    if member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already registered in Organization")  
    
    new_member = OrganizationMember(user_id = user.id, organization_id = membership.organization_id, role = input.role)
    
    try:
        db.add(new_member)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists in organization"
    )
    
    return {"message" : "User added to organization"}