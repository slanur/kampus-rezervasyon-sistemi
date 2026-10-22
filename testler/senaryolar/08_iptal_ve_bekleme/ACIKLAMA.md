# Senaryo 08 — İptal iadesi ve bekleme listesinin yaşam döngüsü (K8, K9, K11)

İptal iadesinin üç kademesini (%100, %50 aşağı yuvarlama, %0 ve −5
güvenilirlik), `bekleme` komutunun dönebileceği bütün sonuçları ve süresi
geçen bekleme kaydının sessizce silinmesini dener.

Başlangıç: saat Pzt 08.03.2027 08:00. İki ODA (ODA-1, ODA-2; h=0, 4 KP/sa,
enerji yoğun değil). Hepsi OGRENCI: u1 (güv. 80), u2 (güv. **70**), u3 (güv. **90**),
bakiyeleri 120. Tarih verilmeyen satırlar 08.03.2027 içindir.

| # | Komut | Beklenen | Gerekçe |
|---|---|---|---|
| 1 | `rezervasyon u1 ODA-1 09.03 10:00-11:00` | TAMAM r1, ücret 4, bakiye 116 | 4 dilim × 4 × 0,25. |
| 2 | `rezervasyon u1 ODA-1 12:00-13:15` | TAMAM r2, ücret **5**, bakiye 111 | 5 dilim → **tek** ücret (iadede yuvarlamayı göstermek için). |
| 3 | `rezervasyon u1 ODA-2 09:00-10:00` | TAMAM r3, ücret 4, bakiye 107 | |
| 4 | `iptal r1` | iade **4** (%100), bakiye 111, güv. 80 | Başlangıca 26 saat var (≥ 24). |
| 5 | `iptal r2` | iade **2** (%50), bakiye 113, güv. 80 | 4 saat var (2–24 arası). 5 / 2 = 2,5 → **aşağı** yuvarlanır: 2. |
| 6 | `iptal r3` | iade **0**, bakiye 113, güv. **75** | 1 saat var (< 2): iade yok, güvenilirlik −5. |
| 7 | `iptal r3` | RED **DURUM_HATASI** | Yalnız ONAYLI rezervasyon iptal edilebilir. |
| 8 | `rezervasyon u1 ODA-1 10:00-11:00` | TAMAM r4, ücret 4, bakiye 109 | u1'in IPTAL olan r2'si K4'te sayılmaz. |
| 9 | `bekleme u2 ODA-1 10:00-11:00` | TAMAM **b1**, sıra 1 | r4 ile KESISME → kayıt açılır. |
| 10 | `bekleme u3 ODA-1 10:30-11:00` | TAMAM **b2**, sıra **1** | u3'ün güvenilirliği (90) u2'ninkinden (70) yüksek; b1'in önüne geçer. |
| 11 | `bekleme u2 ODA-2 10:00-11:00` | RED **BEKLEME_GEREKSIZ** | ODA-2'deki r3 iptal edildi; talep zaten geçerli. |
| 12 | `bekleme u2 ODA-1 09:10-10:00` | RED **ZAMAN_ADIMI_HATASI** | Talep kesişme dışında bir nedenle geçersizse o kod döner; kayıt açılmaz, b numarası tüketilmez. |
| 13 | `saat 08:30` | TAMAM, olay yok | |
| 14 | `iptal r4` | iade 0, bakiye 109, güv. **70**, olaylar: **OTOMATIK_ATAMA b2 → r5** (u3, ücret 2, bakiye 118) | 1,5 saat var → %0, −5. ODA-1 boşalınca bekleme listesi sırayla taranır: önce b2 (u3, güv. 90). 10:30–11:00 artık geçerli, doluluk 0 (r4 IPTAL) → 2 dilim = 2 KP. Ardından b1 (u2, 10:00–11:00) yeni r5 ile kesiştiği için **listede kalır**. |
| 15 | `saat 10:05` | TAMAM, olay yok | b1'in başlangıcı (10:00) artık simüle saatten önce → kayıt **sessizce silinir** (olay üretmez). r5'in gelmeme anı 10:45, henüz gelmedi. |
| 16 | `bekleme u2 ODA-1 10:30-11:00` | TAMAM **b3**, sıra **1** | **Silinmenin kanıtı:** b1 listede kalsaydı (aynı kullanıcı, aynı güvenilirlik, daha erken kayıt) önde olurdu ve b3'ün sırası 2 olurdu. |
| 17 | `saat 10:00` | RED **SAAT_GERI** | Yeni saat mevcut saatten (10:05) önce. |
| 18 | `saat 10:05` | TAMAM, olay yok | Aynı saate "ilerletmek" hata değildir. |
| 19 | `sorgu kaynak ODA-1 2027-03-08` | [10:30–11:00 REZERVASYON r5] | IPTAL olan r2 ve r4 listelenmez. |
| 20 | `sorgu kullanici u1` | bakiye 109, güv. 70, [r3, r4, r2 (08.03), r1 (09.03)] — hepsi IPTAL | Başlangıca göre sıralı; numaraya göre değil. |
| 21 | `sorgu kullanici u3` | bakiye 118, güv. 90, [r5 ONAYLI 2] | Otomatik atamayla oluşan rezervasyon da kullanıcının kendi rezervasyonudur. |

Beklenen değerler kurallardan elle hesaplanmış, ardından motor çıktısıyla
karşılaştırılmıştır.
