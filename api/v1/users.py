from fastapi import Request, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from core.oauth2 import get_current_user, get_user_and_membership
from database.models.jti_blocklist import JtiBlocklist
from database.models.organization_member import OrganizationMember
from database.models.users import Users
from core.utils import audit_logs, get_valid_refresh_payload, hash, verify
from api.v1.schemas.organization_schemas import ListOrgs
from api.v1.schemas.user_schemas import UpdatePasswordIn, UpdatePasswordOut, UserCreate, UserOut, Me
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
def me(db: Session = Depends(get_db), current_user_and_membership = Depends(get_user_and_membership)):
    
    current_user, membership = current_user_and_membership
    
    user_details = db.query(Users).filter(Users.id == current_user.id, ).first()
    
    return {"email": user_details.email, "name": user_details.name, "role" : membership.role}

@router.get("/list_orgs", response_model=ListOrgs)
def list_orgs(db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    
    user = db.query(Users).filter(Users.id == current_user.id).first()
    
    # List out the organizations the user is part of for frontend to select
    org_ids = db.query(OrganizationMember.organization_id).filter(OrganizationMember.user_id == user.id).all()
    org_ids = [org_id for (org_id,) in org_ids]
    
    return {"email": user.email, "org_ids" : org_ids}

@router.put("/update_password", response_model=UpdatePasswordOut, status_code=status.HTTP_200_OK)
def update_password(response: Response, request: Request, input_data: UpdatePasswordIn, current_user: Users = Depends(get_current_user), db: Session = Depends(get_db)):

    if not verify(input_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    
    if verify(input_data.new_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different from the current password")
    
    payload = get_valid_refresh_payload(request, db)
    
    jti_value = payload.jti
    blacklisted_jti = JtiBlocklist(jti=jti_value)

    try:
        db.add(blacklisted_jti)
        hashed_password = hash(input_data.new_password)
        current_user.password_hash = hashed_password
        
        logs = audit_logs(
                db=db,
                actor_user_id=current_user.id,
                action="password_change.success",
                resource_type="users",
                resource_id=str(current_user.id),
                meta_data={"email": current_user.email},
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                endpoint="/update_password",
            )
        
        db.add(logs)
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="none",
    )
    
    return {"response" : "Password updated. Please log in again",
            "action_required": "reauthenticate"}