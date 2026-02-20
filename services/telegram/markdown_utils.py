"""Utilities for safely injecting dynamic values into Telegram MarkdownV2 messages.

Use these helpers only for dynamic fragments (for example usernames, titles, and other
user-provided values). Do not pass fully formatted Markdown message templates here,
because escaping the whole template will break intended formatting.
"""

_MARKDOWN_V2_SPECIAL_CHARS = ("_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!")


def escape_markdown_v2(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters in a dynamic value."""
    escaped = text
    for char in _MARKDOWN_V2_SPECIAL_CHARS:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped
