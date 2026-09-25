"""
agent.py
BONUS: takes the action the LLM proposed (see llm.py's `action` fenced block)
and "executes" it. For a hackathon demo, executing means writing it into a
local actions table that the frontend renders as a to-do/outbox list -- this
is enough to demonstrate an autonomous agent loop (retrieve -> decide -> act)
without needing real Gmail/Calendar OAuth. Swap `execute_action` internals for
real API calls (Google Calendar, Gmail) if you have time before the demo.
"""
import store


ALLOWED_TYPES = {"reminder", "draft_email", "calendar_event"}


def execute_action(action):
    if not action or action.get("type") not in ALLOWED_TYPES:
        return None
    action_id = store.add_action(action["type"], action.get("payload", {}))
    return {"id": action_id, "type": action["type"], "payload": action.get("payload", {})}
