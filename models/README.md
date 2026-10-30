# models/

Eğitilmiş model dosyaları boyutları nedeniyle GitHub'a yüklenmez (`.gitignore`).
Ekibin ortak Drive klasöründeki **Modeller** klasöründen indirip buraya koyun:

| Dosya | Ne işe yarar | Kullanan kod |
|---|---|---|
| `sensor_model.joblib` | Sensör modeli (Random Forest, 12 sensör kanalı) | `src/sensor.py` |
| `fire_smoke.pt` | Görüntü modeli (YOLOv8n, D-Fire; sınıf 0 = duman, 1 = alev) | `src/vision.py` |

Dosyalar yoksa uygulama yine açılır; senaryo dosyalarındaki kayıtlı model çıktılarıyla çalışır.
