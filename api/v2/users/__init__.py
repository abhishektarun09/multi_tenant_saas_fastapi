from fastapi import APIRouter
from .list_orgs import router as list_orgs_router
from .me import router as me_router
from .register import router as register_router
from .update_password import router as update_password_router


router = APIRouter(prefix="/user", tags=["Users"])

router.include_router(list_orgs_router)
router.include_router(me_router)
router.include_router(register_router)
router.include_router(update_password_router)
