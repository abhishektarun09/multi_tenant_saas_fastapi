from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from database.models.organization import Organization
from database.schemas.organization_schemas import OrganizationCreate, OrganizationOut
from database.db.base import get_db
from core.utils import slugify
from core.oauth2 import get_current_user

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
    
    organization_data = organization.model_dump()
    organization_data['slug'] = slug_name
    new_organization = Organization(**organization_data)

    try:
        db.add(new_organization)
        db.commit()
        db.refresh(new_organization)
    except Exception:
        db.rollback()
        raise

    return new_organization
