import os
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash') # Быстрый и бесплатный

with open("test_log.txt", "r") as f:
    error_log = f.read()

prompt = f"Мой бот упал с ошибкой:\n{error_log}\nПроанализируй код и напиши, как его исправить."
response = model.generate_content(prompt)

print("=== СОВЕТ ОТ ИИ ПО ИСПРАВЛЕНИЮ ===")
print(response.text)