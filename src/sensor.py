from pathlib import Path

import joblib
import pandas as pd

# Model dosyası Drive'dan (YanginProjesi/modeller) indirilip models/ klasörüne konmalı; GitHub'da yok.
# Yol bu dosyanın yerine göre bulunur, böylece kod hangi klasörden çalıştırılırsa çalıştırılsın model bulunur.
MODEL_YOLU = Path(__file__).resolve().parent.parent / "models" / "sensor_model.joblib"
MODEL = joblib.load(MODEL_YOLU)

# Eğitimdeki sütun sırası (X_egitim.columns) — sıra değişirse model yanlış tahmin yapar
SUTUNLAR = ["Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
            "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5",
            "NC0.5", "NC1.0", "NC2.5"]

# Doğrulama setinde seçilen karar eşiği (recall >= 0.99 kalan en yüksek eşik)
ESIK = 0.8


def sensor_tahmin(okuma: dict) -> float:
    """Tek bir sensör okumasından yangın olasılığını (0-1 arası) döndürür.

    okuma sözlüğünde SUTUNLAR listesindeki 12 sensörün hepsi bulunmalı.
    """
    eksik = [s for s in SUTUNLAR if s not in okuma]
    if eksik:
        raise ValueError(f"Sensör okumasında eksik sütunlar var: {eksik}")
    X = pd.DataFrame([okuma])[SUTUNLAR]
    return float(MODEL.predict_proba(X)[:, 1][0])


if __name__ == "__main__":
    # Test setinden gerçek iki satır
    yangin_var = {"Temperature[C]": 15.69, "Humidity[%]": 54.04, "TVOC[ppb]": 1186.0,
                  "eCO2[ppm]": 400.0, "Raw H2": 12937.0, "Raw Ethanol": 19432.0,
                  "Pressure[hPa]": 938.721, "PM1.0": 1.34, "PM2.5": 1.39,
                  "NC0.5": 9.22, "NC1.0": 1.437, "NC2.5": 0.032}
    yangin_yok = {"Temperature[C]": 45.89, "Humidity[%]": 16.97, "TVOC[ppb]": 273.0,
                  "eCO2[ppm]": 400.0, "Raw H2": 13485.0, "Raw Ethanol": 20890.0,
                  "Pressure[hPa]": 936.817, "PM1.0": 1.65, "PM2.5": 1.71,
                  "NC0.5": 11.36, "NC1.0": 1.771, "NC2.5": 0.04}
    print("Yangın var satırı ->", sensor_tahmin(yangin_var))
    print("Yangın yok satırı ->", sensor_tahmin(yangin_yok))
