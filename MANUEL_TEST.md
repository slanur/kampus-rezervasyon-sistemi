# Manuel Test Rehberi

Bu rehber, masaüstü uygulamasını baştan sona elle test etmek ve her ekranın
**hangi kuralı** gösterdiğini anlamak için hazırlanmıştır. Her adımda beklenen
sonuç `testler/ornek/beklenen.jsonl` dosyasından alınmıştır. Demoda hoca bu
19 işlemi arayüzden yaptırıp aynı sonucu görmek isteyecektir.

## 0. Hazırlık

```bash
source .venv/bin/activate
python3 -m pytest -q          # 117 test geçmeli
./arayuz.sh testler/ornek/baslangic.json
```

Başlangıç durumu: saat **Pzt 08.03.2027 08:00**, tek kullanıcı **u3 (Elif Şahin,
ARASTIRMACI, 300 KP)**, kaynaklar YAZ-2, CIH-1, ODA-1, ODA-2. YAZ-2'de
08:00–10:00 arası bakım vardır.

Her adımdan sonra şunları kontrol et: takvim, kullanıcı paneli ve saat
**kendiliğinden** güncellendi mi? Günlükte yeni satır var mı?

## 1. Örnek senaryo (19 işlem)

| # | Ekranda ne yapılır | Beklenen | Hangi kural |
|---|---|---|---|
| 1 | Üst bar **+** → id `u1`, ad `Ayşe Kaya`, rol OGRENCI, bakiye 120, güvenilirlik 80 | TAMAM, u1 seçicide hemen görünür | Ekleme kuralları |
| 2 | Aynısı: `u2`, `Mehmet Demir` | TAMAM | |
| 3 | Takvim altı **+ Kaynak ekle** → `YAZ-1`, `3B Yazıcı 1`, YAZICI, izinli: OGRENCI | TAMAM, takvimde yeni satır | |
| 4 | `LAB-1`, `Laboratuvar 1`, LAB, izinli: OGRENCI, ARASTIRMACI, TEKNISYEN | TAMAM | |
| 5 | Kullanıcı u1 seç. Tek mod: YAZ-1, 11:00–13:00 → Talep et | TAMAM · r1 · 36 KP · bakiye 84 | K5 ücret (pik ×1,5) |
| 6 | u2: YAZ-2 10:00–12:00 | TAMAM · r2 · 45 KP · bakiye 75 | |
| 7 | u2: YAZ-2 12:30–13:30 | RED · `ARDISIK_KULLANIM` | K4 |
| 8 | u2: LAB-1 14:00–15:00 | RED · `SERTIFIKA_YOK` | K1 |
| 9 | u1: YAZ-1, başlangıca elle **13:10** yaz, bitiş 14:00 | RED · `ZAMAN_ADIMI_HATASI` | K1 (arayüz engellemez!) |
| 10 | u1: YAZ-1 13:15–14:00 | RED · `HAZIRLIK_IHLALI` + "bekleme listesine gir" düğmesi | K3 |
| 11 | u3: CIH-1 14:00–16:00 → **Fiyat sor** (form altındaki tahmini ücret de 48 gösterir, ama günlüğe yazılmaz) | 48 KP, günlükte `fiyat` satırı | `fiyat` |
| 12 | u3: **Paket** modu, kalem 1 CIH-1 14:00–16:00, kalem 2 ODA-1 14:00–16:00 | TAMAM · p1 · r3, r4 · toplam 56 · bakiye 244 | K7 |
| 13 | u1: CIH-1 16:30–17:30 | RED · `ROL_IZNI_YOK` | K1 (rol 7. adım, sertifikadan önce) |
| 14 | u1: takvimde ileri gün tuşuyla **16.03.2027**'ye git, ODA-2 09:00–10:00 | RED · `ILERI_TARIH_SINIRI` | K1 (OGRENCI 7 gün) |
| 15 | 08.03'e dön. u2: YAZ-1 12:00–13:00 → red kartında **Bekleme listesine gir** (ya da önce reddi al) | b1 · sıra 1 | K9 |
| 16 | **Saate git…** → tarih 08.03.2027, saat `11:20`, Enter | 3 olay: r2 GELMEDI (güv. 65), r1 GELMEDI (güv. 65), OTOMATIK_ATAMA b1 → r5 (18 KP, bakiye 57) | K8, K9, K11 |
| 17 | Takvimde r1 kutusuna tıkla → **Giriş** | RED · `DURUM_HATASI` (r1 artık GELMEDI) | K8 |
| 18 | r4 kutusu → **İptal** (önizleme %50 iade göstermeli) | TAMAM · iade 4 · bakiye 248 | K8 (iade tablosu), K6 (kota) |
| 19 | u2'yi seç, kullanıcı panelini incele | bakiye 57, güv. 65, r2 GELMEDI, r5 ONAYLI | `sorgu` (panel otomatik yenilenir, günlüğe yazılmaz) |

> Not 15. adım için: KESISME / HAZIRLIK_IHLALI reddinden sonra bekleme
> düğmesi gelir. Doğrudan talep YAZ-1 12:00–13:00 r1 ile çakışacağı için
> `KESISME` verir; düğmeye basınca bilgiler **yeniden girilmeden** b1 açılır.
> Bu yüzden günlükte bekleme satırından önce fazladan bir RED satırı olur;
> GUI'de günlük 19 değil 20 satır tutar. Bu beklenen bir durumdur, sonuçların
> içeriği yine aynıdır.

