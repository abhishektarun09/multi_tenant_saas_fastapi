from pydantic import BaseModel, Field, EmailStr
from typing import Literal
from datetime import datetime

from typing import Optional, Literal

class OrganizationCreate(BaseModel):
    name: str    

class OrganizationOut(BaseModel):
    id: int
    slug: str
    created_at: datetime

    class Config:
        orm_mode = True
