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

# ---- Gerçek modeller: model dosyaları models/ klasöründeyse kullanılır ----
# Dosyalar yoksa (ör. modelleri indirmemiş bir bilgisayarda) senaryo dosyasındaki
# "kayitli_*" değerleri kullanılır. Bu değerler aynı modellerin aynı satır/kare için
# önceden kaydedilmiş çıktısıdır (scenarios/senaryo_uret.py).
import importlib.util

try:
    from src.sensor import MODEL_YOLU as SENSOR_MODEL_YOLU, sensor_tahmin
    from src.vision import MODEL_YOLU as GORUNTU_MODEL_YOLU, vision_tahmin
    GERCEK_MODEL = (
        SENSOR_MODEL_YOLU.exists()
        and GORUNTU_MODEL_YOLU.exists()
        and importlib.util.find_spec("ultralytics") is not None   # görüntü modeli için gerekli
    )
except ImportError:          # ör. scikit-learn / joblib kurulu değilse
    GERCEK_MODEL = False

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

# Asistana gönderilecek bina tipi (bilgi tabanındaki bina_tipleri ile aynı yazılmalı)
BINA_TIPLERI = {"S1 Normal": "avm", "S2 Yanlış Alarm": "otel", "S3 Gerçek Yangın": "kampus"}

# TS-10: kamera olasılığı bunu ilk kez geçince günlüğe "duman/alev gördü" yazılır
KAMERA_GORDU_ESIK = 0.25

ASISTAN_ULASILAMIYOR = "Asistana ulaşılamıyor, 112'yi arayın."   # FOG-05


# ---- Model çağrıları ----
@st.cache_data(show_spinner=False)
def _goruntu_sonucu(kare: str) -> dict:
    # Aynı kare için modeli her saniye yeniden çalıştırmamak için sonuç saklanır
    return vision_tahmin((KOK / "scenarios" / "kareler" / kare).read_bytes())


def sensor_olasiligi(adim: dict) -> float:
    if GERCEK_MODEL:
        return sensor_tahmin(adim["sensor_satiri"])
    return adim.get("kayitli_p_sensor", 0.0)


def goruntu_olasiligi(adim: dict) -> dict:
    if GERCEK_MODEL:
        return _goruntu_sonucu(adim["kare"])
    return adim.get("kayitli_goruntu", {"p_alev": 0.0, "p_duman": 0.0})


# ---- Dosya ve görünüm yardımcıları ----
def senaryo_yukle(dosya_adi: str) -> list:
    yol = KOK / "scenarios" / dosya_adi
    if not yol.exists():                       # FG-05: dosya yoksa hata mesajı
        st.error(f"Senaryo dosyası bulunamadı: scenarios/{dosya_adi}")
        st.stop()
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def prosedur_yukle(seviye: str) -> list:
    # kb/prosedur_adimlari.jsonl: her satır bir adım; istenen seviyedekileri sırasıyla döndürür
    yol = KOK / "kb" / "prosedur_adimlari.jsonl"
    with open(yol, encoding="utf-8") as f:
        satirlar = [json.loads(satir) for satir in f if satir.strip()]
    return sorted((s for s in satirlar if s["seviye"] == seviye), key=lambda s: s["adim"])


def madde_yazisi(maddeler: list) -> str:
    # [30, 82] -> "(Madde 30, 82)"; madde yoksa boş
    if not maddeler:
        return ""
    return "(Madde " + ", ".join(str(m) for m in maddeler) + ")"


