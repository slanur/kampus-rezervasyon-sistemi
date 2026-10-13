# Senaryo 04 — Haftalık sıfırlama ve iade kotası kırpması (K6, K11)

İki ayrı K6 davranışını birleştirir: (a) Pazartesi 00:00'da bakiyenin
kotaya **eşitlenmesi** (eklenmesi değil) ve (b) bir iptal iadesinin, kota
zaten doluyken **kırpılması**.

| # | Komut | Beklenen | Gerekçe |
|---|---|---|---|
| 1 | `rezervasyon u1 YAZ-1 08.03 10:00-11:00` | TAMAM r1, ücret 18, bakiye 102 | Normal rezervasyon. |
| 2 | `rezervasyon u2 YAZ-1 15.03 08:00-08:30` | TAMAM r2, ücret 6, bakiye 114 | Başlangıç ileri tarih sınırına (saat + 7 gün = 15.03 08:00) **tam eşit** — sınır dahil olduğundan geçerli. |
| 3 | `saat 15.03 00:00` | TAMAM, 2 olay | Önce **08.03 10:15**'te r1 GELMEDI olur (u1 güvenilirlik 65). Sonra **15.03 00:00**'da HAFTALIK_SIFIRLAMA: u1 ve u2'nin bakiyesi kotaya (120) **eşitlenir** — r2 henüz ONAYLI olduğundan (kendi gelmeme anı 15.03 08:15, hedeften sonra) bu ilerletmede etkilenmez. |
| 4 | `iptal r2` | TAMAM, **iade 0**, bakiye 120, güvenilirlik 80 | Kalan süre 8 saat (2–24 saat arası) → hesaplanan iade `6 // 2 = 3`. Ancak u2'nin bakiyesi az önceki sıfırlamayla zaten kotada (120); `iade_eklenen = max(0, min(3, 120-120)) = 0`. Sonuçtaki `iade` alanı, **gerçekte eklenen** miktarı (0) gösterir — formülün ham değerini değil. |
| 5 | `sorgu kullanici u1` | bakiye 120, güvenilirlik 65, `[r1 GELMEDI 18]` | — |
| 6 | `sorgu kullanici u2` | bakiye 120, güvenilirlik 80, `[r2 IPTAL 6]` | İade 0 olsa da güvenilirlik bu dilimde değişmediğinden 80'de kalır. |

Bu senaryo, "iade kotayı aşarsa kırpılır" kuralının yalnızca iptal anındaki
bakiyeyle değil, **aradaki bir haftalık sıfırlamayla da** tetiklenebildiğini
gösterir.
