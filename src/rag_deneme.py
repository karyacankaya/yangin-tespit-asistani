"""H7: RAG bilgi tabanı denemesi.

Ne yapar?
  1) bge-m3 modeli ile kısa bir benzerlik testi yapar.
  2) kb/maddeler.jsonl dosyasındaki maddeleri Chroma'ya (kb/chroma_db) yükler.
  3) 5 deneme sorusu sorar ve en yakın 3 maddeyi ekrana yazar.

Çalıştırma (repo klasöründeyken):  python3 src/rag_deneme.py
"""
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

REPO = Path(__file__).resolve().parent.parent
JSONL_YOLU = REPO / "kb" / "maddeler.jsonl"
CHROMA_YOLU = REPO / "kb" / "chroma_db"

# ---------------------------------------------------------------
# 1) Modeli yükle (ilk çalıştırmada ~2 GB iner, sonra bilgisayarda kalır)
# ---------------------------------------------------------------
print("Model yükleniyor (ilk seferde birkaç dakika sürebilir)...")
model = SentenceTransformer("BAAI/bge-m3")

# ---------------------------------------------------------------
# 2) Benzerlik testi: soru, asansör cümlesine daha yakın çıkmalı
# ---------------------------------------------------------------
cumleler = [
    "Yangında asansör kullanılır mı?",
    "Asansörler yangın sırasında kullanılmaz.",
    "Bugün hava çok güzel.",
]
vektorler = model.encode(cumleler, normalize_embeddings=True)
benzerlik = model.similarity(vektorler, vektorler)
asansor_skoru = float(benzerlik[0][1])
hava_skoru = float(benzerlik[0][2])
print("\n--- Benzerlik testi ---")
print(f"Soru <-> asansör cümlesi : {asansor_skoru:.3f}")
print(f"Soru <-> hava cümlesi    : {hava_skoru:.3f}")
print("SONUÇ:", "Sistem çalışıyor ✅" if asansor_skoru > hava_skoru else "Bir sorun var ❌")

# ---------------------------------------------------------------
# 3) maddeler.jsonl dosyasını oku ve Chroma'ya yükle
# ---------------------------------------------------------------
maddeler = []
with open(JSONL_YOLU, encoding="utf-8") as f:
    for satir in f:
        if satir.strip():
            maddeler.append(json.loads(satir))

istemci = chromadb.PersistentClient(path=str(CHROMA_YOLU))
koleksiyon = istemci.get_or_create_collection(
    "yonetmelik", metadata={"hnsw:space": "cosine"}
)

print(f"\n{len(maddeler)} madde vektöre çevriliyor...")
metinler = [m["metin"] for m in maddeler]
embeddingler = model.encode(metinler, normalize_embeddings=True, show_progress_bar=True)

# upsert: dosyayı ikinci kez çalıştırırsan aynı maddeleri tekrar eklemez, günceller
koleksiyon.upsert(
    ids=[f"madde_{m['madde']}" for m in maddeler],
    embeddings=embeddingler.tolist(),
    documents=metinler,
    metadatas=[
        {
            "madde": m["madde"],
            "konu": m["konu"],
            "bina_tipleri": ", ".join(m["bina_tipleri"]),  # Chroma liste kabul etmez
            "eylem_adimi": m["eylem_adimi"],
            "kaynak": m["kaynak"],
        }
        for m in maddeler
    ],
)
print("Koleksiyondaki toplam madde sayısı:", koleksiyon.count())

# ---------------------------------------------------------------
# 4) Arama testi: 5 deneme sorusu
# ---------------------------------------------------------------
sorular = [
    "Yangında asansör kullanılır mı?",
    "Elektrik kesilince kaçış yolları nasıl aydınlatılır?",
    "Yangın alarmı çalınca ilk ne yapmalıyım?",
    "Küçük bir yangını nasıl söndürürüm?",
    "Koridor dumanla dolarsa ne olur?",
]
print("\n--- Arama testi ---")
for soru in sorular:
    soru_vektoru = model.encode([soru], normalize_embeddings=True).tolist()
    sonuc = koleksiyon.query(query_embeddings=soru_vektoru, n_results=3)
    print(f"\nSORU: {soru}")
    for sira, (meta, mesafe) in enumerate(
        zip(sonuc["metadatas"][0], sonuc["distances"][0]), start=1
    ):
        print(f"  {sira}. Madde {meta['madde']} ({meta['konu']}), benzerlik {1 - mesafe:.2f}")
        print(f"     Eylem: {meta['eylem_adimi']}")