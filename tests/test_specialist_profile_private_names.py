from services.specialist_profile_private import build_display_name, split_display_name


def test_split_display_name_rules():
    assert split_display_name("") == ("", "", "")
    assert split_display_name("Анна") == ("Анна", "", "")
    assert split_display_name("Анна Петрова") == ("Анна", "", "Петрова")
    assert split_display_name("Анна Сергеевна Петрова") == ("Анна", "Сергеевна", "Петрова")


def test_build_display_name_skips_empty_parts():
    assert build_display_name("Анна", "", "Петрова") == "Анна Петрова"
    assert build_display_name("Анна", "Сергеевна", "Петрова") == "Анна Сергеевна Петрова"
