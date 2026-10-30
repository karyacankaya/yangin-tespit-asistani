from ultralytics import YOLO
import numpy as np
from PIL import Image
import io

# Modeli yükle (bir kere yükle, her seferinde tekrar yükleme)
MODEL = YOLO("models/fire_smoke.pt")

def vision_tahmin(goruntu_bytes: bytes) -> dict:
    """
    Görüntüden yangın/duman tespiti yapar.
    
    Args:
        goruntu_bytes: Görüntü dosyasının byte hali (JPEG/PNG)
    
    Returns:
        dict: {
            'yangin_var': bool,
            'duman_var': bool,
            'guven': float,  # En yüksek güven skoru
            'kutular': list  # Tespit edilen kutular
        }
    """
    # Byte'ı görüntüye çevir
    image = Image.open(io.BytesIO(goruntu_bytes))
    
    # Tahmin yap
    results = MODEL.predict(image, conf=0.5, verbose=False)
    
    # Sonuçları işle
    yangin_var = False
    duman_var = False
    max_guven = 0.0
    kutular = []
    
    for r in results:
        for box in r.boxes:
            sinif = MODEL.names[int(box.cls)]
            guven = float(box.conf)
            
            if sinif == 'fire':
                yangin_var = True
            elif sinif == 'smoke':
                duman_var = True
            
            if guven > max_guven:
                max_guven = guven
            
            kutular.append({
                'sinif': sinif,
                'guven': round(guven, 2),
                'koordinatlar': box.xyxy[0].tolist()  # [x1, y1, x2, y2]
            })
    
    return {
        'yangin_var': yangin_var,
        'duman_var': duman_var,
        'guven': round(max_guven, 2),
        'kutular': kutular
    }

# Test bloğu
if __name__ == "__main__":
    # Test için bir görüntü oku
    with open("test.jpg", "rb") as f:
        sonuc = vision_tahmin(f.read())
        print(sonuc)