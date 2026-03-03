from pydantic import BaseModel, EmailStr


class UserSchema(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_verified: bool
    status: str
    is_deleted: bool

    model_config = {"from_attributes": True}


class OrganizationMemberSchema(BaseModel):
    user_id: int
    organization_id: int
    role: str

    model_config = {"from_attributes": True}
