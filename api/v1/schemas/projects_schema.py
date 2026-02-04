from pydantic import BaseModel

class AddProjectsOut(BaseModel):
    name: str
    organization_id: int
    created_by: int
    
class AddProjectsIn(BaseModel):
    name: str