**Takvimde 16. adımdan sonra görmen gerekenler:**
- r1 ve r2 kırmızı, kesik kenarlı (GELMEDI), **alt satırda**. Modül pasif
  rezervasyonları (IPTAL, GELMEDI) her zaman alt satıra, etkinleri üst satıra koyar.
- r5 (u2, YAZ-1 12:00–13:00) üst satırda, ONAYLI.
- r4 IPTAL, alt satırda üstü çizili.
- Mavi "şimdi" çizgisi 11:20'de.

## 2. Kenar durumları (demo için iyi örnekler)

| Dene | Beklenen |
|---|---|
| Kullanıcı ekle, aynı id `u1` | `ID_MEVCUT` |
| Kullanıcı ekle, güvenilirlik `150` veya bakiye `-5` | `GECERSIZ_DEGER` |
| Saate git → şu andan geriye bir zaman | `SAAT_GERI` |
| Formda alanları değiştir (göndermeden) | Günlüğe **hiçbir** satır eklenmez |
| Bitiş < başlangıç (ör. 14:00–13:00) | Kod + Türkçe açıklama |
| 21:30–22:30 (çalışma saati dışı) | Kod + açıklama |
| ONAYLI bir rezervasyonda **Çıkış** | `DURUM_HATASI` |
| KULLANIMDA rezervasyonda erken **Çıkış** | Bitiş güncellenir, hazırlık şeridi kayar |
| Paket: kalemlerden biri geçersiz | `PAKET_RED`, **her kalem kendi satırında** geçti / neden |
| Geri al (Ctrl+Z) | Son durum değiştiren işlem geri alınır |
| "Dosya değiştir" ile başka bir senaryo dosyası | Tüm durum ve günlük sıfırlanır |
| `testler/senaryolar/*/baslangic.json` dosyalarını yükle | Parametreler değişince arayüz kod değişmeden yeni kurala uyar |

## 3. Kısayollar

| Tuş | İş |
|---|---|
| Ctrl/⌘+Enter | Talebi gönder |
| Ctrl/⌘+Z | Geri al (metin kutusundayken yazıyı geri alır) |
| Ctrl/⌘+F | Günlükte ara |
| ← / → | Gün değiştir |
| T | Bugün (simüle saatin günü) |
| + | Saat +15 dk |
| Boşluk | Zamanı oynat / duraklat |
| Esc | Açık pencereyi kapat |
| Enter (Saate git penceresinde) | Git |

## 4. Test sırasında not alınacaklar

Her adımda şu soruları yanıtla ve bulduklarını buraya ekle:
1. Kaç tıklama gerekti? Daha azıyla olur muydu?
2. Sonuç, işlemi yaptığım yerin yakınında mı göründü?
3. Hata mesajı ne yapmam gerektiğini söylüyor mu?
4. Gözüm bir şeyi aramak zorunda kaldı mı?

## 5. İlk manuel testte bulunanlar (20.10.2026)

19 işlemin tamamı PDF'teki sonuçlarla eşleşti. Kullanılabilirlik açısından
düzeltilecekler, önem sırasıyla. **1–5 düzeltildi** (20.10.2026):

| # | Nerede | Sorun | Neden önemli |
|---|---|---|---|
| ✅ 1 | Giriş/çıkış/iptal sonucu | Hata **kodu** gösterilmiyor, yalnızca açıklama var | PDF hatada kod + Türkçe açıklama istiyor |
| ✅ 2 | Giriş/çıkış/iptal sonucu | Sonuç kutusu, düğmeye basılan karttan uzakta (sayfanın üstünde) çıkıyor | "Geri bildirim" ölçütü: sonuç işlemin yanında görünmeli |
| ✅ 3 | Saat ilerletme sonucu | Olayların saati (10:15, 11:15) ve OTOMATIK_ATAMA'daki yeni bakiye yazmıyor | PDF olaylarda `zaman` ve `bakiye` alanlarını istiyor |
| ✅ 4 | Talep formu | Onaydan sonra form aynı değerlerle kalıyor ve hemen kırmızı KESISME gösteriyor | Kullanıcı yanlış bir şey yaptığını sanabilir |
| ✅ 5 | Paket sonucu | Kalem kalem ücretler (48, 8) gösterilmiyor, yalnızca toplam var | PDF sonucunda `ucretler` alanı var |
| 6 | Kullanıcı paneli | Rezervasyon durumu yalnızca renkli noktayla belli, yazı yok; paket bilgisi yok | Renk körlüğü ve okunabilirlik |
| 7 | Kullanıcı ekleme | Yeni eklenen kullanıcı otomatik seçilmiyor | Ekleyen kişi büyük ihtimalle hemen onun adına işlem yapacak |
| 8 | Günlük | Uzun kodlar kesiliyor (`ZAMAN_ADIMI_HATA…`) | Okunabilirlik |
| 9 | Ret önerileri | ZAMAN_ADIMI_HATASI ve ILERI_TARIH_SINIRI'nda öneri çıkmıyor | "En yakın geçerli saat 13:15" gibi bir öneri işe yarar |
| 10 | Fiyat sor | Düğmenin ne işe yaradığı belli değil, tahmini ücretle aynı görünüyor | Ya daha ikincil yapılmalı ya da açıklama eklenmeli |
| 11 | Açılış | Son kullanılan dosyalar listesi yok; her açılışta dosyayı yeniden seçmek gerekiyor | Analiz belgesinde planlanmış ama yapılmamış |
