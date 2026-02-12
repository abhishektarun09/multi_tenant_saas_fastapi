from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from core.oauth2 import get_current_user
from database.models.organization_member import OrganizationMember
from database.models.users import Users
from api.v2.schemas.organization_schemas import ListOrgs
from database.db.session import get_db
from sqlalchemy import select

router = APIRouter()


@router.get("/orgs", response_model=ListOrgs)
async def list_orgs(
    db: AsyncSession = Depends(get_db), current_user: int = Depends(get_current_user)
):

    user = (
        (
            await db.execute(
                select(Users).where(
                    Users.id == current_user.id, Users.is_deleted.is_(False)
                )
            )
        )
        .scalars()
        .first()
    )

    # List out the organizations the user is part of for frontend to select
    org_ids = (
        (
            await db.execute(
                select(OrganizationMember.organization_id).where(
                    OrganizationMember.user_id == user.id
                )
            )
        )
        .scalars()
        .all()
    )

    return {"email": user.email, "org_ids": org_ids}
