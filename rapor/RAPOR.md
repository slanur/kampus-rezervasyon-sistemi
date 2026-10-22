# Kampüs Kaynak Rezervasyon Sistemi: Kural Tabanlı Bir Rezervasyon Modülü ve Masaüstü Uygulaması

*Yazılım Laboratuvarı I — Proje I Raporu (IEEE formatına uyarlanmak üzere taslak)*

> **Not:** Bu dosya, IEEE iki sütunlu şablonuna (Word/LaTeX) aktarılmak
> üzere 4 sayfalık rapor için hazırlanmış tam içerik taslağıdır. Bölüm
> uzunlukları §19 (PROJE_ANALIZI.md) planına göre ayarlanmıştır.

## Özet

Bu çalışma, sınırlı sayıda paylaşımlı kampüs kaynağının (oda, laboratuvar,
3B yazıcı, GPU sunucusu) adil biçimde paylaşılmasını sağlayan bir
rezervasyon sistemi sunar. Sistem, arayüzden tamamen bağımsız, yalnızca
Python standart kütüphanesini kullanan bir **çekirdek modül** ile bu
çekirdeği doğrudan çağıran bir **PySide6 masaüstü uygulamasından** oluşur.
Çekirdek; zaman adımı, çalışma saati, hazırlık süresi, art arda kullanım,
dinamik doluluğa dayalı ücretlendirme, haftalık kota, paket rezervasyon,
bekleme listesi ve olay tabanlı durum makinesi olmak üzere on bir kural
grubunu uygular. Doğruluk, projenin sağladığı 19 komutluk kabul senaryosu
üzerinde **alan alan birebir eşleşme** (19/19) ile ve sekiz özgün senaryo
ile 117 otomatik testle doğrulanmıştır. Ücret hesabı `fractions.Fraction`
ile kesin aritmetikle yapılmış, kayan nokta hatası tamamen ortadan
kaldırılmıştır.

## 1. Giriş

Paylaşımlı kaynakların adil dağıtımı, talebin arzı aştığı her ortamda
temel bir mühendislik problemidir. Bu projede üniversite, kaynakları
"Kaynak Puanı" (KP) adlı sanal bir para birimiyle fiyatlandırarak talebi
düzenlemektedir: doluluk arttıkça fiyat artar, pik saatlerde enerji yoğun
cihazlar daha pahalıya gelir ve güvenilmez kullanım (gelmeme, geç iptal)
hem bekleme listesindeki önceliği hem de ne kadar ileriye rezervasyon
yapılabileceğini düşürür. Projenin hedefi, bu kuralları **birebir** ve
**parametreleştirilmiş** biçimde uygulayan bir modül ile bu modülü
doğrudan kullanan, az adımlı ve sürekli geri bildirim veren bir masaüstü
arayüzü geliştirmektir.

## 2. Yöntem

### 2.1 Mimari

Sistem üç katmandan oluşur (Şekil 1): **çekirdek** (`rezervasyon/`,
yalnızca stdlib), **CLI** (`cli.py`) ve **masaüstü uygulaması**
(`arayuz/`, PySide6). Çekirdeğin kalbinde `Motor` sınıfı bulunur; her
komut (`rezervasyon`, `paket`, `fiyat`, `iptal`, `giris`, `cikis`,
`bekleme`, `sorgu_*`, `kullanici_ekle`, `kaynak_ekle`) ayrı bir **public
fonksiyon** olarak uygulanmıştır. `Motor.calistir(dict)` bu
fonksiyonlara yönlendiren ince bir **dağıtıcıdan** ibarettir ve yalnızca
CLI tarafından kullanılır; masaüstü uygulaması aynı fonksiyonları
doğrudan çağırır. Bu tasarım, dokümanın "19 işlem arayüzden yapıldığında
aynı sonuçlar görülmelidir" şartını **otomatik testle kanıtlanabilir**
kılar: `test_api_esdegerlik.py`, örnek senaryonun 19 işlemini CLI
dağıtıcısını hiç kullanmadan, doğrudan `Motor` fonksiyonlarıyla tekrarlar
ve sonuçların birebir aynı olduğunu doğrular.

Ayrıca çekirdekte **durum değiştirmeyen** bir "görünüm API'si"
(`gorunum.py`) bulunur: `gun_gorunumu()`, alt satır (lane) yerleşimini,
hazırlık şeritlerini ve bekleme kayıtlarını; `iptal_onizleme()` ise bir
iptalin iade/güvenilirlik etkisini durum değiştirmeden hesaplar. Böylece
"hangi durumlar çakışabilir" gibi kural bilgisi yalnızca çekirdekte
kalır; GUI yalnızca çizer.

