from aiogram.fsm.state import State, StatesGroup


class IteraStates(StatesGroup):
    idle = State()
    awaiting_checkin = State()
    awaiting_goal_text = State()
    awaiting_nickname = State()
    awaiting_email = State()
    awaiting_feedback = State()


# Map DB string values to FSM states and back
STATE_TO_DB: dict[State, str | None] = {
    IteraStates.idle: None,
    IteraStates.awaiting_checkin: "awaiting_checkin",
    IteraStates.awaiting_goal_text: "awaiting_goal_text",
    IteraStates.awaiting_nickname: "awaiting_nickname",
    IteraStates.awaiting_email: "awaiting_email",
    IteraStates.awaiting_feedback: "awaiting_feedback",
}

DB_TO_STATE: dict[str | None, State | None] = {
    None: None,
    "awaiting_checkin": IteraStates.awaiting_checkin,
    "awaiting_goal_text": IteraStates.awaiting_goal_text,
    "awaiting_nickname": IteraStates.awaiting_nickname,
    "awaiting_email": IteraStates.awaiting_email,
    "awaiting_feedback": IteraStates.awaiting_feedback,
}
