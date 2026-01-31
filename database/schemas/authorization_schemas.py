from pydantic import BaseModel
from typing import Optional, List

class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    id: Optional[int] = None
    org_id: Optional[int] = None
    
class LoginOut(BaseModel):
    access_token: str
    token_type: str
    org_ids: List[int]