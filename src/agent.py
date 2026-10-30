"""Müdahale ajanı. Gemini, beş araçtan hangisini çağıracağına kendisi karar verir.

Araçlar:
    sensor_durumu_oku()      -> simülatörün o anki sensör satırı
    kamera_sonucu_al()       -> son görüntü tahmini (p_alev, p_duman)
    prosedur_ara(soru)       -> asistan_cevapla ile bilgi tabanından cevap
    itfaiyeye_bildir(ozet)   -> SADECE günlüğe "112 ARANDI (SİMÜLASYON)" yazar
    adimi_tamamla(adim_no)   -> prosedür adımını tamamlandı olarak işaretler

Arayüz (app/main.py) her saniye `durum` sözlüğünü günceller; araçlar oradan okur.

Kullanım (başka bir dosyadan):
    from src.agent import ajana_sor, durum
    durum["sensor_satiri"] = {...}
    print(ajana_sor("Şu an yangın var mı?"))

Deneme (repo klasöründeyken):  python3 src/agent.py
"""
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))  # "python3 src/agent.py" ile çalışınca da src bulunsun

from src.rag import asistan_cevapla

load_dotenv(REPO / ".env")
MODEL_ADI = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

# Arayüzle ajan arasındaki ortak tahta: app/main.py yazar, araçlar okur.
durum = {
    "sensor_satiri": {},        # o anki sensör ölçümleri
    "kamera": {"p_alev": 0.0, "p_duman": 0.0},
    "bina_tipi": "otel",
    "bolge": "3. kat koridor",
    "gunluk": [],               # ajanın yazdığı olaylar (arayüz bunları kendi günlüğüne ekler)
    "tamamlanan_adimlar": [],   # tamamlanan prosedür adım numaraları
}


def _gunluge_yaz(olay: str):
    durum["gunluk"].append({"zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "olay": olay})


# ---- Araçlar ----
# @tool işareti fonksiyonu Gemini'nin çağırabileceği bir araca çevirir.
# Tırnak içindeki açıklamayı Gemini okur; aracın ne işe yaradığını oradan anlar.

@tool
def sensor_durumu_oku() -> dict:
    """Binadaki sensörlerin şu anki ölçümlerini (sıcaklık, nem, TVOC, eCO2, PM2.5) döndürür."""
    return durum["sensor_satiri"]


@tool
def kamera_sonucu_al() -> dict:
    """Kameranın son görüntü tahminini döndürür: p_alev ve p_duman (0 ile 1 arası olasılık)."""
    return durum["kamera"]


@tool
def prosedur_ara(soru: str) -> dict:
    """Yangın yönetmeliğinde arama yapar. Ne yapılması gerektiğiyle ilgili her soruda kullan.
    Cevabı ve dayandığı madde numaralarını döndürür."""
    return asistan_cevapla(soru, durum["bina_tipi"], durum["bolge"])


@tool
def itfaiyeye_bildir(ozet: str) -> str:
    """İtfaiyeye (112) bildirim yapar. Yalnızca kullanıcı açıkça isterse kullan. ozet: kısa olay özeti."""
    # GERÇEK ARAMA ASLA YOK. Sadece günlüğe yazıyoruz.
    # Model aracı birden fazla kez çağırsa bile bir olay için tek bildirim yazılır.
    if any(k["olay"].startswith("112 ARANDI") for k in durum["gunluk"]):
        return "İtfaiyeye zaten bildirildi, tekrar bildirim yapılmadı."
    _gunluge_yaz(f"112 ARANDI (SİMÜLASYON): {ozet}")
    return "Bildirim günlüğe yazıldı (simülasyon, gerçek arama yapılmadı)."


@tool
def adimi_tamamla(adim_no: int) -> str:
    """Prosedür listesindeki adim_no numaralı adımı tamamlandı olarak işaretler."""
    if adim_no not in durum["tamamlanan_adimlar"]:
        durum["tamamlanan_adimlar"].append(adim_no)
        _gunluge_yaz(f"Prosedür adımı {adim_no} tamamlandı")
    return f"Adım {adim_no} tamamlandı."


ARACLAR = [sensor_durumu_oku, kamera_sonucu_al, prosedur_ara, itfaiyeye_bildir, adimi_tamamla]

SISTEM_PROMPTU = (
    "Sen bir binanın yangın müdahale asistanısın. Türkçe, kısa ve net cevap ver. "
    "Durumu öğrenmek için önce sensor_durumu_oku ve kamera_sonucu_al araçlarını kullan. "
    "Ne yapılacağına dair her bilgiyi prosedur_ara ile yönetmelikten al, kendinden kural uydurma, "
    "kullandığın madde numaralarını yaz. "
    "itfaiyeye_bildir aracını YALNIZCA kullanıcı açıkça isterse kullan; yangın olsa bile kendi kararınla çağırma "
    "(alarm seviyesine sistem karar verir, sen değil)."
)

_ajan = None


def _ajani_hazirla():
    global _ajan
    if _ajan is None:
        model = ChatGoogleGenerativeAI(
            model=MODEL_ADI,
            api_key=os.environ.get("GEMINI_API_KEY"),
            temperature=0,  # tutarlılık için (not: gemini-3.6-flash bunu yok sayıp kendi sabit ayarını kullanıyor)
        )
        _ajan = create_agent(model, tools=ARACLAR, system_prompt=SISTEM_PROMPTU)
    return _ajan


def ajana_sor(soru: str) -> str:
    """Soruyu ajana verir; ajan gerekli araçları çağırıp son cevabı döndürür."""
    sonuc = _ajani_hazirla().invoke(
        {"messages": [{"role": "user", "content": soru}]},
        config={"recursion_limit": 10},  # en fazla 10 adım, sonsuz döngüye girmesin
    )
    return sonuc["messages"][-1].text


if __name__ == "__main__":
    # Sahte bir S3 anı: sıcaklık yüksek, kamera alev görüyor
    durum["sensor_satiri"] = {"Temperature[C]": 48.5, "Humidity[%]": 31.0, "TVOC[ppb]": 1800, "eCO2[ppm]": 1200, "PM2.5": 95.0}
    durum["kamera"] = {"p_alev": 0.91, "p_duman": 0.84}

    for soru in [
        "Şu an yangın var mı? Sensörlere ve kameraya bak.",
        "Yangın doğrulandı. İtfaiyeye bildir ve 1. adımı tamamla.",
        "Tahliyeye nereden başlamalıyız?",
    ]:
        print("=" * 60)
        print("SORU:", soru)
        print(ajana_sor(soru))
    print("=" * 60)
    print("Ajanın günlüğü:", durum["gunluk"])
    print("Tamamlanan adımlar:", durum["tamamlanan_adimlar"])
