from fastapi import APIRouter, Depends, HTTPException, status
from database.db.session import get_db
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.v2.schemas.health_schemas import Health

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=Health, status_code=status.HTTP_200_OK)
def health():
    return {"status": "ok"}


@router.get("/health/db", response_model=Health)
async def check_db(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "db ready"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DB not ready",
        )