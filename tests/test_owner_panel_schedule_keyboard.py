from handlers.personal_bot.routers.specialist.owner_panel import build_weekday_button_text


def test_build_weekday_button_text_marks_only_working_days():
    working_days = {0, 2, 4}

    assert build_weekday_button_text(0, working_days) == "✅ Пн"
    assert build_weekday_button_text(1, working_days) == "Вт"
    assert build_weekday_button_text(2, working_days) == "✅ Ср"
    assert build_weekday_button_text(3, working_days) == "Чт"
    assert build_weekday_button_text(4, working_days) == "✅ Пт"
    assert build_weekday_button_text(5, working_days) == "Сб"
    assert build_weekday_button_text(6, working_days) == "Вс"
