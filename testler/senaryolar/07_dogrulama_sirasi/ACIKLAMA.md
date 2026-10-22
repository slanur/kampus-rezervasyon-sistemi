# Senaryo 07 — Rezervasyon doğrulama sırası (K1–K4, K10)

K10'daki 13 adımın her birini en az bir kez tetikler. Birden fazla kuralı
aynı anda ihlal eden taleplerle **ilk başarısız adımın** kodunun döndüğünü
gösterir. Ayrıca sınır değerleri (bakım bitişi, ileri tarih sınırı, hazırlık
sonu) ve `sorgu kaynak` çıktısını dener.

Başlangıç: saat Pzt 08.03.2027 08:00. YAZ-1 (YAZICI, h=20, 12 KP/sa, enerji
yoğun, yalnız OGRENCI), LAB-1 (LAB_GUVENLIK ister), ODA-1, CIH-1 (yalnız
ARASTIRMACI, CIHAZ_EGITIMI ister). YAZ-1'de 08.03 **12:00–13:00 bakım** var.
Kullanıcılar (hepsi OGRENCI, sertifikasız): u1 (120 KP, güv. 80), u2 (**5 KP**),
u4 (güv. **40**), u5 (120 KP, güv. 80).

Tarih verilmeyen satırlar 08.03.2027 içindir.

| # | Komut | Beklenen | Adım | Gerekçe |
|---|---|---|---|---|
| 1 | `rezervasyon u9 YAZ-1 09:00-10:00` | RED **BULUNAMADI** | 1 | u9 diye bir kullanıcı yok. |
| 2 | `rezervasyon u1 X-9 09:00-10:00` | RED **BULUNAMADI** | 1 | X-9 diye bir kaynak yok. |
| 3 | `rezervasyon u1 YAZ-1 07:10-07:20` | RED **ZAMAN_ADIMI_HATASI** | 2 | Bu talep adım 2, 3, 4 ve 5'i birlikte ihlal ediyor; ilk başarısız adım döner. |
| 4 | `rezervasyon u1 YAZ-1 10:00-09:00` | RED **ZAMAN_ADIMI_HATASI** | 2 | Bitiş başlangıçtan önce. |
| 5 | `rezervasyon u1 YAZ-1 07:00-07:30` | RED **GECMIS_ZAMAN** | 3 | Saatler adıma oturuyor ama başlangıç 08:00'den önce. Çalışma saati dışı da olduğu hâlde adım 3 önce gelir. |
| 6 | `rezervasyon u1 YAZ-1 09.03 21:30-22:30` | RED **CALISMA_SAATI_DISI** | 4 | Bitiş 22:00'ı aşıyor. |
| 7 | `rezervasyon u1 YAZ-1 09.03 07:45-08:30` | RED **CALISMA_SAATI_DISI** | 4 | Gelecekte, ama 08:00'den önce başlıyor. |
| 8 | `rezervasyon u1 YAZ-1 09:00-09:15` | RED **SURE_SINIRI** | 5 | 15 dk < 30 dk. |
| 9 | `rezervasyon u1 YAZ-1 09:00-12:15` | RED **SURE_SINIRI** | 5 | 195 dk > OGRENCI azamisi 180. Bakımla da kesişiyor, ama adım 5 adım 9'dan önce gelir. |
| 10 | `rezervasyon u1 YAZ-1 15.03 08:15-09:00` | RED **ILERI_TARIH_SINIRI** | 6 | Sınır 08.03 08:00 + 7 × 24 sa = 15.03 08:00. 08:15 bu sınırı aşıyor. |
| 11 | `rezervasyon u4 ODA-1 09.03 09:00-10:00` | RED **ILERI_TARIH_SINIRI** | 6 | u4'ün güvenilirliği 50'nin altında; sınır **1 güne** iner: 09.03 08:00. |
| 12 | `rezervasyon u4 ODA-1 09.03 08:00-08:30` | TAMAM r1, ücret **2**, bakiye 118 | — | Başlangıç sınıra **tam eşit**; "aşamaz" olduğu için geçerli. ODA, 2 dilim × 4 × 0,25 = 2. |
| 13 | `rezervasyon u1 CIH-1 09:00-10:00` | RED **ROL_IZNI_YOK** | 7 | OGRENCI izinli değil. Sertifika da eksik, ama adım 7 önce gelir. |
| 14 | `rezervasyon u1 LAB-1 09:00-10:00` | RED **SERTIFIKA_YOK** | 8 | LAB, LAB_GUVENLIK ister. |
| 15 | `rezervasyon u1 YAZ-1 11:00-12:30` | RED **BAKIM** | 9 | 12:00–12:30 bakımla kesişiyor. |
| 16 | `rezervasyon u1 YAZ-1 13:00-14:00` | TAMAM r2, ücret **18**, bakiye 102 | — | Bakım 13:00'da bitiyor ve bakımdan sonra hazırlık süresi **uygulanmaz** (K2). 12–14 bandında YAZICI doluluğu 0 (bakım sayılmaz), pik ×1,5: 4 × 12 × 0,25 × 1,5 = 18. |
| 17 | `rezervasyon u5 YAZ-1 13:30-14:30` | RED **KESISME** | 10 | r2 (13:00–14:00, ONAYLI) ile kesişiyor. |
| 18 | `rezervasyon u5 YAZ-1 14:15-15:00` | RED **HAZIRLIK_IHLALI** | 11 | Kesişme yok, ama r2'nin hazırlığı 14:20'de bitiyor: 14:15 < 14:00 + 20. |
| 19 | `rezervasyon u1 YAZ-1 14:30-15:00` | RED **ARDISIK_KULLANIM** | 12 | Hazırlık tamam (14:30 ≥ 14:20), ama aynı kullanıcının r2'sinden yalnızca 30 dk sonra (< 60). |
| 20 | `rezervasyon u2 YAZ-1 15:00-16:00` | RED **BAKIYE_YETERSIZ** | 13 | Diğer tüm kontroller geçiyor. Ücret 18 (14–16 bandı boş, pik), bakiye yalnızca 5. |
| 21 | `fiyat u2 YAZ-1 15:00-16:00` | TAMAM, ücret **18** | — | `fiyat` bakiye dışındaki tüm kontrolleri yapar; aynı talep burada geçer. |
| 22 | `sorgu kaynak YAZ-1 2027-03-08` | [12:00–13:00 BAKIM, 13:00–14:00 REZERVASYON r2] | — | Başlangıca göre sıralı; yalnız ONAYLI/KULLANIMDA rezervasyonlar ve bakımlar listelenir. |
| 23 | `sorgu kullanici u1` | bakiye 102, güv. 80, [r2 ONAYLI 18] | — | Reddedilen talepler hiçbir şey değiştirmedi ve rezervasyon numarası tüketmedi (r1, r2). |

Beklenen değerler kurallardan elle hesaplanmış, ardından motor çıktısıyla
karşılaştırılmıştır.
