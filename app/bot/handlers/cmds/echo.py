from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

if TYPE_CHECKING:
    from stub import I18nContext

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("echo"))
async def echo_cmd(msg: Message, i18n: I18nContext) -> None:
    """Echo command - repeats the user's message."""
    args = msg.text.split(maxsplit=1)[1:] if msg.text else []
    text = args[0] if args else i18n.echo.no_text(_path="cmds/echo.ftl")
    
    logger.info("User %s echoed: %s", msg.from_user.id, text)
    await msg.answer(text)
