from handlers.personal_bot.routers.specialist.settings_view import build_specialist_settings_view


class _Profile:
    specialist_timezone = "Europe/Moscow"
    session_duration_min = 60
    session_buffer_min = 10
    slot_step_min = 15
    max_sessions_per_day = 4
    cancel_window_hours = 12
    tariff_plan = "start"


class _Row:
    weekday = 0
    is_working = True
    interval_1_start = None
    interval_1_end = None
    interval_2_start = None
    interval_2_end = None
    interval_3_start = None
    interval_3_end = None


class _Calendar:
    calendar_id = "cal-id"
    calendar_summary = "Основной"
    calendar_time_zone = "Europe/Moscow"
    last_smoke_test_status = "ok"


def test_build_specialist_settings_view_has_unified_block_order() -> None:
    text, keyboard = build_specialist_settings_view(
        profile=_Profile(),
        rows=[_Row()],
        calendar_settings=_Calendar(),
        keep_button_text=None,
        keep_callback_data=None,
        include_reset_button=True,
        working_intervals_by_idx={1: (540, 720), 2: (780, 1020), 3: (1020, 1260)},
    )

    assert text.index("Календарь:") < text.index("Параметры записи:")
    assert text.index("Параметры записи:") < text.index("Часовой пояс специалиста:")
    assert text.index("Часовой пояс специалиста:") < text.index("Расписание:")
    assert "• Тариф: Start" in text

    button_texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert button_texts[:5] == [
        "📅 Сменить календарь",
        "⏱️ Изменить длительность и буфер",
        "⚙️ Изменить лимиты (max/day, шаг слота)",
        "🌍 Сменить часовой пояс специалиста",
        "📅 Изменить расписание и интервалы",
    ]

    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert callbacks == [
        "owner_panel:calendar_menu",
        "owner_panel:change_duration_buffer",
        "owner_panel:slot_params_menu",
        "owner_panel:change_timezone",
        "owner_panel:change_schedule",
        "owner_panel:profile_edit_link",
        "owner_panel:apply_defaults",
    ]


def test_build_specialist_settings_view_omits_disabled_first_interval() -> None:
    text, _ = build_specialist_settings_view(
        profile=_Profile(),
        rows=[_Row()],
        calendar_settings=_Calendar(),
        keep_button_text=None,
        keep_callback_data=None,
        include_reset_button=True,
        working_intervals_by_idx={1: (None, None), 2: (780, 1020), 3: (1020, 1260)},
    )

    assert "• Интервалы: 13:00–17:00, 17:00–21:00" in text


def test_build_specialist_settings_view_when_all_intervals_disabled_shows_dash() -> None:
    text, _ = build_specialist_settings_view(
        profile=_Profile(),
        rows=[_Row()],
        calendar_settings=_Calendar(),
        keep_button_text=None,
        keep_callback_data=None,
        include_reset_button=True,
        working_intervals_by_idx={1: (None, None), 2: (None, None), 3: (None, None)},
    )

    assert "• Интервалы: —" in text


def test_build_specialist_settings_view_includes_profile_edit_callback_button() -> None:
    _, keyboard = build_specialist_settings_view(
        profile=_Profile(),
        rows=[_Row()],
        calendar_settings=_Calendar(),
        keep_button_text=None,
        keep_callback_data=None,
        include_reset_button=True,
        working_intervals_by_idx={1: (540, 720), 2: (780, 1020), 3: (1020, 1260)},
    )

    all_buttons = [button for row in keyboard.inline_keyboard for button in row]
    profile_button = next((b for b in all_buttons if b.text == "✏️ Редактировать профиль специалиста"), None)
    reset_button = next((b for b in all_buttons if b.text == "♻️ Сбросить на дефолты"), None)

    assert profile_button is not None
    assert reset_button is not None
    assert profile_button.url is None
    assert profile_button.callback_data == "owner_panel:profile_edit_link"

    profile_button_idx = all_buttons.index(profile_button)
    reset_button_idx = all_buttons.index(reset_button)
    assert profile_button_idx < reset_button_idx


def test_build_specialist_settings_view_always_shows_profile_edit_callback_button() -> None:
    _, keyboard = build_specialist_settings_view(
        profile=_Profile(),
        rows=[_Row()],
        calendar_settings=_Calendar(),
        keep_button_text=None,
        keep_callback_data=None,
        include_reset_button=True,
        working_intervals_by_idx={1: (540, 720), 2: (780, 1020), 3: (1020, 1260)},
    )

    all_buttons = [button for row in keyboard.inline_keyboard for button in row]
    profile_button = next((b for b in all_buttons if b.text == "✏️ Редактировать профиль специалиста"), None)
    assert profile_button is not None
    assert profile_button.callback_data == "owner_panel:profile_edit_link"


def test_build_specialist_settings_view_includes_public_page_url_button_when_provided() -> None:
    _, keyboard = build_specialist_settings_view(
        profile=_Profile(),
        rows=[_Row()],
        calendar_settings=_Calendar(),
        keep_button_text=None,
        keep_callback_data=None,
        include_reset_button=True,
        working_intervals_by_idx={1: (540, 720), 2: (780, 1020), 3: (1020, 1260)},
        public_page_url="https://zumbot.ru/Valid_Slug123",
    )

    all_buttons = [button for row in keyboard.inline_keyboard for button in row]
    public_page_button = next((b for b in all_buttons if b.text == "🌐 Открыть публичную страницу"), None)
    profile_button = next((b for b in all_buttons if b.text == "✏️ Редактировать профиль специалиста"), None)

    assert profile_button is not None
    assert public_page_button is not None
    assert public_page_button.url == "https://zumbot.ru/Valid_Slug123"
    assert public_page_button.callback_data is None
    assert all_buttons.index(profile_button) < all_buttons.index(public_page_button)


def test_build_specialist_settings_view_omits_public_page_url_button_when_missing() -> None:
    _, keyboard = build_specialist_settings_view(
        profile=_Profile(),
        rows=[_Row()],
        calendar_settings=_Calendar(),
        keep_button_text=None,
        keep_callback_data=None,
        include_reset_button=True,
        working_intervals_by_idx={1: (540, 720), 2: (780, 1020), 3: (1020, 1260)},
        public_page_url=None,
    )

    button_texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "🌐 Открыть публичную страницу" not in button_texts