### 2.2 Veri modeli

Alan modeli, dondurulmuş (frozen) parametre türleri (`KaynakTuru`, `Rol`,
`Kaynak`) ile değişebilir durum nesnelerinden (`Kullanici`,
`Rezervasyon`, `BeklemeKaydi`) oluşan `dataclass` hiyerarşisiyle
kurulmuştur. Rezervasyon durumu, Şekil 2'deki beş durumlu bir makineyle
(`ONAYLI → KULLANIMDA → TAMAMLANDI`, `ONAYLI → GELMEDI`,
`ONAYLI → IPTAL`) modellenmiştir; geçişler yalnızca `giris`, `cikis`,
`iptal` komutları ve `saat` olay motoru tarafından tetiklenir. Bütün
durum `Depo` nesnesinde bellekte tutulur; kalıcılık yoktur ve
`kullanici_ekle`/`kaynak_ekle` ile eklenen kayıtlar yalnızca o çalışma
oturumu boyunca yaşar.

### 2.3 Kuralların uygulanışı

**Doğrulama zinciri (K10).** Tek bir `dogrula()` fonksiyonu, 13 adımlık
sırayı (`BULUNAMADI → ZAMAN_ADIMI_HATASI → … → BAKIYE_YETERSIZ`) uygular
ve ilk başarısız adımın kodunu döndürür. `rezervasyon`, `fiyat`, paket
kalemleri, `bekleme` ve otomatik atama bu **tek** fonksiyonu farklı
`simdi` ve `bakiye_kontrol` parametreleriyle çağırır — kural mantığı
hiçbir yerde tekrarlanmaz.

**Kesişme ve hazırlık (K3).** Kritik bir tuzak, hazırlık kontrolünün
kesişme kontrolünden **ayrı ve sonra** yapılması gerekliliğidir: önce
aynı kaynaktaki *tüm* rezervasyonlar kesişmeye göre taranır, yalnızca
hiçbiri çakışmıyorsa *tüm* rezervasyonlar hazırlığa göre taranır.
Rezervasyon bazında sırayla (önce bir kaydın kesişme+hazırlığına, sonra
diğerine) bakmak yanlış kod döndürebilir; bu yüzden iki ayrı döngü
kullanılmıştır (`dogrulama.py`, adım 10–11).

**Ücretlendirme (K5).** En riske açık bölüm olan ücret hesabı
`fractions.Fraction` ile yapılır: `bant_çarpanı = 1 + ⌊4·doluluk⌋/4` ve
nihai yuvarlama `⌊toplam + 1/2⌋` biçiminde, kayan nokta belirsizliği
olmadan hesaplanır. Doluluk paydası (`türdeki kaynak sayısı × 120`)
**talep anında** `Depo.turdeki_kaynak_sayisi()` ile dinamik olarak
hesaplanır; bu sayede `kaynak_ekle` ile sonradan eklenen bir kaynak,
yalnızca eklendiği andan itibaren paydaya katılır ve geçmiş ücretleri
etkilemez (bkz. Bölüm 3, Senaryo 01).

```
def saat(self, yeni):
    while True:
        t = sonraki_olay_zamani(sonra=self.saat)   # dinamik arama
        if t is None or t > yeni: break
        self.saat = t
        bekleme_temizle()
        [HAFTALIK_SIFIRLAMA] -> [TAMAMLANDI (no artan)]
            -> [GELMEDI (no artan)] -> [bosalan kaynaklar için tara()]
    self.saat = yeni
```

**Olay motoru (K11).** Otomatik atamalar yeni rezervasyonlar
yarattığından ve bunların kendi gelmeme anları ilerletilen aralığın
içinde kalabileceğinden, olaylar **önceden listelenmez**; yukarıdaki
döngü her adımda bir sonraki olay zamanını dinamik olarak arar
(`_sonraki_olay_zamani`). Aynı anda birden fazla olay varsa işlem sırası
dokümanla birebir aynıdır: önce haftalık sıfırlama, sonra rezervasyon
numarasına göre artan TAMAMLANDI'lar, sonra GELMEDI'ler, son olarak
boşalan her kaynak için bekleme taraması.

**Bekleme listesi (K9).** Sıralama anahtarı
`(-güncel_güvenilirlik, kayıt_saati, no)`'dır; bir kaydın güvenilirliği
zaman içinde değiştiğinden sıralama her taramada yeniden hesaplanır.
`tara()` listeyi tek seferde kurar ama bir kayıt rezervasyona
dönüştüğünde depo durumu değiştiğinden **sonraki kayıtlar bu yeni
rezervasyonu görür** ve KESISME alabilir — bu, Senaryo 02'de somut olarak
gösterilmiştir.

