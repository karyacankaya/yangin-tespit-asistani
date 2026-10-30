"""Sensör modeli (Random Forest, max_depth=4, 50 ağaç): bir sensör okumasından yangın olasılığı üretir.

Kullanım (başka bir dosyadan):
    from src.sensor import sensor_tahmin, SUTUNLAR
    p = sensor_tahmin(okuma)   # okuma: SUTUNLAR'daki 12 sensörün hepsini içeren sözlük

Deneme (repo klasöründeyken):  python3 src/sensor.py

Model dosyası (sensor_model.joblib) GitHub'da yoktur; Drive'daki Modeller klasöründen indirilip
models/ klasörüne konmalıdır. scikit-learn sürümü requirements.txt'deki ile aynı olmalıdır.
"""
from pathlib import Path

import joblib
import pandas as pd

# Yol bu dosyanın yerine göre bulunur; kod hangi klasörden çalıştırılırsa çalıştırılsın model bulunur.
MODEL_YOLU = Path(__file__).resolve().parent.parent / "models" / "sensor_model.joblib"

# Eğitimdeki sütun sırası (X_egitim.columns). Model bu 12 sütunla eğitildi; sütun eksiltilemez,
# sıra değişirse model yanlış tahmin yapar. Senaryo dosyalarındaki her sensor_satiri bu 12 sütunu içerir.
SUTUNLAR = ["Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
            "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5",
            "NC0.5", "NC1.0", "NC2.5"]

# Doğrulama setinde seçilen karar eşiği (recall >= 0.99 kalan en yüksek eşik).
# Sistemde son kararı bu eşik değil, src/fusion.py'deki füzyon eşikleri verir; burada bilgi amaçlıdır.
ESIK = 0.8

_model = None  # model ilk çağrıda bir kez yüklenir, sonra saklanır


def _modeli_yukle():
    global _model
    if _model is None:
        if not MODEL_YOLU.exists():
            raise FileNotFoundError(
                f"Sensör modeli bulunamadı: {MODEL_YOLU}\n"
                "Drive > Modeller klasöründeki sensor_model.joblib dosyasını models/ klasörüne koyun."
            )
        _model = joblib.load(MODEL_YOLU)
    return _model


def sensor_tahmin(okuma: dict) -> float:
    """Tek bir sensör okumasından yangın olasılığını (0-1 arası) döndürür.

    okuma sözlüğünde SUTUNLAR listesindeki 12 sensörün hepsi bulunmalı.
    """
    eksik = [s for s in SUTUNLAR if s not in okuma]
    if eksik:
        raise ValueError(f"Sensör okumasında eksik sütunlar var: {eksik}")
    X = pd.DataFrame([okuma])[SUTUNLAR]
    return float(_modeli_yukle().predict_proba(X)[:, 1][0])


if __name__ == "__main__":
    # Test setinden gerçek iki satır (etiketleri: 1 ve 0)
    yangin_var = {"Temperature[C]": 15.69, "Humidity[%]": 54.04, "TVOC[ppb]": 1186.0,
                  "eCO2[ppm]": 400.0, "Raw H2": 12937.0, "Raw Ethanol": 19432.0,
                  "Pressure[hPa]": 938.721, "PM1.0": 1.34, "PM2.5": 1.39,
                  "NC0.5": 9.22, "NC1.0": 1.437, "NC2.5": 0.032}
    yangin_yok = {"Temperature[C]": 45.89, "Humidity[%]": 16.97, "TVOC[ppb]": 273.0,
                  "eCO2[ppm]": 400.0, "Raw H2": 13485.0, "Raw Ethanol": 20890.0,
                  "Pressure[hPa]": 936.817, "PM1.0": 1.65, "PM2.5": 1.71,
                  "NC0.5": 11.36, "NC1.0": 1.771, "NC2.5": 0.04}
    print("Yangın var satırı ->", round(sensor_tahmin(yangin_var), 3))   # ~0.986
    print("Yangın yok satırı ->", round(sensor_tahmin(yangin_yok), 3))   # ~0.271
