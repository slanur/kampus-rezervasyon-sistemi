# Senaryo 05 — Kullanıcı/kaynak ekleme doğrulama sırası (K10-ek)

`kullanici_ekle` ve `kaynak_ekle` için 3 adımlı denetim sırasını
(`ID_MEVCUT` → `TANIMSIZ_DEGER` → `GECERSIZ_DEGER`) ve sınır değerlerini
dener.

| # | Komut | Beklenen | Gerekçe |
|---|---|---|---|
| 1 | `kullanici_ekle u1` | TAMAM | Geçerli. |
| 2 | `kullanici_ekle u1` (tekrar) | RED **ID_MEVCUT** | Aynı id zaten var. |
| 3 | `kullanici_ekle u9` (rol `DOKTORA`, bakiye −10, güv 200) | RED **TANIMSIZ_DEGER** | Rol tanımsız olduğundan, bakiye/güvenilirlik geçersiz olsa bile sıraya göre önce bu döner. |
| 4 | `kullanici_ekle u9` (OGRENCI, bakiye 130 > kota 120) | RED **GECERSIZ_DEGER** | Bakiye kotayı aşıyor. |
| 5 | `kullanici_ekle u9` (OGRENCI, bakiye 50, güv 150) | RED **GECERSIZ_DEGER** | Güvenilirlik 0–100 aralığının dışında. |
| 6 | `kullanici_ekle u9` (OGRENCI, bakiye 50, güv 80) | TAMAM | Tüm değerler geçerli. |
| 7 | `kaynak_ekle YAZ-1` (tekrar) | RED **ID_MEVCUT** | Kaynak id'si zaten var (kullanıcı/kaynak id uzayları ayrıdır — u1 ile YAZ-1 çakışmaz). |
| 8 | `kaynak_ekle K9` (tür `ROKET`) | RED **TANIMSIZ_DEGER** | Tür tanımlı değil. |
| 9 | `kaynak_ekle K9` (tür ODA, izinli `["OGRENCI","UZAYLI"]`) | RED **TANIMSIZ_DEGER** | İzinli rollerden biri (`UZAYLI`) tanımsız. |
| 10 | `kaynak_ekle K9` (tür ODA, izinli `[]`) | TAMAM | Boş izinli roller listesi geçerlidir. |
| 11 | `rezervasyon u9 K9 ...` | RED **ROL_IZNI_YOK** | İzinli roller boş olduğundan hiç kimse bu kaynağı rezerve edemez. |
| 12 | `sorgu kullanici u9` | bakiye 50, güvenilirlik 80, `[]` | 6. adımda eklenen kullanıcının durumu doğrulanır. |

`kaynak_ekle` için bakiye/güvenilirlik denetlenmediği (yalnızca
`kullanici_ekle`'ye özgü olduğu) bu senaryoda K9 kaynağının başarıyla
eklenmesiyle ayrıca kanıtlanmıştır.
