# Füzyon: sensör ve kamera olasılıklarını birleştirip alarm seviyesine karar verir.

# ---- Eşikler (sonradan doğrulama verisiyle ayarlanacak) ----
IKI_KAYNAK_ESIK = 0.80   # iki kaynak da bunun üstündeyse yangın doğrulanır
TEK_KAYNAK_COK_EMIN = 0.95   # tek kaynak bu kadar eminse tek başına yeter
TEK_KAYNAK_SUPHE = 0.60   # tek kaynak bunun üstündeyse şüpheli sayılır


def fuzyon(p_sensor: float, p_goruntu: dict) -> str:
    """Sensör olasılığı (0-1) ve görüntü sonucunu alır, alarm seviyesini döndürür."""

    # Görüntü modelinden alev ve duman güvenini al; yoksa 0 say
    p_alev = p_goruntu.get("p_alev", 0.0)
    p_duman = p_goruntu.get("p_duman", 0.0)

    # Kamera için tek bir olasılık: alev ya da duman, hangisi daha yüksekse
    p_kamera = max(p_alev, p_duman)

    # Kural 1: iki kaynak da yüksekse -> doğrulanmış yangın
    if p_sensor >= IKI_KAYNAK_ESIK and p_kamera >= IKI_KAYNAK_ESIK:
        return "DOGRULANMIS"

    # Kural 2: tek kaynak çok eminse -> yine doğrulanmış
    if p_sensor >= TEK_KAYNAK_COK_EMIN or p_kamera >= TEK_KAYNAK_COK_EMIN:
        return "DOGRULANMIS"

    # Kural 3: tek kaynak orta seviyede yüksekse -> şüpheli, operatöre sor
    if p_sensor >= TEK_KAYNAK_SUPHE or p_kamera >= TEK_KAYNAK_SUPHE:
        return "SUPHELI"

    # Kural 4: hiçbiri tutmadıysa -> normal
    return "NORMAL"


# Bu blok sadece dosyayı doğrudan çalıştırınca devreye girer (elle deneme için)
if __name__ == "__main__":
    print(fuzyon(0.90, {"p_alev": 0.85, "p_duman": 0.10}))  # beklenen: DOGRULANMIS
    print(fuzyon(0.97, {"p_alev": 0.00, "p_duman": 0.00}))  # beklenen: DOGRULANMIS
    print(fuzyon(0.70, {"p_alev": 0.10, "p_duman": 0.10}))  # beklenen: SUPHELI
    print(fuzyon(0.10, {"p_alev": 0.00, "p_duman": 0.00}))  # beklenen: NORMAL