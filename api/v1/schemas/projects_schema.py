from typing import List
from pydantic import BaseModel, EmailStr

class AddProjectsOut(BaseModel):
    name: str
    organization_id: int
    created_by: int
    
class AddProjectsIn(BaseModel):
    name: str
    
class AddUsersOut(BaseModel):
    user_id: int
    project_id: int
    
class AddUsersIn(BaseModel):
    email: EmailStr
    project_id: int