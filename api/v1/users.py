from fastapi import status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from core.oauth2 import get_current_user
from database.models.organization_member import OrganizationMember
from database.models.users import Users
from core.utils import hash
from database.schemas.organization_schemas import ListOrgs
from database.schemas.user_schemas import UserCreate, UserOut, Me
from database.db.base import get_db

router = APIRouter(
    prefix="/users",
    tags=['Users']
)

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    
    # Check if user with the same email already exists
    existing_user = db.query(Users).filter(Users.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # hash the password - user.password
    hashed_password = hash(user.password_hash)
    
    user_data = user.model_dump()
    user_data['password_hash'] = hashed_password
    new_user = Users(**user_data)

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise
    
    return new_user

@router.get("/me", response_model=Me)
def me(db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    
    user = db.query(Users).filter(Users.id == current_user.id).first()
    return user

@router.get("/list_orgs", response_model=ListOrgs)
def list_orgs(db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    
    user = db.query(Users).filter(Users.id == current_user.id).first()
    
    # List out the organizations the user is part of for frontend to select
    org_ids = db.query(OrganizationMember.organization_id).filter(OrganizationMember.user_id == user.id).all()
    org_ids = [org_id for (org_id,) in org_ids]
    
    return {"email": user.email, "org_ids" : org_ids}