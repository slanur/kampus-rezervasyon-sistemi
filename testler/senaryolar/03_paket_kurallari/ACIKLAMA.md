# Senaryo 03 — Paket rezervasyon (K7)

K7'nin denetim sırasını (BULUNAMADI → PAKET_BOYUTU → GUVENILIRLIK_DUSUK →
PAKET_RED → PAKET_ICI_KESISME → BAKIYE_YETERSIZ) uçtan uca dener.

| # | Komut | Beklenen | Gerekçe |
|---|---|---|---|
| 3 | `paket u3` (1 kalem) | RED **PAKET_BOYUTU**, `kalemler: []` | Kalem sayısı 2'den az. |
| 4 | `paket uD` (güv 40) | RED **GUVENILIRLIK_DUSUK**, `kalemler: []` | Güvenilirlik 50'nin altında; kalemler denetlenmeden reddedilir. |
| 5 | `paket u3`: CIH-1 10-11 (geçerli) + LAB-1 10:05-11:00 (15dk'ya oturmuyor) | RED **PAKET_RED**, `[{0,TAMAM},{1,RED,ZAMAN_ADIMI_HATASI}]` | Bir kalem geçersiz → tüm kalemler kendi sonucuyla listelenir. |
| 6 | `paket u3`: aynı kaynakta (CIH-1) çakışan iki kalem | RED **PAKET_ICI_KESISME**, tüm kalemler `TAMAM` | Kalemler tek başına geçerli ama birbirleriyle (h=15dk CIHAZ hazırlığı da dahil) çakışıyor. |
| 7 | `paket uE` (bakiye 5): CIH-1(24) + ODA-1(4) = 28 KP | RED **BAKIYE_YETERSIZ**, tüm kalemler `TAMAM` | Toplam ücret bakiyeyi aşıyor; kalemlerin kendisi geçerli olduğundan hepsi `TAMAM` görünür. |
| 8 | `paket u3`: CIH-1 14-15 + ODA-1 14-15 | TAMAM **p1**, `[r1,r2]`, `[24,4]`, toplam **28**, bakiye **272** | Her iki kalem de geçerli; CIH-1 pik saatte (24 KP), ODA enerji yoğun değil (4 KP). |
| 9 | `iptal r1` | TAMAM, iade **12**, bakiye **284** | Kalan süre 6 saat (2–24 saat arası) → %50 iade = 12. |
| 10 | `sorgu kullanici u3` | `[r1 IPTAL 24, r2 ONAYLI 4]` | Paketin bir kalemi iptal edilse de diğeri (r2) etkilenmeden ONAYLI kalır — "paket kalemi tek başına iptal edilebilir" kuralının kanıtı. |