**Paket (K7) ve ekleme (K10-ek).** Paket, 6 adımlı bir sırayla (boyut →
güvenilirlik → her kalemin K10 adım 1–12 ile ayrı ayrı doğrulanması →
paket içi çakışma → toplam bakiye) atomik olarak işlenir. `kullanici_ekle`
ve `kaynak_ekle`, 3 adımlı (`ID_MEVCUT → TANIMSIZ_DEGER → GECERSIZ_DEGER`)
ayrı bir doğrulama kullanır; `bool`'un Python'da `int`'in alt sınıfı
olmasından kaynaklanan tuzağı önlemek için güvenilirlik/bakiye türü
`type(x) is int` ile kesin kontrol edilir.

### 2.4 Masaüstü uygulaması tasarımı

Arayüz, çekirdeği saran ve her çağrıyı günlükleyen bir `Oturum`
nesnesiyle (gözlemci deseni) kurulmuştur: durum değiştiren her çağrıdan
sonra `durum_degisti` sinyali yayılır ve takvim, kullanıcı paneli, üst bar
**kullanıcı bir şey yapmadan** kendini yeniler. Doküman GUI kütüphanesini
serbest bıraktığından, arayüz **HTML/CSS/JS ile çizilip native bir Qt
penceresine gömülmüştür** (`QWebEngineView`): Qt'nin stil dili (QSS) gerçek
`box-shadow`, gradyan ve yumuşak geçiş animasyonlarını desteklemediğinden,
bu seçim kayda değer bir görsel kalite farkı yaratmıştır. Mimari
bozulmamıştır — JavaScript hiçbir iş kuralı barındırmaz; bir `QWebChannel`
köprüsü (`arayuz/kopru.py`) üzerinden `Motor`'un **aynı** fonksiyonunu
çağırır ve aynı sonuç sözlüğünü JSON olarak geri alır. Tek pencere
içinde özel çizimli bir takvim (CSS Grid/mutlak konumlandırma tabanlı;
saat/çeyrek ızgarası, durum renkleri + ikon/desen kodlaması, hazırlık
şeritleri, "şimdi" çizgisi, geçmiş bölge karartması), canlı fiyat
önizlemeli bir talep formu, kullanıcı paneli ve JSON görünümlü bir olay
günlüğü bir arada bulunur. Arayüz **hiçbir iş kuralı barındırmaz**:
eylem düğmeleri duruma göre devre dışı bırakılmaz, saat alanları serbest
metin kabul eder, geçersiz bir talep gönderilebilir — red kodunu ve
Türkçe açıklamasını her zaman çekirdek üretir.

## 3. Deneysel Sonuçlar

| Test grubu | Sayı | Sonuç |
|---|---:|---|
| E-destek kabul senaryosu (19 komut) | 19/19 | alan alan birebir eşleşme |
| API eşdeğerlik testi (GUI fonksiyonları) | 19/19 | CLI ile birebir aynı |
| Özgün senaryolar (`testler/senaryolar/`) | 8 klasör, 110 komut | tümü geçti |
| GUI duman testi (`Oturum` üzerinden 19 işlem) | 3 | tümü geçti |
| Birim testleri (K1–K11 uç durumları) | 104 | tümü geçti |
| **Toplam (pytest)** | **117** | **117/117 geçti** |

Özgün senaryolar sırasıyla şunları hedefler: (01) bant sınırını aşan
talepler ve doluluk eşiğinin tam 0,25 sınırındaki davranışı; (02) bekleme
listesi sıralamasının güncel güvenilirliğe göre değişebilmesi ve bir
terfinin aynı taramadaki diğer kayıtları etkilemesi; (03) paketin altı
adımlı denetim sırasının tamamı; (04) haftalık sıfırlamanın bakiyeyi
*eklemek* değil *eşitlemek* olduğu ve bir iade kotanın üstüne taşarsa
kırpıldığı; (05) ekleme komutlarının 3 adımlı doğrulama sırası; (06)
giriş/çıkış/gelmeme/tamamlanma durum makinesi, giriş penceresinin iki
sınırı ve erken çıkışın bitişi güncellediği; (07) K10'un 13 adımının
her biri ve birden çok kural ihlal edildiğinde ilk adımın kodunun döndüğü;
(08) iptal iadesinin üç kademesi, `bekleme` komutunun tüm sonuçları ve
süresi geçen bekleme kaydının sessizce silindiği. Böylece dokümandaki
bütün hata kodları en az bir özgün senaryoda yer alır. Her
senaryonun beklenen değerleri elle hesaplanmış ve `ACIKLAMA.md`
dosyasında gerekçelendirilmiştir.

