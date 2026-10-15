# fusion.py'deki karar kurallarının doğru çalıştığını kontrol eden testler.
# Her test fonksiyonu "test_" ile başlar; pytest bunları otomatik bulur ve çalıştırır.

from src.fusion import fuzyon


# ---- DOGRULANMIS durumları ----

def test_iki_kaynak_yuksek_dogrulanmis():
    # Sensör de kamera da 0.80 üstünde -> yangın doğrulanır
    assert fuzyon(0.90, {"p_alev": 0.85, "p_duman": 0.0}) == "DOGRULANMIS"


def test_sadece_sensor_cok_emin_dogrulanmis():
    # Kamera hiçbir şey görmese de sensör 0.95 üstündeyse tek başına yeter
    assert fuzyon(0.97, {"p_alev": 0.0, "p_duman": 0.0}) == "DOGRULANMIS"


def test_sadece_kamera_cok_emin_dogrulanmis():
    # Sensör sakin ama kamera alevden çok emin -> yine doğrulanır
    assert fuzyon(0.10, {"p_alev": 0.96, "p_duman": 0.0}) == "DOGRULANMIS"


def test_esik_tam_sinirda_dogrulanmis():
    # Tam 0.80 eşiği geçmiş sayılmalı (>= kullandığımız için)
    assert fuzyon(0.80, {"p_alev": 0.0, "p_duman": 0.80}) == "DOGRULANMIS"


# ---- SUPHELI durumları ----

def test_sadece_sensor_orta_supheli():
    # Sensör yüksek ama kamera doğrulamıyor -> operatöre sorulmalı
    assert fuzyon(0.90, {"p_alev": 0.10, "p_duman": 0.10}) == "SUPHELI"


def test_sadece_kamera_duman_orta_supheli():
    # Kamera duman görüyor ama sensör sakin -> şüpheli
    assert fuzyon(0.10, {"p_alev": 0.0, "p_duman": 0.70}) == "SUPHELI"


def test_buhar_senaryosu_dogrulanmisa_atlamamali():
    # S2 (otel banyosu, buhar): sensör 0.79, kamera düşük.
    # Yanlış alarmda sistem asla tek başına DOGRULANMIS dememeli (KK-02).
    assert fuzyon(0.79, {"p_alev": 0.0, "p_duman": 0.14}) == "SUPHELI"


# ---- NORMAL durumu ----

def test_iki_kaynak_dusuk_normal():
    # Hiçbir belirti yok -> normal
    assert fuzyon(0.10, {"p_alev": 0.0, "p_duman": 0.0}) == "NORMAL"