from handlers.personal_bot import router as personal_root_router
from handlers.personal_bot.routers.common import calendar as calendar_router


def _collect_router_names(router):
    names = [router.name]
    for sub in router.sub_routers:
        names.extend(_collect_router_names(sub))
    return names


def test_personal_root_router_includes_calendar_router():
    names = _collect_router_names(personal_root_router)
    assert "personal_bot_common_calendar" in names


def test_calendar_action_keyboard_does_not_have_create_button():
    keyboard = calendar_router._calendar_action_keyboard()
    callback_data = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert callback_data == ["calendar:select", "calendar:cancel_select"]
    assert "calendar:create" not in callback_data
