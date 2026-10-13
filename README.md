# Kampüs Kaynak Rezervasyon Sistemi

Kocaeli Üniversitesi Bilgisayar Mühendisliği — Yazılım Laboratuvarı I,
2026–2027 Güz, Proje I.

İki bileşenden oluşur:

- **`rezervasyon/`** — arayüzden bağımsız, yalnızca **standart kütüphane**
  kullanan çekirdek modül. Bir başlangıç dosyası ve bir komut dosyası
  (JSON Lines) okur, her komut için bir sonuç satırı üretir.
- **`arayuz/`** — aynı çekirdeği doğrudan fonksiyon çağrılarıyla kullanan
  **PySide6** masaüstü uygulaması.

Kuralların ayrıntılı analizi için [`PROJE_ANALIZI.md`](PROJE_ANALIZI.md)
dosyasına bakınız.

## Gereksinimler

- Python **3.11+**
- Çekirdek modül için ek bağımlılık yoktur.
- Masaüstü uygulaması için yalnızca `PySide6` gerekir.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # yalnızca arayüz için gereklidir
```

## Komut satırından çalıştırma

```bash
./calistir.sh baslangic.json komutlar.jsonl > sonuclar.jsonl
```

Windows:

```bat
calistir.bat baslangic.json komutlar.jsonl > sonuclar.jsonl
```

Betikler çağrıldığı dizine göre yol çözer (`cd` yapmaz) ve çıktıyı
UTF-8 olarak, `ensure_ascii=False` ile üretir. Örnek:

```bash
./calistir.sh testler/ornek/baslangic.json testler/ornek/komutlar.jsonl
```

Doğrudan modül olarak da çalıştırılabilir:

```bash
python3 -m rezervasyon baslangic.json komutlar.jsonl
```

## Masaüstü uygulamasını çalıştırma

```bash
pip install -r requirements.txt
./arayuz.sh                      # veya: ./arayuz.sh baslangic.json
```

Windows: `arayuz.bat`

Açılışta bir başlangıç dosyası seçilir; "Dosya değiştir" ile her an yeni
bir dosyayla sıfırdan kurulum yapılabilir. Uygulama komut dosyası okumaz,
sonuç dosyası yazmaz — tüm veriler yalnızca bellekte tutulur.

## Testler

```bash
pip install pytest
python3 -m pytest
```

Test katmanları:

| Katman | Yer | Açıklama |
|---|---|---|
| Kabul testi | `testler/ornek/` | E-destek örneğindeki 19 komutluk senaryo; `beklenen.jsonl` ile alan alan karşılaştırılır. |
| API eşdeğerlik | `testler/test_api_esdegerlik.py` | Aynı 19 işlem, GUI'nin çağıracağı `Motor` fonksiyonlarıyla (CLI dağıtıcısı kullanılmadan) tekrarlanır. |
| Kendi senaryolarımız | `testler/senaryolar/*/` | Her klasörde `baslangic.json`, `komutlar.jsonl`, elle hesaplanmış `beklenen.jsonl` ve gerekçesini anlatan `ACIKLAMA.md` bulunur. |
| Birim testleri | `testler/test_*.py` | `dogrulama`, `fiyat`, `olaylar`, `bekleme`, `paket`, `gorunum` modüllerinin uç durumları. |

Tek bir sonucu elle karşılaştırmak için:

```bash
python3 testler/karsilastir.py testler/ornek/beklenen.jsonl sonuclar.jsonl
```

## Proje dizin yapısı

```
yazlab/
├── calistir.sh / calistir.bat   # CLI çalıştırma betikleri
├── arayuz.sh / arayuz.bat       # masaüstü uygulamasını başlatır
├── requirements.txt             # yalnızca GUI için (PySide6)
├── rezervasyon/                 # çekirdek — yalnızca stdlib
│   ├── sabitler.py               # doküman sabitleri (15dk adım, 08-22, vb.)
│   ├── zaman.py                  # ayrıştırma/biçimlendirme, aralık yardımcıları
│   ├── model.py                  # dataclass'lar, Durum enum
│   ├── yukleyici.py              # baslangic.json → Depo
│   ├── depo.py                   # bellekteki durum, sayaçlar, dinamik tür sayısı
│   ├── dogrulama.py              # K1–K4, K10 + ekleme doğrulaması
│   ├── fiyat.py                  # K5 (Fraction ile kesin aritmetik)
│   ├── bekleme.py                # K9 — bekleme listesi
│   ├── olaylar.py                # K8 durum geçişleri + K11 olay motoru
│   ├── paket.py                  # K7 — paket rezervasyon
│   ├── gorunum.py                # salt okunur görünüm API'si (GUI için)
│   ├── motor.py                  # komut fonksiyonları + calistir() dağıtıcısı
│   ├── hata_kodlari.py           # hata kodu → Türkçe açıklama
│   └── cli.py                    # komut satırı arayüzü
├── arayuz/                      # masaüstü — PySide6 + QWebEngineView
│   ├── oturum.py                  # Motor'u sarar, günlük tutar, undo
│   ├── ana_pencere.py             # QMainWindow: tek bir QWebEngineView barındırır
│   ├── kopru.py                   # QWebChannel köprüsü — JS, Motor fonksiyonlarını bu üzerinden çağırır
│   └── web/                       # arayüzün tamamı HTML/CSS/JS ile çizilir
│       ├── index.html
│       ├── css/stil.css           # tasarım sistemi (OKLCH renk tokenları, gerçek gölge/gradient/geçiş)
│       ├── fonts/                 # Space Grotesk + JetBrains Mono (OFL, yerel — internet gerekmez)
│       └── js/
│           ├── kopru.js           # QWebChannel'ı Promise tabanlı API'ye sarar
│           ├── takvim.js          # takvim çizimi, hit-test, sürükleyerek talep
│           ├── uygulama.js        # durum yönetimi, paneller, formlar, kısayollar
│           └── qwebchannel.js     # Qt'nin JS köprü kütüphanesi (üretilmiş, dokunulmaz)
├── testler/
│   ├── ornek/                    # e-destek örneği (19 komut)
│   ├── senaryolar/                # kendi senaryolarımız
│   ├── karsilastir.py             # alan alan karşılaştırıcı
│   └── test_*.py
└── PROJE_ANALIZI.md             # teknik analiz ve uygulama planı
```

## Tasarım ilkeleri

- **Görsel tasarım kaynağı:** Arayüzün renk paleti (OKLCH tabanlı), tipografisi
  (Space Grotesk + JetBrains Mono) ve bileşen dili, kullanıcının Lovable ile
  tasarladığı [calendar-clock-spark](https://github.com/slanur/calendar-clock-spark)
  prototipinden (React + Tailwind v4 + shadcn/ui) uyarlanmıştır. Burada aynı
  görsel dil, derleme adımı gerektirmeyen düz HTML/CSS/JS olarak yeniden
  üretilmiştir; iş mantığı o prototipin `engine.ts` dosyasından DEĞİL, her
  zaman gerçek `rezervasyon/` Python çekirdeğinden gelir.
- **Her komut bir public modül fonksiyonudur** (`Motor.rezervasyon()`,
  `Motor.kullanici_ekle()`, vb.). `Motor.calistir(dict)` yalnızca CLI için
  bir dağıtıcıdır; GUI bu fonksiyonları doğrudan çağırır, böylece iki yol
  da aynı kodu çalıştırır.
- **Arayüz HTML/CSS/JS ile çizilir, native bir pencere içinde** (PySide6
  `QWebEngineView`). Doküman GUI kütüphanesini serbest bırakıyor; bu seçim
  Qt'nin stil dilinin (QSS) sunamadığı gerçek gölge/gradient/geçişleri
  mümkün kılar. Mimari bozulmaz: JavaScript hiçbir iş kuralı barındırmaz,
  yalnızca `QWebChannel` köprüsü (`arayuz/kopru.py`) üzerinden `Motor`'un
  ilgili fonksiyonunu çağırır — aynı Python kodu, aynı sonuç sözlüğü.
- **Parametre sabitlenmez.** Tür adları, roller, kotalar, ücretler ve
  hazırlık süreleri başlangıç dosyasından ya da `*_ekle` komutlarından
  gelir; kodda `"YAZICI"` gibi bir sabit bulunmaz.
- **Kesin aritmetik.** Ücret hesabı `fractions.Fraction` ile yapılır;
  kayan nokta hatası oluşmaz.
- **Salt okunur görünüm API'si.** GUI'nin ihtiyaç duyduğu tüm türetilmiş
  veri (alt satır yerleşimi, hazırlık şeritleri, iptal önizlemesi) çekirdekte
  hesaplanır; GUI yalnızca çizer, iş kuralı barındırmaz.
- **Arayüz hiçbir talebi engellemez.** Geçersiz bir talep de gönderilebilir;
  reddi ve kodunu modül verir.
