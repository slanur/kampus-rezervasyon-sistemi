# Senaryo 06 — Durum makinesi: giriş, çıkış, gelmeme, tamamlanma (K8, K11)

Bir rezervasyonun bütün yaşam döngüsünü dener: ONAYLI → KULLANIMDA →
TAMAMLANDI (bitişte ya da erken çıkışla) ve ONAYLI → GELMEDI. Giriş
penceresinin iki sınırını, `giris`/`cikis` hata sırasını
(`BULUNAMADI` → `DURUM_HATASI` → `GIRIS_PENCERESI_DISI`), erken çıkışta
bitişin güncellenmesini ve güvenilirliğin 100'de kırpılmasını gösterir.

Başlangıç: saat Pzt 08.03.2027 08:00. ODA-1 (ODA, h=0, 4 KP/sa) ve LAB-1
(LAB, h=10, 8 KP/sa). Kullanıcılar: u1 OGRENCI (120 KP, güv. 80), u2
ARASTIRMACI (300 KP, güv. 80, LAB_GUVENLIK), u3 OGRENCI (120 KP, güv. **99**).
Her türde tek kaynak vardır; enerji yoğun tür yoktur, yani pik çarpanı hep 1,0'dır.

| # | Komut | Beklenen | Gerekçe |
|---|---|---|---|
| 1 | `rezervasyon u1 ODA-1 09:00-10:00` | TAMAM r1, ücret **4**, bakiye 116 | 08–10 bandı boş, çarpan 1,0. 4 dilim × 4 × 0,25 = 4. |
| 2 | `rezervasyon u2 LAB-1 09:00-11:00` | TAMAM r2, ücret **16**, bakiye 284 | 08–10 ve 10–12 bantlarında 4'er dilim: 2 × (4 × 8 × 0,25) = 16. |
| 3 | `rezervasyon u3 ODA-1 10:30-11:30` | TAMAM r3, ücret 4, bakiye 116 | ODA'da h=0 olduğu için r1'in 10:00 bitişi engel değil. r1 10–12 bandında olmadığından doluluk 0. |
| 4 | `giris r1` (saat 08:00) | RED **GIRIS_PENCERESI_DISI** | Pencere [08:50, 09:15]. 08:00 çok erken. |
| 5 | `cikis r1` | RED **DURUM_HATASI** | Çıkış yalnızca KULLANIMDA durumunda yapılır; r1 ONAYLI. |
| 6 | `giris r99` | RED **BULUNAMADI** | Böyle bir rezervasyon yok. |
| 7 | `saat 08:50` | TAMAM, olay yok | (08:00, 08:50] aralığında olay yok. |
| 8 | `giris r1` | TAMAM, yeni_durum **KULLANIMDA** | 08:50 = başlangıç − 10 dk; pencerenin alt sınırı dahildir. |
| 9 | `saat 09:15` | 1 olay: **GELMEDI r2**, u2 güv. 80 − 15 = **65** | r2'ye giriş yapılmadı; olay tam b + 15 = 09:15'te ve yeni saat dahil işlenir. LAB-1'de bekleme kaydı olmadığı için atama yok. |
| 10 | `giris r2` | RED **DURUM_HATASI** | r2 artık GELMEDI. Saat pencerede (09:15) olsa da durum kontrolü önce gelir. |
| 11 | `saat 10:00` | 1 olay: **TAMAMLANDI r1**, u1 güv. 80 + 2 = **82** | KULLANIMDA r1 bitiş saatinde kendiliğinden tamamlanır. |
| 12 | `saat 10:20` | TAMAM, olay yok | |
| 13 | `giris r3` | TAMAM, KULLANIMDA | 10:20 = 10:30 − 10 dk, sınırda. |
| 14 | `saat 11:00` | TAMAM, olay yok | r3 KULLANIMDA, bitişi 11:30. |
| 15 | `cikis r3` | TAMAM, yeni_durum **TAMAMLANDI**, güv. **99** (değişmez), olaylar [] | Erken çıkış: bitiş 11:00 olur, iade yok, güvenilirlik değişmez. ODA-1'de bekleme kaydı yok. |
| 16 | `rezervasyon u1 ODA-1 11:00-11:30` | TAMAM **r4**, ücret 2, bakiye 114 | r3'ün boşalttığı 11:00–11:30 artık alınabilir. TAMAMLANDI r3 kesişmede sayılmaz, h=0. u1'in r1'i 10:00'da bitti, boşluk 60 dk (K4 tamam). Doluluk 0. 2 dilim × 1 = 2. |
| 17 | `rezervasyon u3 ODA-1 12:00-12:30` | TAMAM **r5**, ücret 2, bakiye 114 | **Bitişin güncellendiğinin kanıtı:** u3'ün r3'ü 11:00'da bitmiş sayılır, boşluk 60 dk. Bitiş 11:30 kalsaydı boşluk 30 dk olur ve `ARDISIK_KULLANIM` dönerdi. |
| 18 | `saat 11:55` | 1 olay: **GELMEDI r4** (11:15), u1 güv. 82 − 15 = **67** | |
| 19 | `giris r5` | TAMAM, KULLANIMDA | 11:55, pencerenin [11:50, 12:15] içinde. |
| 20 | `saat 12:30` | 1 olay: **TAMAMLANDI r5**, u3 güv. **100** | 99 + 2 = 101 olur, ama değer 0–100 aralığında tutulur. |
| 21 | `sorgu kullanici u3` | bakiye 114, güv. 100, [r3 10:30–**11:00** TAMAMLANDI 4, r5 TAMAMLANDI 2] | r3'ün bitişi çıkış saatidir; erken çıkışta ücret iade edilmez. |
| 22 | `sorgu kullanici u1` | bakiye 114, güv. 67, [r1 TAMAMLANDI 4, r4 GELMEDI 2] | Gelmemede iade yoktur. |
| 23 | `sorgu kullanici u2` | bakiye 284, güv. 65, [r2 GELMEDI 16] | |

Beklenen değerler kurallardan elle hesaplanmış, ardından motor çıktısıyla
karşılaştırılmıştır.
