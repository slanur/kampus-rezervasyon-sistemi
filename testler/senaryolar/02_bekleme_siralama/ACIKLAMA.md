# Senaryo 02 — Bekleme listesi sıralaması ve otomatik atama (K9)

Üç bekleme kaydı güvenilirlik farkıyla oluşturuluyor; sıralama anahtarının
`(-güvenilirlik, kayıt_saati, no)` olduğunu ve bir kaydın **güncel**
güvenilirliğe göre öne geçebildiğini gösterir.

| # | Komut | Beklenen | Gerekçe |
|---|---|---|---|
| 1-3 | `kullanici_ekle uA(60), uB(90), uC(60)` | TAMAM | Test kullanıcıları, farklı güvenilirlik. |
| 4 | `rezervasyon u3 ODA-1 09:00-10:00` | TAMAM r1 | Yeri dolduran rezervasyon. |
| 5 | `bekleme uA ODA-1 09:00-10:00` | TAMAM b1, **sıra 1** | Tek kayıt, ilk sırada. |
| 6 | `bekleme uB ODA-1 09:00-10:00` | TAMAM b2, **sıra 1** | uB (güv 90) > uA (güv 60); güvenilirliği yüksek olan öne geçer. |
| 7 | `bekleme uC ODA-1 09:00-10:00` | TAMAM b3, **sıra 3** | uC ile uA güvenilirlikte eşit (60); kayıt saatleri de eşit (08:00) → numarası küçük olan (b1/uA) önde kalır, uC en sona düşer. |
| 8 | `iptal r1` | TAMAM, iade 0, güvenilirlik 75, **1 OTOMATIK_ATAMA (uB → r2)** | Kalan süre 1 saat (<2 saat) → iade 0, güvenilirlik −5. Tarama sırası [uB, uA, uC]: uB atanır; ODA-1 artık dolu olduğundan uA ve uC için KESISME oluşur ve listede kalırlar — yalnızca **bir** otomatik atama olur. |
| 9 | `sorgu kullanici u3` | bakiye 296, güvenilirlik 75, [r1 IPTAL] | Son durumun doğrulanması. |

Bu senaryo, bir kaydın terfi etmesinin **aynı taramadaki diğer kayıtların**
sonucunu değiştirebileceğini (K9 tarama algoritmasının art arda
`dogrula()` çağırması) de kanıtlar.
