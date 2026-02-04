import pytest
from unittest.mock import AsyncMock
from main import get_echo_text, echo_handler

# 1. Тест простой функции логики
def test_echo_logic():
    input_text = "Привет"
    expected_output = "Вы написали: Привет"
    assert get_echo_text(input_text) == expected_output

# 2. Асинхронный тест обработчика (Mock-тест)
@pytest.mark.asyncio
async def test_echo_handler():
    # Создаем поддельное сообщение
    message = AsyncMock()
    message.text = "Hello"
    message.answer = AsyncMock()

    # Вызываем обработчик
    await echo_handler(message)

    # Проверяем, что метод answer был вызван с правильным текстом
    message.answer.assert_called_with("Вы написали: Hello")