from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    user_id: int
    token_type: str
    org_id: Optional[int] = None
    jti: str
    
class LoginOut(BaseModel):
    access_token: str
    token_type: str
    
class LogoutResponse(BaseModel):
    response: str