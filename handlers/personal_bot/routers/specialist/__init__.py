from aiogram import Router

from handlers.personal_bot.role_guard import SpecialistRoleGuardMiddleware
from .commands import router as commands_router
from .owner_panel import router as owner_panel_router

router = Router(name="personal_bot_specialist")
router.include_router(commands_router)
router.include_router(owner_panel_router)

router.message.middleware(SpecialistRoleGuardMiddleware())
router.callback_query.middleware(SpecialistRoleGuardMiddleware())

__all__ = ["router"]