def virgullu(sayi: float) -> str:
    # 0.85 -> "0,85" (Türkçe ondalık)
    return f"{sayi:.2f}".replace(".", ",")


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
    "prosedur_adim": 0,         # Müdahale Asistanı'nda tamamlanan adım sayısı
    "duman_goruldu": False,     # "Kamera duman gördü" günlüğe yazıldı mı?
    "alev_goruldu": False,      # "Kamera alev gördü" günlüğe yazıldı mı?
    "asistan_cevabi": None,     # soru kutusundan gelen son cevap
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
    gunluge_yaz(f"Seviye değişti: {eski} → {yeni}")
    if yeni == "DOGRULANMIS" and not ss.dogrulandi:
        ss.dogrulandi = True
        gunluge_yaz("112 ARANDI (SİMÜLASYON)")   # KK-11: gerçek arama ASLA yapılmaz


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
    p_sensor = sensor_olasiligi(adim)
    p_goruntu = goruntu_olasiligi(adim)
    ham = fuzyon(p_sensor, p_goruntu)

    # TS-10: kameranın dumanı ve alevi ilk gördüğü anı günlüğe bir kez yaz
    if not ss.duman_goruldu and p_goruntu["p_duman"] >= KAMERA_GORDU_ESIK:
        ss.duman_goruldu = True
        gunluge_yaz(f"Kamera duman gördü (p_duman = {virgullu(p_goruntu['p_duman'])})")
    if not ss.alev_goruldu and p_goruntu["p_alev"] >= KAMERA_GORDU_ESIK:
        ss.alev_goruldu = True
        gunluge_yaz(f"Kamera alev gördü (p_alev = {virgullu(p_goruntu['p_alev'])})")

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

    kaynak = "gerçek modeller" if GERCEK_MODEL else "kayıtlı model çıktısı"
    st.write(
        f"**Model olasılıkları ({kaynak}):** sensör = {p_sensor:.2f} · "
        f"alev = {p_goruntu['p_alev']:.2f} · duman = {p_goruntu['p_duman']:.2f}"
    )
    kare_yolu = KOK / "scenarios" / "kareler" / adim["kare"]
    if kare_yolu.exists():
        st.image(str(kare_yolu), caption=f"Kamera karesi: {adim['kare']}", width=420)
    else:
        st.caption(f"Kamera karesi: {adim['kare']} (dosya yok)")
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

    # ---- Müdahale Asistanı (yalnızca DOĞRULANMIŞ'ta) ----
    if ss.seviye == "DOGRULANMIS":
        st.divider()
        st.subheader("Müdahale Asistanı")
        prosedur = prosedur_yukle("DOGRULANMIS")

        # Tamamlanan adımlar üstte ✓ ile; sonraki adımlar gizli (KK-09)
        for p in prosedur[:ss.prosedur_adim]:
            st.write(f"✓ {p['adim']}. {p['eylem']} {madde_yazisi(p['ilgili_madde'])}")

        if ss.prosedur_adim < len(prosedur):
            p = prosedur[ss.prosedur_adim]
            st.markdown(f"**{p['adim']}. {p['eylem']}** {madde_yazisi(p['ilgili_madde'])}")
            st.caption(p["aciklama"])
            if st.button("Tamamlandı", type="primary", key=f"tamam_{ss.prosedur_adim}"):
                ss.prosedur_adim += 1
                gunluge_yaz(f"Adım {p['adim']} tamamlandı: {p['eylem']}")
                if ss.prosedur_adim == len(prosedur):
                    gunluge_yaz("Prosedür tamamlandı")
                st.rerun()
        else:
            st.success("Prosedür tamamlandı")

        # ---- Serbest soru kutusu (FG-09, FG-10, KK-03) ----
        # form: yazarken sayfa yenilenmesin, yalnızca "Sor"a basınca gönderilsin
        with st.form("soru_formu", clear_on_submit=False):
            soru = st.text_input("Soru sor:")
            sor = st.form_submit_button("Sor")
        if sor and soru.strip():
            gunluge_yaz(f"Asistana soruldu: {soru.strip()}")
            with st.spinner("Asistan cevaplıyor..."):
                try:
                    from src.rag import asistan_cevapla   # paket/Chroma yoksa burada hata verir
                    ss.asistan_cevabi = asistan_cevapla(soru.strip(), BINA_TIPLERI[ss.senaryo], ss.senaryo)
                except Exception as hata:
                    # Uygulama çökmesin; ama sebebi görünsün ki düzeltebilelim
                    ss.asistan_cevabi = {"cevap": ASISTAN_ULASILAMIYOR, "kaynaklar": [],
                                         "hata": f"{type(hata).__name__}: {hata}"}
        if ss.asistan_cevabi:
            st.info(ss.asistan_cevabi["cevap"])
            if ss.asistan_cevabi["kaynaklar"]:
                st.caption("Kaynaklar: " + ", ".join(f"Madde {m}" for m in ss.asistan_cevabi["kaynaklar"]))
            if ss.asistan_cevabi.get("hata"):
                st.caption(f"Teknik ayrıntı: {ss.asistan_cevabi['hata']}")

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
    st.caption("Kayıtlı olay yok.")   # FG-13 / UC-07 metni

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