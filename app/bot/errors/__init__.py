from aiogram import Router

from . import aiogram_errors


def get_errors_router() -> Router:
    router = Router()

    router.include_routers(aiogram_errors.router)

    return router
