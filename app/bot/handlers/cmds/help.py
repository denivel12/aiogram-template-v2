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


@router.message(Command("help"))
async def help_cmd(msg: Message, i18n: I18nContext) -> None:
    logger.info("User %s requested help", msg.from_user.id)
    await msg.answer(
        i18n.help.help_text(_path="cmds/help.ftl"),
        parse_mode="HTML",
    )
