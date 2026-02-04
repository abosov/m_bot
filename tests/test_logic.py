from main import TOKEN

def test_token_format():
    # Проверяем, что токен содержит двоеточие
    assert ":" in TOKEN
    # А теперь сломаем тест специально:
    assert TOKEN == "ОШИБКА"