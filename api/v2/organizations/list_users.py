from fastapi import status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.organization_member import OrganizationMember
from api.v2.schemas.organization_schemas import ListUsers
from database.models.users import Users
from database.db.session import get_db
from core.oauth2 import get_user_and_membership

router = APIRouter()


@router.get("/users", status_code=status.HTTP_200_OK, response_model=ListUsers)
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    user, membership = current_user_and_membership

    if membership.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view users organization",
        )

    users_in_org = (
        (
            await db.execute(
                select(Users)
                .join(OrganizationMember, OrganizationMember.user_id == Users.id)
                .where(
                    OrganizationMember.organization_id == membership.organization_id,
                    Users.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )

    if not users_in_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No users in Organization"
        )

    user_details = [{"name": user.name, "email": user.email} for user in users_in_org]

    return {"user_details": user_details}
