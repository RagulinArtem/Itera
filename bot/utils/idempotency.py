"""Middleware for deduplicating Telegram updates."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Update

from bot import database as db

logger = logging.getLogger(__name__)


class IdempotencyMiddleware(BaseMiddleware):
    """Skip updates that have already been processed (duplicate delivery)."""

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        update_id = event.update_id
        is_dup = await db.check_and_mark_update(update_id)
        if is_dup:
            logger.debug("Duplicate update %d, skipping", update_id)
            return None
        return await handler(event, data)
