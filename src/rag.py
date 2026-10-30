"""RAG zinciri. Soru -> en yakın maddeler (Chroma) -> Gemini -> kaynaklı cevap.

Kullanım (başka bir dosyadan):
    from src.rag import asistan_cevapla
    sonuc = asistan_cevapla("Yangında asansör kullanılır mı?", "otel", "3. kat koridor")
    print(sonuc["cevap"], sonuc["kaynaklar"])

Deneme (repo klasöründeyken):  python3 src/rag.py
Önce bir kez `python3 src/rag_deneme.py` çalışmış olmalı (kb/chroma_db onu oluşturur).
"""
import os
import re
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types
from sentence_transformers import SentenceTransformer

REPO = Path(__file__).resolve().parent.parent
CHROMA_YOLU = REPO / "kb" / "chroma_db"
PROMPT_YOLU = REPO / "kb" / "sistem_promptu.txt"
KAC_MADDE = 5  # Gemini'ye gönderilecek madde sayısı
ASISTAN_ULASILAMIYOR = "Asistana ulaşılamıyor, 112'yi arayın."  # FOG-05 uyarı metni

load_dotenv(REPO / ".env")
MODEL_ADI = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

# Ağır şeyleri (bge-m3, Chroma, Gemini istemcisi) bir kez yükleyip saklıyoruz.
# Böylece asistan_cevapla her çağrıldığında model baştan yüklenmez.
_hazir = {}


def _yukle():
    if not _hazir:
        anahtar = os.environ.get("GEMINI_API_KEY")
        if not anahtar:
            raise RuntimeError(".env dosyasında GEMINI_API_KEY bulunamadı.")
        koleksiyon = chromadb.PersistentClient(path=str(CHROMA_YOLU)).get_or_create_collection(
            "yonetmelik", metadata={"hnsw:space": "cosine"}
        )
        if koleksiyon.count() == 0:
            raise RuntimeError("Chroma boş. Önce `python3 src/rag_deneme.py` çalıştır.")
        _hazir["model"] = SentenceTransformer("BAAI/bge-m3")
        _hazir["koleksiyon"] = koleksiyon
        # 60 saniyede cevap gelmezse hata ver (sonsuza kadar beklemesin)
        _hazir["gemini"] = genai.Client(
            api_key=anahtar,
            http_options=types.HttpOptions(
                timeout=60_000, retry_options=types.HttpRetryOptions(attempts=2)
            ),
        )
        _hazir["sistem_promptu"] = PROMPT_YOLU.read_text(encoding="utf-8")
    return _hazir


def _maddeleri_bul(soru: str, bina_tipi: str) -> list[dict]:
    """Soruya en yakın KAC_MADDE maddeyi getirir; bina_tipi verilmişse ona uyanları seçer."""
    h = _yukle()
    vektor = h["model"].encode([soru], normalize_embeddings=True).tolist()
    # Fazladan çekip bina tipine göre eliyoruz (Chroma'da bina_tipleri "otel, avm, kampus" metni)
    sonuc = h["koleksiyon"].query(query_embeddings=vektor, n_results=15)
    maddeler = []
    for metin, meta in zip(sonuc["documents"][0], sonuc["metadatas"][0]):
        tipler = [t.strip() for t in meta["bina_tipleri"].split(",")]
        if bina_tipi and bina_tipi not in tipler:
            continue
        maddeler.append({"madde": meta["madde"], "metin": metin, "ozet": meta["eylem_adimi"]})
        if len(maddeler) == KAC_MADDE:
            break
    return maddeler


def asistan_cevapla(soru: str, bina_tipi: str, bolge: str) -> dict:
    """Soruyu bilgi tabanına dayanarak cevaplar.

    Dönen sözlük: {"cevap": str, "kaynaklar": [madde numaraları]}
    """
    bina_tipi = (bina_tipi or "").strip().lower()   # "Otel" ile "otel" aynı sayılsın
    try:
        h = _yukle()
        maddeler = _maddeleri_bul(soru, bina_tipi)
    except RuntimeError:
        raise                                    # .env / Chroma kurulum hatası: geliştirici görmeli
    except Exception:
        # FOG-05: model indirilemiyor ya da bağlantı yoksa sistem çökmez, uyarı döner
        return {"cevap": ASISTAN_ULASILAMIYOR, "kaynaklar": []}

    # Her maddenin başına kısa özetini (eylem adımı) koyuyoruz; uzun maddelerde
    # önemli cümle metnin ortasında kaybolmasın diye.
    madde_metni = "\n\n".join(
        f"[Madde {m['madde']}]\nÖzet: {m['ozet']}\nMetin: {m['metin']}" for m in maddeler
    )
    mesaj = (
        f"Bina tipi: {bina_tipi}\n"
        f"Olayın olduğu bölge: {bolge}\n\n"
        f"YÖNETMELİK MADDELERİ:\n{madde_metni}\n\n"
        f"SORU: {soru}"
    )
    try:
        yanit = h["gemini"].models.generate_content(
            model=MODEL_ADI,
            contents=mesaj,
            config=types.GenerateContentConfig(
                system_instruction=h["sistem_promptu"],
                temperature=0,  # her seferinde aynı, tahminsiz cevap
            ),
        )
    except Exception:
        # FOG-05: internet kesintisi, kota aşımı vb. durumda uygulama çökmesin
        return {"cevap": ASISTAN_ULASILAMIYOR, "kaynaklar": []}
    cevap = (yanit.text or "").strip()

    # Cevapta geçen madde numaralarını topla; sadece gerçekten gönderdiklerimizi kabul et
    gonderilenler = {m["madde"] for m in maddeler}
    anilanlar = {int(n) for n in re.findall(r"Madde\s+(\d+)", cevap)}
    return {"cevap": cevap, "kaynaklar": sorted(anilanlar & gonderilenler)}


if __name__ == "__main__":
    test_sorulari = [
        ("Normal", "Kademeli tahliye nedir?"),
        ("Tuzak", "Yangında çocukları asansörle mi indirmeliyim?"),
        ("Bilgi tabanında yok", "Helikopter pisti nerede?"),
    ]
    for tur, soru in test_sorulari:
        sonuc = asistan_cevapla(soru, bina_tipi="otel", bolge="3. kat koridor")
        print("=" * 60)
        print(f"[{tur}] SORU: {soru}")
        bulunanlar = [m["madde"] for m in _maddeleri_bul(soru, "otel")]
        print("Gemini'ye gönderilen maddeler:", bulunanlar)
        print(sonuc["cevap"])
        print("KAYNAKLAR:", sonuc["kaynaklar"])
