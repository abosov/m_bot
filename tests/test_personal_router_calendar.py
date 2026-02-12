from handlers.personal_bot import router as personal_root_router


def _collect_router_names(router):
    names = [router.name]
    for sub in router.sub_routers:
        names.extend(_collect_router_names(sub))
    return names


def test_personal_root_router_includes_calendar_router():
    names = _collect_router_names(personal_root_router)
    assert "personal_bot_common_calendar" in names
