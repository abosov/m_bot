from services.client_display import format_client_display, normalize_telegram_username


def test_normalize_telegram_username_strips_at_and_spaces():
    assert normalize_telegram_username("  @ivan_petrov  ") == "ivan_petrov"


def test_normalize_telegram_username_handles_empty_values():
    assert normalize_telegram_username(None) is None
    assert normalize_telegram_username("   ") is None


def test_format_client_display_with_username():
    assert format_client_display(display_name="Иван Петров", tg_username="@ivan_petrov") == "Иван Петров (@ivan_petrov)"


def test_format_client_display_without_username():
    assert format_client_display(display_name="Иван Петров", tg_username=None) == "Иван Петров"
