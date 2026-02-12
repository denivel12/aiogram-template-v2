from aiogram import Router

from . import echo, help, info, language_settings, start, test

router = Router()
router.include_routers(
    echo.router,
    help.router,
    info.router,
    language_settings.router,
    start.router,
    test.router,
)
