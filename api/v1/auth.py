from fastapi import status, HTTPException, Depends, APIRouter, Request
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.models.users import Users
from database.models.organization_member import OrganizationMember
from core.utils import verify, audit_logs
from database.schemas.authorization_schemas import LoginOut
from database.db.base import get_db
from core.oauth2 import create_access_token

router = APIRouter(
    tags=['Authentication']
)

@router.post("/login", response_model=LoginOut)
def login(request: Request, db: Session = Depends(get_db), user_credentials: OAuth2PasswordRequestForm = Depends()):
    
    user = db.query(Users).filter(Users.email == user_credentials.username).first()
    
    if not user or not verify(user_credentials.password, user.password_hash):
        logs = audit_logs(
                    db=db,
                    action="login.failed",
                    resource_type="auth",
                    status="failed",
                    meta_data={"reason": "invalid_credentials"},
                    ip_address=request.client.host,
                    user_agent=request.headers.get("user-agent"),
                    endpoint="/login",
                )
        try:
            db.add(logs)
            db.commit()
            db.refresh(logs)
        except Exception:
            db.rollback()
            raise

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")
    
    logs = audit_logs(
                db=db,
                actor_user_id=user.id,
                action="login.success",
                resource_type="auth",
                resource_id=str(user.id),
                meta_data={"email": user.email},
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                endpoint="/login",
            )
    
    try:
        db.add(logs)
        db.commit()
        db.refresh(logs)
    except Exception:
        db.rollback()
        raise
    
    # List out the organizations the user is part of for frontend to select
    org_ids = db.query(OrganizationMember.organization_id).filter(user.id == OrganizationMember.user_id).all()
    org_ids = [org_id for (org_id,) in org_ids]
    
    jwt_data = {
        "user_id" : user.id
    }
    
    jwt_token = create_access_token(jwt_data)
    
    return {"access_token" : jwt_token, "token_type" : "bearer", "org_ids": org_ids}