# Senaryo dosyalarının yapısını ve füzyonla birlikte beklenen seviyeleri kontrol eder.
# Model dosyası GEREKMEZ: senaryolardaki kayıtlı model çıktıları (kayitli_*) kullanılır.
import json
from pathlib import Path

import pytest

from src.fusion import fuzyon
from src.sensor import SUTUNLAR

KOK = Path(__file__).resolve().parent.parent
SENARYOLAR = ["s1_normal.json", "s2_yanlis_alarm.json", "s3_gercek_yangin.json"]


def seviyeler(dosya):
    adimlar = json.loads((KOK / "scenarios" / dosya).read_text(encoding="utf-8"))
    return [fuzyon(a["kayitli_p_sensor"], a["kayitli_goruntu"]) for a in adimlar]


@pytest.mark.parametrize("dosya", SENARYOLAR)
def test_her_adimda_12_sensor_ve_kare_var(dosya):
    # FG-01: sensör modeli 12 kanalın hepsini ister; her adımın karesi klasörde olmalı
    adimlar = json.loads((KOK / "scenarios" / dosya).read_text(encoding="utf-8"))
    for adim in adimlar:
        assert set(SUTUNLAR) <= set(adim["sensor_satiri"]), f"saniye {adim['saniye']}"
        assert (KOK / "scenarios" / "kareler" / adim["kare"]).exists(), adim["kare"]


def test_s1_hic_alarm_yok():
    # KK-06: normal günde hiçbir saniyede alarm üretilmez
    assert set(seviyeler("s1_normal.json")) == {"NORMAL"}


def test_s2_supheli_olur_ama_tek_basina_dogrulanmis_olmaz():
    # KK-02: yanlış alarmda sistem ŞÜPHELİ'de bekler, kendiliğinden DOĞRULANMIŞ demez
    s = seviyeler("s2_yanlis_alarm.json")
    assert "SUPHELI" in s
    assert "DOGRULANMIS" not in s


def test_s3_once_supheli_sonra_dogrulanmis():
    # KK-07: gerçek yangında seviye DOĞRULANMIŞ'a çıkar; duman alevden önce görülür (TS-10)
    s = seviyeler("s3_gercek_yangin.json")
    assert s[0] == "NORMAL"
    assert s.index("SUPHELI") < s.index("DOGRULANMIS")
    adimlar = json.loads((KOK / "scenarios" / "s3_gercek_yangin.json").read_text(encoding="utf-8"))
    ilk_duman = next(i for i, a in enumerate(adimlar) if a["kayitli_goruntu"]["p_duman"] >= 0.25)
    ilk_alev = next(i for i, a in enumerate(adimlar) if a["kayitli_goruntu"]["p_alev"] >= 0.25)
    assert ilk_duman < ilk_alev
