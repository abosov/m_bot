from aiogram import Router

from handlers.personal_bot.routers.client.commands import router as client_router
from handlers.personal_bot.routers.common.start import router as common_router
from handlers.personal_bot.routers.specialist import router as specialist_router

router = Router(name="personal_bot_root")

router.include_router(common_router)
router.include_router(specialist_router)
router.include_router(client_router)

__all__ = ["router"]
