from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core.config import env
from database.models.users import Users
from database.models.organization_member import OrganizationMember
from database.schemas.authorization_schemas import TokenData
from database.db.base import get_db
from typing import Tuple


bearer_scheme = HTTPBearer()
#oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

SECRET_KEY = env.secret_key
ALGORITHM = env.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = env.access_token_expire_minutes


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_access_token(token: str, credentials_exception):

    try:

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        org_id = payload.get("org_id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, org_id=org_id)
    except JWTError:
        raise credentials_exception

    return token_data

#def get_token_payload(token: str = Depends(oauth2_scheme)):
def get_token_payload(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials
    return verify_access_token(token, credentials_exception)



def get_current_user(payload = Depends(get_token_payload), db: Session = Depends(get_db)):

    user = db.query(Users).filter(Users.id == payload.user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    return user

def get_membership(payload = Depends(get_token_payload), db: Session = Depends(get_db)):
            
    org_id = payload.org_id
    
    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization not selected")
    
    membership = db.query(OrganizationMember).filter(OrganizationMember.user_id == payload.user_id, OrganizationMember.organization_id == org_id).first() #admin, member etc.
    
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    
    return membership

def get_user_and_membership(user=Depends(get_current_user), membership=Depends(get_membership)) -> Tuple[Users, OrganizationMember]:
    return user, membership