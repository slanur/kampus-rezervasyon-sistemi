"""JS ↔ Python köprüsü (QWebChannel).

Tek giriş noktası `cagir()`dır: JS tarafı `{"yontem": "...", "args": {...}}`
biçiminde bir JSON gönderir, köprü bunu `Oturum`'daki (veya durum
değiştirmeyen görünüm çağrıları için doğrudan `Motor`'daki) **aynı isimli
fonksiyona** yönlendirir ve sonucu JSON olarak döndürür.

Bu tasarım, Bölüm 8/12'deki "GUI, modülün ilgili fonksiyonunu çağırır"
ilkesini korur: JavaScript hiçbir iş kuralı barındırmaz, yalnızca hangi
komutun çağrılacağını bilir. Python tarafında tek bir jenerik dağıtıcı
vardır; her komutun kendi mantığı yine `rezervasyon/` çekirdeğindedir.
"""
from __future__ import annotations

import json

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QWidget

from .oturum import Oturum

# Yalnızca bu adlarla çağrı yapılabilir (JS'den keyfi Python nesnesi/
# fonksiyonu çağrılmasını engeller).
_IZINLI_YONTEMLER = {
    "saat",
    "rezervasyon",
    "paket",
    "fiyat",
    "iptal",
    "giris",
    "cikis",
    "bekleme",
    "kullanici_ekle",
    "kaynak_ekle",
    "geri_al",
    "simdi",
    "parametreler",
    "kullanicilar",
    "kaynaklar",
    "gun_gorunumu",
    "rezervasyon_detayi",
    "kullanici_bekleme_kayitlari",
    "hata_aciklamasi",
    "red_aciklamasi",
    "uygun_araliklar",
    "sonraki_olay_zamani",
    "iptal_onizleme",
}


class Kopru(QObject):
    durumDegisti = Signal()
    dosyaDegisti = Signal(str)

    def __init__(self, oturum: Oturum, pencere: QWidget, ilk_dosya: str | None = None) -> None:
        super().__init__()
        self._oturum = oturum
        self._pencere = pencere
        self._ilk_dosya = ilk_dosya or ""
        self._oturum.durum_degisti.connect(self.durumDegisti.emit)

    @Slot(result=str)
    def ilkDosya(self) -> str:
        """Başlangıçta `python -m arayuz baslangic.json` ile verilen yol.

        JS, QWebChannel bağlantısı KURULDUKTAN sonra bunu okuyup yükler;
        Python tarafında otomatik tetiklenmez — aksi halde sinyal, JS henüz
        dinlemeye başlamadan yayılabilir (yarış durumu).
        """
        return self._ilk_dosya

    # ------------------------------------------------------------------
    @Slot(str, result=str)
    def cagir(self, istek_json: str) -> str:
        try:
            istek = json.loads(istek_json)
            yontem = istek["yontem"]
            args = istek.get("args", {})
            if yontem not in _IZINLI_YONTEMLER:
                return json.dumps({"hata": f"izinsiz yöntem: {yontem}"})
            if not self._oturum.yuklu_mu():
                return json.dumps({"hata": "dosya yüklenmedi"})
            fn = getattr(self._oturum, yontem)
            sonuc = fn(**args)
            return json.dumps({"sonuc": sonuc})
        except Exception as exc:  # JS tarafını asla çökertme
            return json.dumps({"hata": str(exc)})

    @Slot(str, result=str)
    def kullaniciDetayi(self, id: str) -> str:
        """`sorgu_kullanici` ile aynı veriyi döndürür ama günlüğe YAZMAZ.

        Kullanıcı paneli her durum değişikliğinden sonra bunu çağırarak
        kendini yeniler; bu bir kullanıcı komutu değildir, bu yüzden
        olay günlüğünü kirletmemelidir (bkz. arayuz/oturum.py).
        """
        if not self._oturum.yuklu_mu():
            return json.dumps({"hata": "dosya yüklenmedi"})
        return json.dumps({"sonuc": self._oturum.motor.sorgu_kullanici(id)})

    @Slot(result=str)
    def gunluk(self) -> str:
        return json.dumps(self._oturum.gunluk)

    @Slot(result=bool)
    def yukluMu(self) -> bool:
        return self._oturum.yuklu_mu()

    @Slot(result=bool)
    def geriAlYapilabilir(self) -> bool:
        return self._oturum.geri_al_yapilabilir()

    # ------------------------------------------------------------------
    @Slot(result=str)
    def dosyaSec(self) -> str:
        yol, _ = QFileDialog.getOpenFileName(self._pencere, "Başlangıç dosyası seç", "", "JSON (*.json)")
        if not yol:
            return ""
        return self.dosyaYukle(yol)

    @Slot(str, result=str)
    def dosyaYukle(self, yol: str) -> str:
        try:
            self._oturum.dosya_yukle(yol)
        except Exception as exc:
            return json.dumps({"hata": str(exc)})
        import os

        self.dosyaDegisti.emit(os.path.basename(yol))
        return json.dumps({"sonuc": {"dosya": os.path.basename(yol), "yol": yol}})
