import json

from core.redis.redis_config import redis_client as redis
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

    # get current version for this org from Redis (or default to 1)
    version_key = f"org_id:{membership.organization_id}:version"
    version = await redis.get(version_key)
    if version is None:
        version = 1
        await redis.set(version_key, version)

    cache_key = f"org_id:{membership.organization_id}:v{version}:page:{page}:page_size:{page_size}/organizations/get_users"
    cached_users_in_org = await redis.get(cache_key)

    if cached_users_in_org:
        cached_data = json.loads(cached_users_in_org)
        return ListUsers.model_validate(cached_data)

    else:
        offset = (page - 1) * page_size

        users_in_org = (
            (
                await db.execute(
                    select(Users)
                    .join(OrganizationMember, OrganizationMember.user_id == Users.id)
                    .where(
                        OrganizationMember.organization_id
                        == membership.organization_id,
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

        users_in_org = ListUsers(
            page=page, page_size=page_size, user_details=user_details
        )

        await redis.set(cache_key, users_in_org.model_dump_json(), ex=60 * 5)

        return users_in_org
