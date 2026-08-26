from aiogram import Router
from .base import router as base_router
from .balance import router as balance_router
from .yookassa import router as yookassa_router
from .keys_config import router as keys_config_router
from .demo import router as demo_router

router = Router()
router.include_router(base_router)
router.include_router(balance_router)
router.include_router(yookassa_router)
router.include_router(keys_config_router)
router.include_router(demo_router)
