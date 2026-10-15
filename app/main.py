import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ---- Proje kök klasörünü Python'a tanıt (src'den içe aktarma için) ----
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from src.fusion import fuzyon

# ---- Ayarlar ----
SENARYOLAR = {
    "S1 Normal": "s1_normal.json",
    "S2 Yanlış Alarm": "s2_yanlis_alarm.json",
    "S3 Gerçek Yangın": "s3_gercek_yangin.json",
}

GOSTERILECEK_SENSORLER = {
    "Temperature[C]": ("Sıcaklık", "°C"),
    "Humidity[%]": ("Nem", "%"),
    "TVOC[ppb]": ("TVOC", "ppb"),
    "eCO2[ppm]": ("eCO2", "ppm"),
    "PM2.5": ("PM2.5", ""),
}

# FG-06: operatör bu kadar saniye içinde yanıt vermezse alarm güvenli tarafa (DOGRULANMIS) yükselir
GERI_SAYIM_SN = 60


# ---- Sahte model fonksiyonları (Büşra'nın modelleri gelene kadar) ----
def sahte_sensor(adim: dict) -> float:
    return adim.get("sahte_p_sensor", 0.1)


def sahte_goruntu(adim: dict) -> dict:
    return adim.get("sahte_goruntu", {"p_alev": 0.0, "p_duman": 0.0})


# ---- Dosya ve görünüm yardımcıları ----
def senaryo_yukle(dosya_adi: str) -> list:
    with open(KOK / "scenarios" / dosya_adi, encoding="utf-8") as f:
        return json.load(f)


def seviye_kutusu(seviye: str):
    if seviye == "NORMAL":
        st.success("NORMAL — Durum sakin")
    elif seviye == "SUPHELI":
        st.warning("ŞÜPHELİ — Operatör onayı bekleniyor")
    else:
        st.error("DOĞRULANMIŞ YANGIN — Prosedürü başlat")


# ---- Hafıza (session_state): sayfa her yeniden çalıştığında korunan bilgiler ----
ss = st.session_state

VARSAYILANLAR = {
    "gunluk": [],               # olay günlüğü satırları
    "calisiyor": False,         # senaryo şu an oynuyor mu?
    "senaryo": None,            # hangi senaryo oynuyor
    "adim": 0,                  # senaryonun kaçıncı saniyesindeyiz
    "seviye": "NORMAL",         # ekranda gösterilen alarm seviyesi
    "karar": None,              # operatör kararı: None / "ONAY" / "RED"
    "dogrulandi": False,        # bir kez DOGRULANMIS olduysa geri dönmez
    "supheli_baslangic": None,  # ŞÜPHELİ'ye geçilen an (geri sayım için)
}
for anahtar, deger in VARSAYILANLAR.items():
    if anahtar not in ss:
        ss[anahtar] = deger


def gunluge_yaz(olay: str):
    ss.gunluk.append({
        "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "senaryo": ss.senaryo or "-",
        "seviye": ss.seviye,
        "olay": olay,
    })


def seviye_degistir(yeni: str):
    # Seviye gerçekten değiştiyse günlüğe yazar ve gerekli işaretleri koyar
    if yeni == ss.seviye:
        return
    eski = ss.seviye
    ss.seviye = yeni
    if yeni == "SUPHELI" and ss.supheli_baslangic is None:
        ss.supheli_baslangic = time.time()   # geri sayım bu andan başlar
    if yeni == "DOGRULANMIS":
        ss.dogrulandi = True
    gunluge_yaz(f"Seviye değişti: {eski} → {yeni}")


def senaryoyu_baslat(ad: str):
    for anahtar, deger in VARSAYILANLAR.items():
        if anahtar != "gunluk":       # günlük senaryolar arasında birikir, sıfırlanmaz
            ss[anahtar] = deger
    ss.calisiyor = True
    ss.senaryo = ad
    gunluge_yaz("Senaryo başlatıldı")


def seviye_belirle(ham: str) -> str:
    # Füzyonun ham kararını operatör kararıyla birleştirir
    if ss.dogrulandi or ham == "DOGRULANMIS":
        return "DOGRULANMIS"               # gerçek yangın her şeyi ezer
    if ss.karar == "RED":
        return "NORMAL"                    # operatör reddettiyse şüpheyi tekrar sorma
    if ham == "SUPHELI" or ss.supheli_baslangic is not None:
        return "SUPHELI"                   # şüphe, operatör karar verene kadar sürer
    return "NORMAL"


