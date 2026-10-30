"""H9: Gemini bağlantı testi. Anahtar .env dosyasından okunur, ekrana YAZILMAZ.

Çalıştırma (repo klasöründeyken):  python3 src/gemini_deneme.py
"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # proje klasöründeki .env dosyasını okur
anahtar = os.environ.get("GEMINI_API_KEY")
model_adi = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

if not anahtar:
    raise SystemExit("Anahtar YOK ❌  .env dosyasında GEMINI_API_KEY=... satırı var mı?")
print("Anahtar bulundu ✅")

# 30 saniyede cevap gelmezse dur, hata varsa tekrar denemeden hemen göster
istemci = genai.Client(
    api_key=anahtar,
    http_options=types.HttpOptions(
        timeout=30_000, retry_options=types.HttpRetryOptions(attempts=1)
    ),
)
print(f"Gemini'ye soruluyor ({model_adi})...")
cevap = istemci.models.generate_content(
    model=model_adi,
    contents="Bana Türkçe tek kelimeyle 'merhaba' de.",
)
print("Gemini cevabı:", cevap.text)
