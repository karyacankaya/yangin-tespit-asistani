# RAG arama testi sonuçları (23 Ekim 2026)

Model: `BAAI/bge-m3` · Veritabanı: Chroma (`kb/chroma_db`, koleksiyon `yonetmelik`) · Kod: `src/rag_deneme.py`

**Benzerlik testi:** "Yangında asansör kullanılır mı?" → asansör cümlesi 0,798, hava cümlesi 0,357. Sistem çalışıyor ✅
**Yüklenen madde sayısı:** 36 (`kb/maddeler.jsonl` satır sayısıyla aynı)

| # | Soru | İlk 3 sonuç (benzerlik) | Değerlendirme |
|---|------|-------------------------|---------------|
| 1 | Yangında asansör kullanılır mı? | 63 asansör (0,65), 62 asansör (0,63), 34 kaçış (0,60) | ✅ Doğru maddeler ilk iki sırada |
| 2 | Elektrik kesilince kaçış yolları nasıl aydınlatılır? | 70, 71, 72 aydınlatma (0,67 / 0,64 / 0,58) | ✅ Üçü de doğru konu |
| 3 | Yangın alarmı çalınca ilk ne yapmalıyım? | 75 alarm (0,66), 128 ekip (0,62), 76 alarm (0,61) | ✅ 75 ve 76 doğru, 128 kısmen ilgili |
| 4 | Küçük bir yangını nasıl söndürürüm? | 75 alarm (0,56), 99 söndürme (0,56), 136 iç düzenleme (0,55) | ⚠️ Doğru madde (99) 2. sırada, skorlar birbirine çok yakın |
| 5 | Koridor dumanla dolarsa ne olur? | 88 duman (0,47), 85 duman (0,45), 34 kaçış (0,45) | ⚠️ Konu doğru ama skorlar düşük; koridor/kaçış yolu dumanına özel madde yok |

**Notlar / sonraki adımlar**
- 5 sorunun 3'ünde doğru madde 1. sırada, 5'inin hepsinde ilk 3 içinde.
- Uzun maddeler (72, 81, 99: 3000+ karakter) tek vektöre sıkışıyor; H8+'da fıkra bazında parçalamak (chunking) skorları iyileştirebilir.
- Metadata'daki `konu` alanıyla filtreleme (ör. soru "duman" içeriyorsa `where={"konu": "duman"}`) denenebilir.
- `kb/chroma_db` klasörü GitHub'a yüklenmedi (.gitignore); `python src/rag_deneme.py` ile 1-2 dakikada yeniden oluşturulur.
