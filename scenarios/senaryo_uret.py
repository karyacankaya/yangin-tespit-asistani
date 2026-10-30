"""S1, S2 ve S3 senaryo dosyalarını GERÇEK veriden üretir.

- Sensör satırları: Smoke Detection verisinden (smoke_detection_iot.csv), 12 sensör kanalının hepsiyle.
- Kamera kareleri: D-Fire test setinden seçilen görüntüler (scenarios/kareler/).
- Her adıma iki modelin o satır/kare için verdiği çıktı da yazılır ("kayitli_p_sensor", "kayitli_goruntu").
  Model dosyaları olmayan bir bilgisayarda uygulama bu kayıtlı değerlerle çalışır.

Çalıştırma (repo klasöründeyken; CSV proje kökünde, modeller models/ içinde olmalı):
    python3 scenarios/senaryo_uret.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from src.fusion import fuzyon  # noqa: E402
from src.sensor import SUTUNLAR, sensor_tahmin  # noqa: E402
from src.vision import vision_tahmin  # noqa: E402

CSV_YOLU = KOK / "smoke_detection_iot.csv"
KARE_KLASORU = KOK / "scenarios" / "kareler"

# Her senaryo: CSV satır numaraları (ilk sütundaki "Unnamed: 0" = dosyadaki sıra) ve her adımın karesi.
# Satırlar art arda değil, belli aralıklarla seçildi; böylece 1 saniyelik adımlarda gerçek bir değişim görülür.
SENARYOLAR = {
    # S1 — AVM yemek katı, normal gün. 1. kayıt oturumunun başı: etiket 0, sensör sakin.
    # Kareler: aynı kameranın (Camera0001) açık havada, olay içermeyen görüntüleri.
    "s1_normal.json": {
        "satirlar": [0, 10, 20, 30, 40, 50],
        "kareler": ["AoF06858.jpg", "AoF06875.jpg", "AoF06892.jpg",
                    "AoF06858.jpg", "AoF06875.jpg", "AoF06892.jpg"],
    },
    # S2 — Otel banyosu, buhar (yanlış alarm). 4. kayıt oturumu: etiket hep 0 (yangın yok),
    # nem %39'dan %75'e, TVOC 0'dan 2500'e çıkıyor; sensör modeli 0.60'ı geçiyor ama 0.95'e hiç ulaşmıyor.
    # Kareler: aynı kamera, önce açık hava, sonra sis/yağmur (yangına benzeyen ama yangın olmayan sahne).
    "s2_yanlis_alarm.json": {
        "satirlar": [54974, 55004, 55034, 55064, 55094, 55124, 55154, 55184],
        "kareler": ["AoF06858.jpg", "AoF06875.jpg", "AoF06856.jpg", "AoF06884.jpg",
                    "AoF06856.jpg", "AoF06884.jpg", "AoF06856.jpg", "AoF06884.jpg"],
    },
    # S3 — Kampüs kütüphanesi, gerçek yangın. 1. kayıt oturumunda etiketin 0'dan 1'e geçtiği an (satır 3178).
    # Kareler: önce olay yok, sonra yalnız duman, sonra duman + alev (erken tespit: duman alevden önce görülür).
    "s3_gercek_yangin.json": {
        "satirlar": [3148, 3163, 3178, 3193, 3208, 3223],
        "kareler": ["AoF06892.jpg", "WEB11798.jpg", "WEB11798.jpg",
                    "WEB11799.jpg", "WEB11802.jpg", "WEB11802.jpg"],
    },
}


def main():
    df = pd.read_csv(CSV_YOLU)
    for dosya, tanim in SENARYOLAR.items():
        adimlar = []
        for saniye, (satir_no, kare) in enumerate(zip(tanim["satirlar"], tanim["kareler"])):
            satir = df.iloc[satir_no]
            sensor_satiri = {s: round(float(satir[s]), 3) for s in SUTUNLAR}
            p_sensor = round(sensor_tahmin(sensor_satiri), 3)
            goruntu = vision_tahmin((KARE_KLASORU / kare).read_bytes())
            adimlar.append({
                "saniye": saniye,
                "sensor_satiri": sensor_satiri,
                "kare": kare,
                "kaynak": {"csv_satiri": int(satir_no), "gercek_etiket": int(satir["Fire Alarm"])},
                "kayitli_p_sensor": p_sensor,
                "kayitli_goruntu": {"p_alev": goruntu["p_alev"], "p_duman": goruntu["p_duman"]},
            })
            seviye = fuzyon(p_sensor, goruntu)
            print(f"{dosya:24s} sn {saniye}: p_sensor={p_sensor:.2f} "
                  f"alev={goruntu['p_alev']:.2f} duman={goruntu['p_duman']:.2f} -> {seviye}")
        with open(KOK / "scenarios" / dosya, "w", encoding="utf-8") as f:
            json.dump(adimlar, f, ensure_ascii=False, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
