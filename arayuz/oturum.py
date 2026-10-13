"""`Motor`'u sararak GUI için gözlemci (observer) deseni sağlar.

Her çağrıda (komut_dict, sonuc_dict) günlüğe eklenir; durum değiştiren
çağrılardan sonra `durum_degisti` sinyali yayılır (Bölüm 13.5,
PROJE_ANALIZI.md). Bu sınıf hesap yapmaz; yalnızca Motor'u çağırır,
günlükler ve geri alma (undo) için çağrı geçmişi tutar.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from rezervasyon.motor import Motor


class Oturum(QObject):
    durum_degisti = Signal()
    dosya_degisti = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.motor: Motor | None = None
        self.dosya_yolu: str | None = None
        self.gunluk: list[dict] = []
        self._replay: list[tuple[str, dict]] = []

    # ------------------------------------------------------------------
    # Dosya
    # ------------------------------------------------------------------
    def dosya_yukle(self, yol: str) -> None:
        self.motor = Motor.dosyadan(yol)
        self.dosya_yolu = yol
        self.gunluk = []
        self._replay = []
        self.dosya_degisti.emit()
        self.durum_degisti.emit()

    def yuklu_mu(self) -> bool:
        return self.motor is not None

    # ------------------------------------------------------------------
    def _kaydet(self, komut: dict, sonuc: dict, degistirir: bool) -> dict:
        self.gunluk.append({"no": len(self.gunluk) + 1, "komut": komut, "sonuc": sonuc})
        if degistirir:
            self._replay.append((komut["komut"], komut))
            self.durum_degisti.emit()
        return sonuc

    # ------------------------------------------------------------------
    # Komutlar — her biri Motor'un ilgili fonksiyonunu çağırır
    # ------------------------------------------------------------------
    def saat(self, zaman: str) -> dict:
        komut = {"komut": "saat", "zaman": zaman}
        return self._kaydet(komut, self.motor.saat(zaman), True)

    def rezervasyon(self, kullanici: str, kaynak: str, baslangic: str, bitis: str) -> dict:
        komut = {"komut": "rezervasyon", "kullanici": kullanici, "kaynak": kaynak, "baslangic": baslangic, "bitis": bitis}
        return self._kaydet(komut, self.motor.rezervasyon(kullanici, kaynak, baslangic, bitis), True)

    def paket(self, kullanici: str, kalemler: list[dict]) -> dict:
        komut = {"komut": "paket", "kullanici": kullanici, "kalemler": kalemler}
        return self._kaydet(komut, self.motor.paket(kullanici, kalemler), True)

    def fiyat(self, kullanici: str, kaynak: str, baslangic: str, bitis: str) -> dict:
        komut = {"komut": "fiyat", "kullanici": kullanici, "kaynak": kaynak, "baslangic": baslangic, "bitis": bitis}
        return self._kaydet(komut, self.motor.fiyat(kullanici, kaynak, baslangic, bitis), False)

    def iptal(self, rezervasyon: str) -> dict:
        komut = {"komut": "iptal", "rezervasyon": rezervasyon}
        return self._kaydet(komut, self.motor.iptal(rezervasyon), True)

    def giris(self, rezervasyon: str) -> dict:
        komut = {"komut": "giris", "rezervasyon": rezervasyon}
        return self._kaydet(komut, self.motor.giris(rezervasyon), True)

    def cikis(self, rezervasyon: str) -> dict:
        komut = {"komut": "cikis", "rezervasyon": rezervasyon}
        return self._kaydet(komut, self.motor.cikis(rezervasyon), True)

    def bekleme(self, kullanici: str, kaynak: str, baslangic: str, bitis: str) -> dict:
        komut = {"komut": "bekleme", "kullanici": kullanici, "kaynak": kaynak, "baslangic": baslangic, "bitis": bitis}
        return self._kaydet(komut, self.motor.bekleme(kullanici, kaynak, baslangic, bitis), True)

    def sorgu_kullanici(self, id: str) -> dict:
        komut = {"komut": "sorgu", "tur": "kullanici", "id": id}
        return self._kaydet(komut, self.motor.sorgu_kullanici(id), False)

    def sorgu_kaynak(self, id: str, gun: str) -> dict:
        komut = {"komut": "sorgu", "tur": "kaynak", "id": id, "gun": gun}
        return self._kaydet(komut, self.motor.sorgu_kaynak(id, gun), False)

    def kullanici_ekle(self, id: str, ad: str, rol: str, sertifikalar: list[str], bakiye, guvenilirlik) -> dict:
        komut = {
            "komut": "kullanici_ekle",
            "id": id,
            "ad": ad,
            "rol": rol,
            "sertifikalar": sertifikalar,
            "bakiye": bakiye,
            "guvenilirlik": guvenilirlik,
        }
        return self._kaydet(komut, self.motor.kullanici_ekle(id, ad, rol, sertifikalar, bakiye, guvenilirlik), True)

    def kaynak_ekle(self, id: str, ad: str, tur: str, izinli_roller: list[str]) -> dict:
        komut = {"komut": "kaynak_ekle", "id": id, "ad": ad, "tur": tur, "izinli_roller": izinli_roller}
        return self._kaydet(komut, self.motor.kaynak_ekle(id, ad, tur, izinli_roller), True)

    # ------------------------------------------------------------------
    # Geri al (undo, P2) — başlangıç dosyasından yeniden kurup son durum
    # değiştiren işlem hariç tüm çağrıları tekrar oynatır.
    # ------------------------------------------------------------------
    def geri_al_yapilabilir(self) -> bool:
        return bool(self._replay) and self.dosya_yolu is not None

    def geri_al(self) -> None:
        if not self.geri_al_yapilabilir():
            return
        self._replay.pop()
        tekrar = list(self._replay)
        self.motor = Motor.dosyadan(self.dosya_yolu)
        self.gunluk = []
        self._replay = []
        for _, komut in tekrar:
            fn = getattr(self, komut["komut"])
            kwargs = {k: v for k, v in komut.items() if k != "komut"}
            fn(**kwargs)
        self.durum_degisti.emit()

    # ------------------------------------------------------------------
    # Görünüm API'si — doğrudan motora yönlendirilir (salt okunur)
    # ------------------------------------------------------------------
    def __getattr__(self, ad: str):
        motor = self.__dict__.get("motor")
        if motor is None:
            raise AttributeError(ad)
        return getattr(motor, ad)
