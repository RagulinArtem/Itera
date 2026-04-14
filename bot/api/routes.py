"""REST API for Telegram Mini App."""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta

from aiohttp import web

from bot import database as db
from bot.api.auth import validate_init_data
from bot.services.achievements import (
    ACHIEVEMENT_DEFS,
    LEVELS,
    get_level,
    get_next_level,
    get_user_achievements,
)

logger = logging.getLogger(__name__)


def _json(data: dict, status: int = 200) -> web.Response:
    return web.json_response(data, status=status)


async def _get_user(request: web.Request):
    """Extract and validate Telegram user from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("tma "):
        return None, _json({"error": "unauthorized"}, 401)

    init_data = auth[4:]
    tg_user = validate_init_data(init_data)
    if not tg_user:
        return None, _json({"error": "invalid init data"}, 401)

    user = await db.get_or_create_user(tg_user["id"])
    return user, None


# ── Profile ──────────────────────────────────

async def get_profile(request: web.Request) -> web.Response:
    user, err = await _get_user(request)
    if err:
        return err

    xp = user["xp"] or 0
    level = get_level(xp)
    next_lvl = get_next_level(xp)

    return _json({
        "nickname": user["nickname"] or "",
        "xp": xp,
        "streak": user["streak"] or 0,
        "ai_mode": user["ai_mode"] or "focus",
        "last_checkin_date": str(user["last_checkin_date"]) if user["last_checkin_date"] else None,
        "level": {
            "number": level.number,
            "name": level.name,
            "icon": level.icon,
            "min_xp": level.min_xp,
        },
        "next_level": {
            "number": next_lvl.number,
            "name": next_lvl.name,
            "icon": next_lvl.icon,
            "min_xp": next_lvl.min_xp,
        } if next_lvl else None,
    })


# ── Achievements ─────────────────────────────

async def get_achievements(request: web.Request) -> web.Response:
    user, err = await _get_user(request)
    if err:
        return err

    unlocked = await get_user_achievements(user["id"])

    categories = [
        ("Чекины", ["first_checkin", "streak_3", "streak_7", "streak_14", "streak_30",
                     "checkins_10", "checkins_50", "checkins_100"]),
        ("Цели", ["first_goal", "goal_completed", "goals_5", "goals_completed_3"]),
        ("Аналитика", ["first_report", "reports_5"]),
        ("Режимы", ["try_psychologist", "try_coach", "try_reflection", "all_modes"]),
        ("Уровни", ["level_3", "level_5", "level_7"]),
    ]

    result = []
    for cat_name, codes in categories:
        items = []
        for code in codes:
            defn = ACHIEVEMENT_DEFS[code]
            items.append({
                "code": code,
                "icon": defn.icon,
                "name": defn.name,
                "description": defn.description,
                "xp_reward": defn.xp_reward,
                "unlocked": code in unlocked,
            })
        result.append({"category": cat_name, "achievements": items})

    return _json({
        "total": len(ACHIEVEMENT_DEFS),
        "unlocked": len(unlocked & set(ACHIEVEMENT_DEFS.keys())),
        "categories": result,
    })


# ── Goals ────────────────────────────────────

async def get_goals(request: web.Request) -> web.Response:
    user, err = await _get_user(request)
    if err:
        return err

    goals = await db.get_all_goals(user["id"])
    result = []
    for g in goals:
        plan = g["plan"]
        if isinstance(plan, str):
            plan = json.loads(plan)
        result.append({
            "id": str(g["id"]),
            "goal": g["goal"],
            "status": g["status"],
            "progress": g["progress"],
            "plan": plan,
            "created_at": g["created_at"].isoformat(),
            "completed_at": g["completed_at"].isoformat() if g["completed_at"] else None,
        })

    return _json({"goals": result})


# ── Activity calendar (last 90 days) ────────

async def get_activity(request: web.Request) -> web.Response:
    user, err = await _get_user(request)
    if err:
        return err

    rows = await db._get_pool().fetch(
        """
        SELECT entry_date, COUNT(*) as cnt
        FROM journal_entries
        WHERE user_id = $1 AND entry_date >= $2
        GROUP BY entry_date
        ORDER BY entry_date
        """,
        user["id"],
        date.today() - timedelta(days=89),
    )

    activity = {str(r["entry_date"]): r["cnt"] for r in rows}
    return _json({"activity": activity})


# ── Checkin history ──────────────────────────

async def get_checkins(request: web.Request) -> web.Response:
    user, err = await _get_user(request)
    if err:
        return err

    limit = min(int(request.query.get("limit", "30")), 100)
    entries = await db.get_journal_entries(user["id"], limit=limit)

    result = []
    for e in entries:
        analysis = e["analysis"]
        if isinstance(analysis, str):
            analysis = json.loads(analysis)
        result.append({
            "date": str(e["entry_date"]),
            "text": e["checkin_text"],
            "analysis": analysis,
            "created_at": e["created_at"].isoformat(),
        })

    return _json({"checkins": result})


# ── Levels reference ─────────────────────────

async def get_levels(request: web.Request) -> web.Response:
    return _json({
        "levels": [
            {"number": l.number, "name": l.name, "min_xp": l.min_xp, "icon": l.icon}
            for l in LEVELS
        ]
    })


# ── Route setup ──────────────────────────────

def setup_api_routes(app: web.Application) -> None:
    app.router.add_get("/api/profile", get_profile)
    app.router.add_get("/api/achievements", get_achievements)
    app.router.add_get("/api/goals", get_goals)
    app.router.add_get("/api/activity", get_activity)
    app.router.add_get("/api/checkins", get_checkins)
    app.router.add_get("/api/levels", get_levels)