Ayrıca kodda tür/rol/kaynak adı sabiti bulunmadığı
(`grep -R "YAZICI\|OGRENCI" rezervasyon arayuz` boş döner) doğrulanmış;
bu, başlangıç dosyasındaki bir parametre (örn. `hazirlik_dk`,
`temel_ucret`, `haftalik_kota`) değiştiğinde sistemin kod değişikliği
gerektirmeden yeni kurala göre davranacağını garanti eder.

## 4. Tasarım Kararları

**Mimari.** "Her komut bir fonksiyon" ilkesi, dokümanın GUI–modül eşdeğerlik
şartını tasarım zamanında değil **test zamanında** kanıtlanabilir hale
getirir; bu, tek bir `calistir(dict)` dağıtıcısına her iki arayüzü de
bağlamaktan daha güvenlidir çünkü GUI'nin gerçekte hangi imzayla
çağırdığını doğrudan test eder.

**Fraction tercihi.** Ücret formülündeki ardışık çarpımlar (0,25 × 1,25 ×
1,5 gibi) `float` ile biriken yuvarlama hatasına açıktır; `Fraction`
kullanımı bu riski matematiksel olarak sıfırlar ve "doluluk tam 0,25 ise
çarpan 1,25'tir" gibi sınır durumlarını hatasız işler.

**İşlem kolaylığı.** Takvimde boş bir alana sürükleme, talep formunu
doldurur (kaynak, gün, 15 dakikaya hizalanmış başlangıç/bitiş); bir
rezervasyon kutusuna tıklamak popover'da Giriş/Çıkış/İptal eylemlerini
açar. Böylece sık yapılan bir işlem tek sürükleme + tek tıklamaya iner.

**Uğraştırmama.** Form varsayılanları (seçili kullanıcı, görüntülenen
gün, simüle saatten sonraki ilk 15 dakika adımı), yeni üye eklemede
bakiye varsayılanı olarak rol kotası, ve iptal düğmesinin yanında onay
penceresi yerine iade önizlemesi ("İptal · %50 iade: 4 KP") kullanılması
— bilgi onaydan daha değerlidir ilkesiyle — bu ölçütü doğrudan hedefler.

**Engellemeyen arayüz.** Eylem düğmelerinin duruma göre devre dışı
bırakılmaması bilinçli bir karardır: aksi hâlde GUI, K8 durum makinesini
*bilmek* zorunda kalır ve doküman bunu açıkça yasaklar. Bunun yerine
`DURUM_HATASI` gibi reddler, düğmenin hemen yanında Türkçe açıklamasıyla
gösterilir.

**Görsel kodlama.** Durumlar yalnızca renkle değil (ONAYLI mavi,
KULLANIMDA yeşil+▶, TAMAMLANDI gri+✓, IPTAL kesikli çerçeve+üstü çizili,
GELMEDI turuncu çapraz desen) ayrıca ikon ve desenle de kodlanır; bu,
renk körlüğüne karşı dayanıklılık sağlar ve görsel kalite ölçütüne
hizmet eder.

## 5. Sonuç

Proje, dokümanda tanımlanan on bir kural grubunun tamamını
parametreleştirilmiş, yalnızca standart kütüphane kullanan bir çekirdekte
uygulamış ve bunu hem CLI hem de PySide6 tabanlı bir masaüstü uygulaması
üzerinden **aynı kod yoluyla** sunmuştur. 19 komutluk kabul senaryosunun
birebir geçmesi ve sekiz özgün senaryo ile toplam 117 otomatik testin yeşil
olması, kural uygulamasının doğruluğuna güçlü bir kanıt sunar. Geliştirme
için öneriler: çoklu kullanıcı eşzamanlılığı (şu an tek iş parçacıklı
varsayılıyor), kalıcı depolama katmanı ve bekleme listesi için tahmini
atanma zamanı gösterimi.

## Kaynakça

1. Python Software Foundation, *Python 3.11 Documentation* — `fractions`,
   `datetime`, `dataclasses`, `enum` modülleri.
2. The Qt Company, *Qt for Python (PySide6) Documentation*.
3. J. Nielsen, "10 Usability Heuristics for User Interface Design,"
   Nielsen Norman Group, 1994.
4. IEEE, *IEEE Conference Proceedings Formatting Template*.
5. Kocaeli Üniversitesi Bilgisayar Mühendisliği Bölümü, *Yazılım
   Laboratuvarı I 2026–2027 Güz Proje I: Kampüs Kaynak Rezervasyon
   Sistemi* (proje dokümanı), 2026.
