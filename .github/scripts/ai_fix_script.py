import os
from google import genai

# Используем новый клиент 2026 года
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

with open("test_log.txt", "r") as f:
    error_log = f.read()

# Промпт для модели Gemini 2.0 Flash
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=f"Мой бот упал с ошибкой:\n{error_log}\nПроанализируй код и напиши, как его исправить."
)

print("=== СОВЕТ ОТ ИИ ПО ИСПРАВЛЕНИЮ ===")
print(response.text)