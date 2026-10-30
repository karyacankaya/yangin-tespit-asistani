# 🔥 Yangın Tespit ve Müdahale Asistanı

**Kalabalık binalarda sensör + kamera verisini birleştirip yangını erken tespit eden ve personele adım adım müdahale rehberliği yapan yapay zekâ asistanı.**

---

## 👥 Ekip

- Büşra Şen
- Halime Karya Çankaya
- Gizem Beklen
- Ecem Topcu

---

## 📁 Klasör Yapısı

```
yangin-tespit-asistani/
├── app/            # Streamlit web arayüzü (main.py)
├── src/            # Çekirdek kod: sensor.py, vision.py, fusion.py, rag.py
├── notebooks/      # 01-02 sensör verisi ve modeli, 03-04 D-Fire ve YOLO (Colab)
├── kb/             # Bilgi tabanı: maddeler.jsonl, prosedur_adimlari.jsonl, sistem_promptu.txt
├── scenarios/      # S1, S2, S3 senaryoları (gerçek veriden) + kareler/ + senaryo_uret.py
├── models/         # Eğitilmiş model dosyaları (GitHub'a yüklenmez, bkz. models/README.md)
├── tests/          # Otomatik testler (pytest)
└── docs/           # Vize belgeleri (Use Case, Kabul Kriterleri, Test Senaryoları) ve diyagramlar
```

> 📦 **Veri setleri ve model dosyaları GitHub'da değildir.** Boyutları nedeniyle ekibin ortak Google Drive klasöründe tutulur:
> [Ortak Drive klasörü](https://drive.google.com/drive/folders/1ROSX4iXgNkw5IpC1Be5XCxi3V6MiOJqO) → `csv dosyası/`, `Modeller/`, `veri seti/DFire/`, `grafikler/`

---

## 🚀 Çalıştırma

```bash
pip install -r requirements.txt
# Drive > Modeller klasöründeki sensor_model.joblib ve fire_smoke.pt dosyalarını models/ içine koyun
streamlit run app/main.py
```

Model dosyaları yoksa uygulama yine açılır; senaryo dosyalarındaki kayıtlı model çıktılarıyla çalışır.

## 🧪 Testler

```bash
python -m pytest
```

Füzyon kuralları, senaryoların beklenen seviyeleri (S1 hiç alarm yok, S2 ŞÜPHELİ'de kalır, S3 DOĞRULANMIŞ olur) ve — model dosyaları varsa — sensör ve görüntü modelleri test edilir.

## 🤖 Modeller (özet)

| Model | Veri | Sonuç |
|---|---|---|
| Sensör: Random Forest (50 ağaç, derinlik 4) | Smoke Detection (62.630 satır, 12 kanal) | Test: recall 0,989, ROC-AUC 0,991, eşik 0,8 |
| Görüntü: YOLOv8n (50 epoch, 416 px) | D-Fire (sınıf 0 = duman, 1 = alev) | Val: mAP@0.5 0,740 (duman 0,816, alev 0,665); test sonuçları `notebooks/04_yolo_egitim.ipynb` |

---

*Bu proje, **Veri Madenciliği ve İş Zekâsı** dersi kapsamında Güz 2026 döneminde geliştirilmektedir.*
