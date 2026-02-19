from fastapi import APIRouter
from .login import router as login_router
from .logout import router as logout_router
from .refresh_token import router as refresh_token_router
from .google_auth import router as google_router

router = APIRouter(prefix="/v2/auth", tags=["Authentication"])

router.include_router(login_router)
router.include_router(logout_router)
router.include_router(refresh_token_router)
router.include_router(google_router)
