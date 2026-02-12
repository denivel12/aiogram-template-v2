from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from storages.psql.user.user_model import UserModel
from storages.redis.user.user_model import UserRD

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from stub import I18nContext

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("test"))
async def test_cmd(
    msg: Message,
    i18n: I18nContext,
    redis: Redis,
    db_pool: async_sessionmaker[AsyncSession],
) -> None:
    """Test PostgreSQL and Redis connections."""
    user = msg.from_user
    logger.info("User %s requested database/redis test", user.id)
    
    results = []
    
    # Test PostgreSQL
    pg_status = await test_postgresql(db_pool, user.id, user.full_name, user.username)
    results.append(pg_status)
    
    # Test Redis
    redis_status = await test_redis_connection(redis, user.id, user.full_name, user.username)
    results.append(redis_status)
    
    # Format results
    status_text = i18n.test.test_results(
        pg_status=pg_status["status"],
        pg_time=pg_status["time"],
        redis_status=redis_status["status"],
        redis_time=redis_status["time"],
        _path="cmds/test.ftl",
    )
    
    await msg.answer(status_text, parse_mode="HTML")


async def test_postgresql(db_pool, user_id: int, first_name: str, username: str | None) -> dict:
    """Test PostgreSQL connection by reading/writing user data."""
    start_time = time.time()
    
    try:
        async with db_pool() as session:
            # Try to get existing user
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model:
                # Update last_active
                user_model.last_active = datetime.utcnow()
            else:
                # Create new user
                user_model = UserModel(
                    id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=None,
                    pm_active=True,
                )
                session.add(user_model)
            
            await session.commit()
            
        elapsed = (time.time() - start_time) * 1000
        return {
            "status": "✅ OK",
            "time": f"{elapsed:.2f}ms",
        }
    except Exception as e:
        logger.error("PostgreSQL test failed: %s", e)
        elapsed = (time.time() - start_time) * 1000
        return {
            "status": f"❌ Error: {str(e)}",
            "time": f"{elapsed:.2f}ms",
        }


async def test_redis_connection(redis: Redis, user_id: int, first_name: str, username: str | None) -> dict:
    """Test Redis connection by reading/writing user data."""
    start_time = time.time()
    
    try:
        # Create test user data
        user_rd = UserRD(
            id=user_id,
            username=username,
            first_name=first_name,
            last_name=None,
            registration_datetime=datetime.utcnow(),
            pm_active=True,
        )
        
        # Save to Redis
        await user_rd.save(redis)
        
        # Read from Redis
        retrieved_user = await UserRD.get(redis, user_id)
        
        if retrieved_user and retrieved_user.first_name == first_name:
            elapsed = (time.time() - start_time) * 1000
            return {
                "status": "✅ OK",
                "time": f"{elapsed:.2f}ms",
            }
        else:
            elapsed = (time.time() - start_time) * 1000
            return {
                "status": "❌ Data mismatch",
                "time": f"{elapsed:.2f}ms",
            }
    except Exception as e:
        logger.error("Redis test failed: %s", e)
        elapsed = (time.time() - start_time) * 1000
        return {
            "status": f"❌ Error: {str(e)}",
            "time": f"{elapsed:.2f}ms",
        }
