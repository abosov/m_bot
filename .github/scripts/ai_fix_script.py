import os
from google import genai

# Используем новый клиент 2026 года
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

with open("test_log.txt", "r") as f:
    error_log = f.read()

# Замените gemini-2.0-flash на gemini-1.5-flash
response = client.models.generate_content(
    model='gemini-1.5-flash', 
    contents=f"Мой бот упал с ошибкой:\n{error_log}\nПроанализируй код и напиши, как его исправить."
)

print("=== СОВЕТ ОТ ИИ ПО ИСПРАВЛЕНИЮ ===")
print(response.text)