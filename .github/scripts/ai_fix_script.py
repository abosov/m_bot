import os
from google import genai
from google.genai import errors

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

try:
    with open("test_log.txt", "r") as f:
        error_log = f.read()

    # Исправляем 404: в новом SDK используем только имя модели
    response = client.models.generate_content(
        model='gemini-1.5-flash', 
        contents=f"Мой бот упал с ошибкой:\n{error_log}\nПроанализируй код и предложи исправление."
    )

    print("=== СОВЕТ ОТ ИИ ПО ИСПРАВЛЕНИЮ ===")
    print(response.text)

except errors.ClientError as e:
    print(f"Ошибка API (лимиты или модель): {e}")
except Exception as e:
    print(f"Ошибка: {e}")
