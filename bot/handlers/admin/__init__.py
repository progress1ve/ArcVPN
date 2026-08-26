"""
Подключение роутеров админ-панели.
"""
from aiogram import Router

from bot.handlers.admin.main import router as main_router

admin_router = Router()

admin_router.include_router(main_router)
