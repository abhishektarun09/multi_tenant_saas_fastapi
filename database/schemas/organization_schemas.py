from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Literal
from datetime import datetime

from typing import Optional, Literal

class OrganizationCreate(BaseModel):
    name: str    

class OrganizationOut(BaseModel):
    id: int
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
class SelectOrganization(BaseModel):
    org_id: int