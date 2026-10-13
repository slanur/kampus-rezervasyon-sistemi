# Senaryo 01 — Ücret bantları (K5)

Bu senaryo K5'in en riskli alt kurallarını hedefler: bant sınırını aşan
talepler, doluluk eşiğinin tam sınırda davranışı, pik saat sınırının bandı
ikiye bölmesi ve `kaynak_ekle` ile değişen türdeki kaynak sayısı.

| # | Komut | Beklenen | Gerekçe |
|---|---|---|---|
| 1 | `kaynak_ekle YAZ-2` | TAMAM | YAZICI türündeki kaynak sayısı 1→2 olur. |
| 2 | `rezervasyon u1 YAZ-1 10:00-11:00` | TAMAM, ücret **18** | Tamamı 10-12 bandında (pik, enerji yoğun ×1,5), doluluk 0 → çarpan 1,0. 4 dilim × 12×0,25×1,0×1,5 = 18. |
| 3 | `fiyat u2 YAZ-2 11:00-13:00` | ücret **41** | 10-12 bandında (4 dilim): r1'in 60 dakikası var, YAZICI sayısı artık 2 → doluluk 60/240=0,25 → çarpan 1,25 → 4×12×0,25×1,25×1,5=22,5. 12-14 bandında (4 dilim) doluluk 0 → çarpan 1,0 → 4×12×0,25×1,0×1,5=18. Toplam 40,5 → **yuvarla 41** (tam 0,5 yukarı). |
| 4 | `rezervasyon u2 ODA-1 10:00-10:30` | TAMAM, ücret **2** | ODA enerji yoğun değil, doluluk 0: 2 dilim × 4×0,25×1,0×1,0 = 2. |
| 5 | `fiyat u1 ODA-1 10:30-11:30` | ücret **5** | r2'nin 10-12 bandındaki 30 dakikası, ODA sayısı 1 → doluluk 30/120 = **tam 0,25** → alt sınır dahil olduğundan çarpan **1,25** (0,50 değil). 4 dilim × 4×0,25×1,25×1,0 = 5. |
| 6 | `rezervasyon u3 CIH-1 15:30-16:30` | TAMAM, ücret **20** | Talep iki bandı kapsıyor: 14-16 (pik, 2 dilim) ve 16-18 (pik değil, 2 dilim). Pik kısım: 2×16×0,25×1,0×1,5=12. Normal kısım: 2×16×0,25×1,0×1,0=8. Toplam 20. |

Tüm değerler `rezervasyon/fiyat.py` içindeki `Fraction` tabanlı hesapla
elle doğrulanmış, engine çıktısıyla birebir eşleşmiştir.
