from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from core.oauth2 import get_user_and_membership
from database.models.users import Users
from api.v2.schemas.user_schemas import Me
from database.db.session import get_db
from sqlalchemy import select

router = APIRouter()


@router.get("/me", response_model=Me)
async def me(
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    user_details = (
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

    return {
        "email": user_details.email,
        "name": user_details.name,
        "role": membership.role,
    }
