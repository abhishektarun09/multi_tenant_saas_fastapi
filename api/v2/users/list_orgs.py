import json

from fastapi import Depends, APIRouter
from core.redis.redis_config import redis_client as redis
from sqlalchemy.ext.asyncio import AsyncSession
from core.oauth2 import get_current_user
from core.rate_limiter import RateLimiter
from database.models.organization_member import OrganizationMember
from api.v2.schemas.organization_schemas import ListOrgs
from database.db.session import get_db
from sqlalchemy import select

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.get("/orgs", response_model=ListOrgs)
async def list_orgs(
    db: AsyncSession = Depends(get_db), current_user: int = Depends(get_current_user)
):

    cache_key = f"user_id:{current_user.id}:/users/orgs"
    cached_user = await redis.get(cache_key)

    if cached_user:
        cached_data = json.loads(cached_user)
        return ListOrgs.model_validate(cached_data)

    else:
        # List out the organizations the user is part of for frontend to select
        org_ids = (
            (
                await db.execute(
                    select(OrganizationMember.organization_id).where(
                        OrganizationMember.user_id == current_user.id
                    )
                )
            )
            .scalars()
            .all()
        )

        user_data = ListOrgs(email=current_user.email, org_ids=org_ids)

        await redis.set(cache_key, user_data.model_dump_json(), ex=60 * 5)

        return user_data
