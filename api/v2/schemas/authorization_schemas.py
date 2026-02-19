from pydantic import BaseModel, EmailStr
from typing import List, Optional


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


class EmailModel(BaseModel):
    email_addresses: List[str]


class GoogleUser(BaseModel):
    id: str
    email: EmailStr
    name: str
    picture: str
    verified_email: bool
