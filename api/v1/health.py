from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.db.base import get_db
from sqlalchemy import text

from api.v1.schemas.health_schemas import Health

router = APIRouter(
    tags=['Health']
)

@router.get("/health", response_model=Health, status_code=status.HTTP_200_OK)
def health():
    return {"status": "ok"}

@router.get("/health/ready", response_model=Health, status_code=status.HTTP_200_OK)
def readiness(db: Session = Depends(get_db)):
    try:       
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="DB not ready")

    return {"status": "ready"}
