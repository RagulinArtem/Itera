"""
Custom aiogram FSM storage that persists state in Profiles.state column.
Data (extra FSM data dict) is kept in-memory — only the state string is in DB.
"""
from __future__ import annotations

from typing import Any, Dict

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType

from bot import database as db
from bot.fsm.states import DB_TO_STATE


class PostgresStateStorage(BaseStorage):
    """Stores FSM state in Profiles.state; data in memory."""

    def __init__(self) -> None:
        self._data: Dict[StorageKey, Dict[str, Any]] = {}

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        # Resolve state string for DB
        if state is None:
            db_value = None
        elif isinstance(state, State):
            db_value = state.state  # e.g. "IteraStates:awaiting_checkin"
        elif isinstance(state, str):
            db_value = state
        else:
            db_value = None

        # Store a short string in DB (just the part after colon, or None)
        short = None
        if db_value and ":" in db_value:
            short = db_value.split(":", 1)[1]
        elif db_value:
            short = db_value

        telegram_id = key.user_id
        await db.update_user_state(telegram_id, short)

    async def get_state(self, key: StorageKey) -> str | None:
        telegram_id = key.user_id
        user = await db.get_user_by_telegram_id(telegram_id)
        if not user or not user["state"]:
            return None
        db_state = user["state"]
        fsm_state = DB_TO_STATE.get(db_state)
        if fsm_state is not None:
            return fsm_state.state
        return None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        self._data[key] = data

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        return self._data.get(key, {})

    async def close(self) -> None:
        self._data.clear()
