"""Hata kodu -> Türkçe açıklama sözlüğü (Bölüm 11)."""

ACIKLAMALAR: dict[str, str] = {
    "BULUNAMADI": "Kullanıcı, kaynak veya rezervasyon bulunamadı",
    "ZAMAN_ADIMI_HATASI": "Saatler 15 dakikalık adımlara oturmalı ve bitiş başlangıçtan sonra olmalı",
    "GECMIS_ZAMAN": "Başlangıç simüle saatten önce olamaz",
    "CALISMA_SAATI_DISI": "Rezervasyon aynı gün 08:00–22:00 arasında olmalı",
    "SURE_SINIRI": "Süre 30 dk ile rolün azami süresi arasında olmalı",
    "ILERI_TARIH_SINIRI": "Rolün ileri tarih sınırı aşıldı (güvenilirlik 50'nin altındaysa 1 gün)",
    "ROL_IZNI_YOK": "Rolünüz bu kaynağı rezerve edemez",
    "SERTIFIKA_YOK": "Bu kaynak türü için gerekli sertifika yok",
    "BAKIM": "Kaynak bu aralıkta bakımda",
    "KESISME": "Aralık başka bir rezervasyonla çakışıyor",
    "HAZIRLIK_IHLALI": "Kaynağın hazırlık (soğuma/havalandırma) süresi ihlal ediliyor",
    "ARDISIK_KULLANIM": "Aynı kaynaktaki rezervasyonlarınız arasında en az 60 dk olmalı",
    "BAKIYE_YETERSIZ": "Bakiye yetersiz",
    "PAKET_BOYUTU": "Paket 2–4 kalemden oluşmalı",
    "GUVENILIRLIK_DUSUK": "Güvenilirlik 50'nin altında olduğu için paket yapılamaz",
    "PAKET_RED": "Paketteki en az bir kalem geçersiz",
    "PAKET_ICI_KESISME": "Paketteki kalemler birbiriyle çakışıyor",
    "DURUM_HATASI": "Rezervasyon bu işlem için uygun durumda değil",
    "GIRIS_PENCERESI_DISI": "Giriş, başlangıçtan 10 dk önce ile 15 dk sonra arasında yapılabilir",
    "SAAT_GERI": "Saat geri alınamaz",
    "BEKLEME_GEREKSIZ": "Talep zaten geçerli; doğrudan rezervasyon yapabilirsiniz",
    "ID_MEVCUT": "Bu kimlikle bir kayıt zaten var",
    "TANIMSIZ_DEGER": "Rol, tür veya izinli rol başlangıç dosyasında tanımlı değil",
    "GECERSIZ_DEGER": "Bakiye 0 ile rol kotası arasında, güvenilirlik 0–100 arasında tam sayı olmalı",
    "GECERSIZ_KOMUT": "Komut biçimi geçersiz",
}


def aciklama(kod: str) -> str:
    return ACIKLAMALAR.get(kod, kod)
