import google.generativeai as genai
from config import get_config

config = get_config()
genai.configure(api_key=config.GOOGLE_API_KEY)

print("사용 가능한 모델 목록:\n")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"- {model.name}")
