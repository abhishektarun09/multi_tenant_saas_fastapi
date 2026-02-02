from fastapi import status, HTTPException, Depends, APIRouter, Request, Response
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.models.users import Users
from core.utils import verify, audit_logs
from database.schemas.authorization_schemas import LoginOut, Token
from database.db.base import get_db
from core.oauth2 import create_access_token, create_refresh_token, verify_access_token
from core.config import env

REFRESH_TOKEN_EXPIRE_DAYS = env.refresh_token_expire_days

router = APIRouter(
    tags=['Authentication']
)

@router.post("/login", response_model=LoginOut)
def login(response: Response, request: Request, db: Session = Depends(get_db), user_credentials: OAuth2PasswordRequestForm = Depends()):
    
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
    
    access_token_data = {
        "user_id" : user.id,
        "token_type" : "access",
    }
    
    refresh_token_data = {
        "user_id" : user.id,
        "token_type" : "refresh",
    }
    
    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(refresh_token_data)
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=(REFRESH_TOKEN_EXPIRE_DAYS * 60 * 60 * 24),
    )
    
    
    return {"access_token" : access_token, "token_type" : "bearer"}


@router.post("/refresh_token", response_model=Token)
def refresh_token(response: Response, request: Request):
    
    refresh_token_value = request.cookies.get("refresh_token")
    
    if not refresh_token_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token missing")
    
    credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_access_token(token=refresh_token_value, credentials_exception=credentials_exception)
    
    if payload.token_type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    
    access_token_data = {
        "user_id" : payload.user_id,
        "token_type" : "access",
    }
    
    refresh_token_data = {
        "user_id" : payload.user_id,
        "token_type" : "refresh",
    }
    
    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(refresh_token_data)      
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=(REFRESH_TOKEN_EXPIRE_DAYS * 60 * 60 * 24),
    )
    
    return {"access_token" : access_token, "token_type" : "bearer"}