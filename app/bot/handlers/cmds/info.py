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


@router.message(Command("info"))
async def info_cmd(msg: Message, i18n: I18nContext) -> None:
    """Info command - shows user and chat information."""
    user = msg.from_user
    chat = msg.chat
    
    logger.info("User %s requested info", user.id)
    
    info_text = i18n.info.info_text(
        user_id=user.id,
        user_name=user.full_name,
        username=f"@{user.username}" if user.username else i18n.info.no_username(_path="cmds/info.ftl"),
        chat_id=chat.id,
        chat_type=chat.type,
        _path="cmds/info.ftl",
    )
    
    await msg.answer(info_text, parse_mode="HTML")
