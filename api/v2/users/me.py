from fastapi import Depends, APIRouter
from core.oauth2 import get_user_and_membership
from core.rate_limiter import RateLimiter
from api.v2.schemas.user_schemas import Me

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.get("/me", response_model=Me)
async def me(
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "org_id": membership.organization_id,
        "role": membership.role,
    }
