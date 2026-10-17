# Use Case Taslağı

Kalabalık Binalarda Yangın Tespiti ve Yapay Zekâ Destekli Müdahale Asistanı

## Aktörler

| Aktör | Kim? |
|---|---|
| Güvenlik operatörü | Paneli izleyen kişi |
| Acil durum personeli | Prosedür adımlarını uygulayan kişi |
| Tesis yöneticisi | Raporları gören kişi |
| Sistem yöneticisi | Bakım yapan, model dosyalarını güncelleyen kişi |
| Zaman | Otomatik olaylar (60 saniyelik geri sayım gibi) |

## Aktörlerin sistemle etkileşimi

| Aktör | Sistemle ne yapar? | UC |
|---|---|---|
| Güvenlik operatörü | Alarmı görüntüler | UC-01 |
| Güvenlik operatörü | Alarmı doğrular | UC-02 |
| Güvenlik operatörü | Alarmı reddeder | UC-03 |
| Güvenlik operatörü | Olay günlüğünü indirir | UC-07 |
| Güvenlik operatörü | Senaryo simülasyonu başlatır | UC-09 |
| Acil durum personeli | Prosedür adımlarını izler | UC-04 |
| Acil durum personeli | Adımı tamamlandı işaretler | UC-05 |
| Acil durum personeli | Asistana soru sorar | UC-06 |
| Tesis yöneticisi | Geçmiş olayları görüntüler | UC-08 |
| Sistem yöneticisi | Model dosyalarını günceller | UC-10 (isteğe bağlı) |
| Zaman | 60 saniye cevap gelmezse seviyeyi otomatik yükseltir | UC-11 (isteğe bağlı) |

> Not: UC-10 ve UC-11 isteğe bağlıdır. Müşteri gereksinimleri (MG) listesi gelince tutulup tutulmayacağına birlikte karar verilecek.
