"""Görüntü modeli (YOLOv8n, D-Fire ile eğitildi): bir kameradan gelen karede alev ve duman arar.

Kullanım (başka bir dosyadan):
    from src.vision import vision_tahmin
    sonuc = vision_tahmin(open("kare.jpg", "rb").read())
    print(sonuc["p_alev"], sonuc["p_duman"])

Deneme (repo klasöründeyken):  python3 src/vision.py scenarios/kareler/s3_kare_02.jpg

Model dosyası (fire_smoke.pt) GitHub'da yoktur; Drive'daki Modeller klasöründen indirilip
models/ klasörüne konmalıdır.
"""
import io
import sys
from pathlib import Path

from PIL import Image

# Yol bu dosyanın yerine göre bulunur; kod hangi klasörden çalıştırılırsa çalıştırılsın model bulunur.
MODEL_YOLU = Path(__file__).resolve().parent.parent / "models" / "fire_smoke.pt"

# ÖNEMLİ — sınıf numaraları: D-Fire etiketlerinde 0 = DUMAN, 1 = ALEV.
# Eğitimde kullanılan dfire.yaml dosyasında adlar ters yazıldığı için (names: ['fire', 'smoke'])
# model dosyasının içindeki MODEL.names yanlıştır: 0'a "fire", 1'e "smoke" der.
# Bu yüzden adlara değil, sınıf NUMARASINA bakıyoruz. (Doğrulama: notebooks/04_yolo_egitim.ipynb)
SINIF_ANAHTARI = {0: "p_duman", 1: "p_alev"}

# Düşük güvenli tespitleri de alıyoruz; asıl kararı füzyon (src/fusion.py) verir.
# 0.5 kullanılsaydı 0.5'in altındaki her şey 0 sayılırdı ve ŞÜPHELİ seviyesi için bilgi kaybolurdu.
GUVEN_ESIGI = 0.25

_model = None  # model ilk çağrıda bir kez yüklenir, sonra saklanır


def _modeli_yukle():
    global _model
    if _model is None:
        if not MODEL_YOLU.exists():
            raise FileNotFoundError(
                f"Görüntü modeli bulunamadı: {MODEL_YOLU}\n"
                "Drive > Modeller klasöründeki fire_smoke.pt dosyasını models/ klasörüne koyun."
            )
        from ultralytics import YOLO  # ağır kütüphane; yalnızca gerektiğinde yüklenir
        _model = YOLO(str(MODEL_YOLU))
    return _model


def vision_tahmin(goruntu_bytes: bytes) -> dict:
    """Bir kameradan gelen kareden alev ve duman olasılıklarını döndürür.

    Dönen sözlük (src/fusion.py'nin beklediği biçim):
        {
            "p_alev":  0-1 arası en yüksek alev güveni (alev yoksa 0.0),
            "p_duman": 0-1 arası en yüksek duman güveni (duman yoksa 0.0),
            "kutular": [{"sinif": "alev"/"duman", "guven": 0.83, "koordinatlar": [x1, y1, x2, y2]}, ...]
        }
    """
    model = _modeli_yukle()

    # PNG'ler saydamlık kanalı (RGBA) taşıyabilir; model 3 kanal (RGB) bekler
    goruntu = Image.open(io.BytesIO(goruntu_bytes)).convert("RGB")
    sonuc = model.predict(goruntu, conf=GUVEN_ESIGI, verbose=False)[0]

    olasiliklar = {"p_alev": 0.0, "p_duman": 0.0}
    kutular = []
    for kutu in sonuc.boxes:
        anahtar = SINIF_ANAHTARI[int(kutu.cls)]
        guven = float(kutu.conf)
        olasiliklar[anahtar] = max(olasiliklar[anahtar], guven)
        kutular.append({
            "sinif": "alev" if anahtar == "p_alev" else "duman",
            "guven": round(guven, 3),
            "koordinatlar": [round(v, 1) for v in kutu.xyxy[0].tolist()],
        })

    return {
        "p_alev": round(olasiliklar["p_alev"], 3),
        "p_duman": round(olasiliklar["p_duman"], 3),
        "kutular": kutular,
    }


if __name__ == "__main__":
    dosya = sys.argv[1] if len(sys.argv) > 1 else "scenarios/kareler/s3_kare_02.jpg"
    with open(dosya, "rb") as f:
        print(dosya, "->", vision_tahmin(f.read()))
