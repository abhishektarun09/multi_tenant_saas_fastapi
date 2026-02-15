from fastapi import APIRouter
from .add_user import router as add_user_router
from .list_users import router as list_users_router
from .register import router as register_router
from .select import router as select_router
from .update import router as update_router
from .delete import router as delete_router
from .remove_member import router as remove_member_router

router = APIRouter(prefix="/v2/organization", tags=["Organizations"])

router.include_router(select_router)
router.include_router(add_user_router)
router.include_router(list_users_router)
router.include_router(register_router)
router.include_router(update_router)
router.include_router(delete_router)
router.include_router(remove_member_router)
