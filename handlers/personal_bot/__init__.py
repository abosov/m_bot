from aiogram import Router

from handlers.personal_bot.role_guard import SpecialistRoleGuardMiddleware
from handlers.personal_bot.routers.client.commands import router as client_router
from handlers.personal_bot.routers.common.start import router as common_router
from handlers.personal_bot.routers.specialist.commands import router as specialist_router

router = Router(name="personal_bot_root")

specialist_router.message.middleware(SpecialistRoleGuardMiddleware())
specialist_router.callback_query.middleware(SpecialistRoleGuardMiddleware())

router.include_router(common_router)
router.include_router(specialist_router)
router.include_router(client_router)

__all__ = ["router"]
