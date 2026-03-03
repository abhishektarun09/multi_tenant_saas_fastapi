from fastapi import Query, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.rate_limiter import RateLimiter
from database.models.organization_member import OrganizationMember
from api.v2.schemas.organization_schemas import ListUsers
from database.models.users import Users
from database.db.session import get_db
from core.oauth2 import get_user_and_membership

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.get("/users", status_code=status.HTTP_200_OK, response_model=ListUsers)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    user, membership = current_user_and_membership

    if membership.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view users organization",
        )

    offset = (page - 1) * page_size

    users_in_org = (
        (
            await db.execute(
                select(Users)
                .join(OrganizationMember, OrganizationMember.user_id == Users.id)
                .where(
                    OrganizationMember.organization_id == membership.organization_id,
                    Users.is_deleted.is_(False),
                )
                .order_by(Users.id.asc())
                .offset(offset)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    if not users_in_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No users in Organization"
        )

    user_details = [
        {"user_id": user.id, "name": user.name, "email": user.email}
        for user in users_in_org
    ]

    return {"page": page, "page_size": page_size, "user_details": user_details}
