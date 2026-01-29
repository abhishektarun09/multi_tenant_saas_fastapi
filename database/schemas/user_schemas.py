from pydantic import BaseModel, Field, EmailStr
from typing import Literal
from datetime import datetime

from typing import Optional, Literal

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password_hash: str
    

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        orm_mode = True
