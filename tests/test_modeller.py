# Gerçek model dosyalarıyla çalışan testler. Model dosyaları models/ klasöründe yoksa
# (ör. GitHub'dan yeni indirilmiş bir bilgisayarda) bu testler atlanır (SKIPPED), hata vermez.
import importlib.util
import json
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
SENSOR_VAR = (KOK / "models" / "sensor_model.joblib").exists()
GORUNTU_VAR = (KOK / "models" / "fire_smoke.pt").exists() and importlib.util.find_spec("ultralytics") is not None


@pytest.mark.skipif(not SENSOR_VAR, reason="models/sensor_model.joblib yok")
def test_sensor_olasilik_araliginda_ve_sirasi_dogru():
    from src.sensor import sensor_tahmin
    s3 = json.loads((KOK / "scenarios" / "s3_gercek_yangin.json").read_text(encoding="utf-8"))
    p_once = sensor_tahmin(s3[0]["sensor_satiri"])    # gerçek etiket 0
    p_sonra = sensor_tahmin(s3[-1]["sensor_satiri"])  # gerçek etiket 1
    assert 0.0 <= p_once <= 1.0 and 0.0 <= p_sonra <= 1.0
    assert p_sonra > p_once
    assert abs(p_sonra - s3[-1]["kayitli_p_sensor"]) < 0.01   # kayıtlı değerle aynı


@pytest.mark.skipif(not SENSOR_VAR, reason="models/sensor_model.joblib yok")
def test_sensor_eksik_sutunda_hata_verir():
    from src.sensor import sensor_tahmin
    with pytest.raises(ValueError):
        sensor_tahmin({"Temperature[C]": 20.0})


@pytest.mark.skipif(not GORUNTU_VAR, reason="models/fire_smoke.pt ya da ultralytics yok")
def test_vision_fusion_bicimini_dondurur():
    from src.fusion import fuzyon
    from src.vision import vision_tahmin
    kare = (KOK / "scenarios" / "kareler" / "WEB11799.jpg").read_bytes()
    sonuc = vision_tahmin(kare)
    assert {"p_alev", "p_duman", "kutular"} <= set(sonuc)
    assert 0.0 <= sonuc["p_alev"] <= 1.0 and 0.0 <= sonuc["p_duman"] <= 1.0
    assert fuzyon(0.5, sonuc) in {"NORMAL", "SUPHELI", "DOGRULANMIS"}


@pytest.mark.skipif(not GORUNTU_VAR, reason="models/fire_smoke.pt ya da ultralytics yok")
def test_vision_sinif_eslemesi_dogru():
    # Duman bulutunun kaplandığı görüntüde en güçlü tespit DUMAN olmalı (sınıf 0 = duman).
    # Bu test, sınıf adlarının ters çevrilmesi hatasının geri gelmesini engeller.
    from src.vision import vision_tahmin
    duman = vision_tahmin((KOK / "scenarios" / "kareler" / "WEB11798.jpg").read_bytes())
    assert duman["p_duman"] > 0.5 and duman["p_alev"] < 0.25
    olaysiz = vision_tahmin((KOK / "scenarios" / "kareler" / "AoF06858.jpg").read_bytes())
    assert olaysiz["p_alev"] == 0.0 and olaysiz["p_duman"] == 0.0


@pytest.mark.skipif(not GORUNTU_VAR, reason="models/fire_smoke.pt ya da ultralytics yok")
def test_vision_png_seffaflikla_calisir():
    import io

    from PIL import Image

    from src.vision import vision_tahmin
    tampon = io.BytesIO()
    Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(tampon, format="PNG")
    assert vision_tahmin(tampon.getvalue())["p_alev"] == 0.0
