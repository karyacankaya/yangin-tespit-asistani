import json   # senaryo dosyalarını (JSON) okumak için
import sys    # Python'un modül arama yoluna proje klasörünü eklemek için
import time   # saniye saniye beklemek için
from pathlib import Path   # dosya yollarını Mac/Windows fark etmeden kurmak için

import streamlit as st

# ---- Proje kök klasörünü bul ve Python'a tanıt ----
# Bu dosya app/main.py; iki üst klasör = yangin-tespit-asistani/
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))   # bu sayede "src" klasöründen içe aktarma yapabiliyoruz

from src.fusion import fuzyon   # senin yazdığın karar fonksiyonu

# ---- Ayarlar ----
# Menüde görünen ad -> scenarios klasöründeki dosya adı
SENARYOLAR = {
    "S1 Normal": "s1_normal.json",
    "S2 Yanlış Alarm": "s2_yanlis_alarm.json",
    "S3 Gerçek Yangın": "s3_gercek_yangin.json",
}

# Ekranda gösterilecek sensörler: veri setindeki sütun adı -> (ekrandaki ad, birim)
GOSTERILECEK_SENSORLER = {
    "Temperature[C]": ("Sıcaklık", "°C"),
    "Humidity[%]": ("Nem", "%"),
    "TVOC[ppb]": ("TVOC", "ppb"),
    "eCO2[ppm]": ("eCO2", "ppm"),
    "PM2.5": ("PM2.5", ""),
}


# ---- Sahte model fonksiyonları (Büşra'nın modelleri gelene kadar) ----
def sahte_sensor(adim: dict) -> float:
    # JSON'daki sahte değeri okur; yoksa 0.1 döner
    return adim.get("sahte_p_sensor", 0.1)


def sahte_goruntu(adim: dict) -> dict:
    # JSON'daki sahte kamera sonucunu okur; yoksa "hiçbir şey yok" döner
    return adim.get("sahte_goruntu", {"p_alev": 0.0, "p_duman": 0.0})


# ---- Yardımcı fonksiyonlar ----
def senaryo_yukle(dosya_adi: str) -> list:
    # scenarios/ klasöründeki JSON dosyasını açıp listeye çevirir
    yol = KOK / "scenarios" / dosya_adi
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def seviye_kutusu(seviye: str):
    # Füzyon sonucuna göre renkli kutu çizer
    if seviye == "NORMAL":
        st.success("NORMAL — Durum sakin")
    elif seviye == "SUPHELI":
        st.warning("ŞÜPHELİ — Operatör onayı bekleniyor")
    else:
        st.error("DOĞRULANMIŞ YANGIN — Prosedürü başlat")


# ---- Sayfa ----
st.title("Yangın Tespit ve Müdahale Asistanı")

secim = st.sidebar.selectbox("Senaryo", list(SENARYOLAR.keys()))   # soldaki senaryo menüsü
adimlar = senaryo_yukle(SENARYOLAR[secim])                          # seçilen dosyayı oku
st.sidebar.caption(f"{len(adimlar)} saniyelik senaryo")

if st.button("Senaryoyu Başlat"):
    alan = st.empty()      # her saniye üzerine yazılacak boş bir alan
    onceki = None          # bir önceki saniyenin sensör değerleri (değişimi göstermek için)

    for adim in adimlar:
        sensor = adim["sensor_satiri"]
        p_sensor = sahte_sensor(adim)
        p_goruntu = sahte_goruntu(adim)
        seviye = fuzyon(p_sensor, p_goruntu)

        with alan.container():   # alanın içini bu saniyenin bilgisiyle yeniden çiz
            st.subheader(f"Saniye {adim['saniye']}")

            # Sensör değerlerini yan yana kutucuklar hâlinde göster
            sutunlar = st.columns(len(GOSTERILECEK_SENSORLER))
            for sutun, (anahtar, (ad, birim)) in zip(sutunlar, GOSTERILECEK_SENSORLER.items()):
                deger = sensor.get(anahtar)
                fark = None
                if onceki is not None and deger is not None and anahtar in onceki:
                    fark = round(deger - onceki[anahtar], 2)
                # delta_color="inverse": artış kırmızı, düşüş yeşil (yangında artış kötü haber)
                sutun.metric(ad, f"{deger} {birim}", delta=fark, delta_color="inverse")

            st.write(
                f"**Model olasılıkları (sahte):** sensör = {p_sensor:.2f} · "
                f"alev = {p_goruntu['p_alev']:.2f} · duman = {p_goruntu['p_duman']:.2f}"
            )
            st.caption(f"Kamera karesi: {adim['kare']}")
            seviye_kutusu(seviye)

        onceki = sensor
        time.sleep(1)   # bir saniye bekle, sonra sıradaki satıra geç

    st.info("Senaryo bitti.")