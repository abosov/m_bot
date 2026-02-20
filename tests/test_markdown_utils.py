from services.telegram.markdown_utils import escape_markdown_v2


def test_escape_markdown_v2_username_with_underscores() -> None:
    assert escape_markdown_v2("david_psy_123bot") == "david\\_psy\\_123bot"


def test_escape_markdown_v2_without_special_chars() -> None:
    assert escape_markdown_v2("davidpsy123bot") == "davidpsy123bot"


def test_escape_markdown_v2_multiple_special_chars() -> None:
    assert escape_markdown_v2("name_[bot](v2)!") == "name\\_\\[bot\\]\\(v2\\)\\!"
