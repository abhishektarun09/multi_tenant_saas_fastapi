from fastapi import Depends, APIRouter, HTTPException, Request, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from core.logger import logger
from core.rate_limiter import RateLimiter
from database.models.jti_blocklist import JtiBlocklist
from core.utils import get_valid_refresh_payload
from api.v2.schemas.authorization_schemas import LogoutResponse
from database.db.session import get_db

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response, request: Request, db: AsyncSession = Depends(get_db)
):

    payload = await get_valid_refresh_payload(request, db)

    jti_value = payload.jti
    blacklisted_jti = JtiBlocklist(jti=jti_value)

    try:
        db.add(blacklisted_jti)
        await db.commit()

    except SQLAlchemyError as e:
        await db.rollback()

        logger.exception(
            "Database error",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )

    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return {"response": "Logged out successfully"}
