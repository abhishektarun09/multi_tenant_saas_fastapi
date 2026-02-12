from fastapi import APIRouter
from .add_user import router as add_user_router
from .create import router as create_router
from .list_members import router as list_members_router
from .list_projects import router as list_projects_router
from .remove_user import router as remove_user_router
from .update import router as update_router
from .delete import router as delete_router

router = APIRouter(prefix="/project", tags=["Projects"])

router.include_router(create_router)
router.include_router(update_router)
router.include_router(delete_router)
router.include_router(list_members_router)
router.include_router(list_projects_router)
router.include_router(add_user_router)
router.include_router(remove_user_router)