# ================= SAYFA =================
st.title("Yangın Tespit ve Müdahale Asistanı")

secim = st.sidebar.selectbox("Senaryo", list(SENARYOLAR.keys()))
if st.sidebar.button("Senaryoyu Başlat", type="primary"):
    senaryoyu_baslat(secim)

adimlar = None
if ss.senaryo is None:
    st.info("Soldan bir senaryo seçip **Senaryoyu Başlat**'a basın.")
else:
    adimlar = senaryo_yukle(SENARYOLAR[ss.senaryo])
    adim = adimlar[ss.adim]
    sensor = adim["sensor_satiri"]
    p_sensor = sahte_sensor(adim)
    p_goruntu = sahte_goruntu(adim)
    ham = fuzyon(p_sensor, p_goruntu)

    yeni = seviye_belirle(ham)

    # Zaman aşımı: operatör GERI_SAYIM_SN içinde yanıt vermediyse güvenli tarafa düş
    if yeni == "SUPHELI" and ss.supheli_baslangic is not None:
        if time.time() - ss.supheli_baslangic >= GERI_SAYIM_SN:
            gunluge_yaz(f"Operatör {GERI_SAYIM_SN} sn yanıt vermedi — alarm otomatik yükseltildi")
            yeni = "DOGRULANMIS"

    seviye_degistir(yeni)

    # ---- Sensör paneli ----
    durum = "oynatılıyor" if ss.calisiyor else "bitti"
    st.subheader(f"{ss.senaryo} — Saniye {adim['saniye']} ({durum})")

    onceki = adimlar[ss.adim - 1]["sensor_satiri"] if ss.adim > 0 else None
    sutunlar = st.columns(len(GOSTERILECEK_SENSORLER))
    for sutun, (anahtar, (ad, birim)) in zip(sutunlar, GOSTERILECEK_SENSORLER.items()):
        deger = sensor.get(anahtar)
        fark = None
        if onceki is not None and deger is not None and anahtar in onceki:
            fark = round(deger - onceki[anahtar], 2)
        sutun.metric(ad, f"{deger} {birim}", delta=fark, delta_color="inverse")

    st.write(
        f"**Model olasılıkları (sahte):** sensör = {p_sensor:.2f} · "
        f"alev = {p_goruntu['p_alev']:.2f} · duman = {p_goruntu['p_duman']:.2f}"
    )
    st.caption(f"Kamera karesi: {adim['kare']}")
    seviye_kutusu(ss.seviye)

    # ---- Operatör doğrulama paneli (yalnızca ŞÜPHELİ'de) ----
    if ss.seviye == "SUPHELI":
        gecen = time.time() - ss.supheli_baslangic
        kalan = max(0, GERI_SAYIM_SN - int(gecen))
        st.progress(kalan / GERI_SAYIM_SN, text=f"Operatör yanıtı bekleniyor — kalan süre: {kalan} sn")

        sol, sag = st.columns(2)
        if sol.button("Onayla — gerçek yangın", type="primary", key="onay"):
            ss.karar = "ONAY"
            gunluge_yaz("Operatör onayladı: gerçek yangın")
            seviye_degistir("DOGRULANMIS")
            st.rerun()
        if sag.button("Reddet — yanlış alarm", key="red"):
            ss.karar = "RED"
            ss.supheli_baslangic = None
            gunluge_yaz("Operatör reddetti: yanlış alarm")
            seviye_degistir("NORMAL")
            st.rerun()

# ---- Olay günlüğü ----
st.divider()
st.subheader("Olay günlüğü")
if ss.gunluk:
    df = pd.DataFrame(ss.gunluk)
    st.dataframe(df, hide_index=True)
    st.download_button(
        "Günlüğü CSV indir",
        data=df.to_csv(index=False).encode("utf-8-sig"),   # utf-8-sig: Excel'de Türkçe karakterler bozulmaz
        file_name="olay_gunlugu.csv",
        mime="text/csv",
    )
else:
    st.caption("Henüz olay yok.")

# ---- Bir sonraki saniyeye geç ----
# Senaryo oynuyorsa ya da operatör yanıtı bekleniyorsa 1 sn bekleyip sayfayı yeniden çalıştır
if adimlar is not None and (ss.calisiyor or ss.seviye == "SUPHELI"):
    time.sleep(1)
    if ss.calisiyor:
        if ss.adim < len(adimlar) - 1:
            ss.adim += 1
        else:
            ss.calisiyor = False
            gunluge_yaz("Senaryo bitti")
    st.rerun()