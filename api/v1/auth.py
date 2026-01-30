from fastapi import status, HTTPException, Depends, APIRouter
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.models.users import Users
from core.utils import verify
from database.schemas.authorization_schemas import Token
from database.db.base import get_db
from core.oauth2 import create_access_token

router = APIRouter(
    tags=['Authentication']
)

@router.post("/login", response_model=Token)
def login(db: Session = Depends(get_db), user_credentials: OAuth2PasswordRequestForm = Depends()):
    
    user = db.query(Users).filter(Users.email == user_credentials.username).first()
    
    if not user or not verify(user_credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")
    
    jwt_data = {
        "user_id" : user.id
    }
    
    jwt_token = create_access_token(jwt_data)
    
    return {"access_token" : jwt_token, "token_type" : "bearer"}