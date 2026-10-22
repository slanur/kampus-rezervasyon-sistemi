"""Motor — her komut için bir public fonksiyon (Bölüm 8.1).

GUI bu fonksiyonları doğrudan çağırır. `calistir()` yalnızca CLI için bir
dağıtıcıdır; iş kuralı barındırmaz.
"""
from __future__ import annotations

from . import dogrulama, gorunum, olaylar, paket as paket_mod, zaman
from .bekleme import bekleme_ac
from .depo import Depo
from .model import Kaynak, Kullanici
from .yukleyici import yukle


class Motor:
    def __init__(self, depo: Depo) -> None:
        self.depo = depo

    @classmethod
    def dosyadan(cls, yol: str) -> "Motor":
        return cls(yukle(yol))

    # ------------------------------------------------------------------
    # Komut fonksiyonları (durum değiştirebilir)
    # ------------------------------------------------------------------

    def saat(self, zaman: str) -> dict:
        return olaylar.saat(self.depo, zaman)

    def rezervasyon(self, kullanici: str, kaynak: str, baslangic: str, bitis: str) -> dict:
        b = _p(baslangic)
        e = _p(bitis)
        kod, ucret = dogrulama.dogrula(self.depo, kullanici, kaynak, b, e, self.depo.saat, bakiye_kontrol=True)
        if kod is not None:
            return {"komut": "rezervasyon", "durum": "RED", "kod": kod}
        r = self.depo.yeni_rezervasyon(kullanici, kaynak, b, e, ucret)
        u = self.depo.kullanicilar[kullanici]
        u.bakiye -= ucret
        return {"komut": "rezervasyon", "durum": "TAMAM", "rezervasyon_id": r.id, "ucret": ucret, "bakiye": u.bakiye}

    def paket(self, kullanici: str, kalemler: list[dict]) -> dict:
        return paket_mod.paket(self.depo, kullanici, kalemler)

    def fiyat(self, kullanici: str, kaynak: str, baslangic: str, bitis: str) -> dict:
        b = _p(baslangic)
        e = _p(bitis)
        kod, ucret = dogrulama.dogrula(self.depo, kullanici, kaynak, b, e, self.depo.saat, bakiye_kontrol=False)
        if kod is not None:
            return {"komut": "fiyat", "durum": "RED", "kod": kod}
        return {"komut": "fiyat", "durum": "TAMAM", "ucret": ucret}

    def iptal(self, rezervasyon: str) -> dict:
        return olaylar.iptal(self.depo, rezervasyon)

    def giris(self, rezervasyon: str) -> dict:
        return olaylar.giris(self.depo, rezervasyon)

    def cikis(self, rezervasyon: str) -> dict:
        return olaylar.cikis(self.depo, rezervasyon)

    def bekleme(self, kullanici: str, kaynak: str, baslangic: str, bitis: str) -> dict:
        return bekleme_ac(self.depo, kullanici, kaynak, _p(baslangic), _p(bitis))

    def sorgu_kullanici(self, id: str) -> dict:
        u = self.depo.kullanicilar.get(id)
        if u is None:
            return {"komut": "sorgu", "durum": "RED", "kod": "BULUNAMADI"}
        rezlar = sorted(
            (r for r in self.depo.rezervasyonlar.values() if r.kullanici == id),
            key=lambda r: (r.baslangic, r.no),
        )
        rez_out = [
            {
                "id": r.id,
                "kaynak": r.kaynak,
                "baslangic": zaman.bicimle(r.baslangic),
                "bitis": zaman.bicimle(r.bitis),
                "durum": r.durum.value,
                "ucret": r.ucret,
            }
            for r in rezlar
        ]
        return {
            "komut": "sorgu",
            "durum": "TAMAM",
            "bakiye": u.bakiye,
            "guvenilirlik": u.guvenilirlik,
            "rezervasyonlar": rez_out,
        }

    def sorgu_kaynak(self, id: str, gun: str) -> dict:
        k = self.depo.kaynaklar.get(id)
        if k is None:
            return {"komut": "sorgu", "durum": "RED", "kod": "BULUNAMADI"}
        gun_date = zaman.gun_parse(gun)

        from datetime import datetime, timedelta
        gun_baslangic = datetime.combine(gun_date, datetime.min.time())
        gun_bitis = gun_baslangic + timedelta(days=1)

        ogeler = []
        for bak in self.depo.bakimlar_for(id):
            if zaman.kesisir(bak.baslangic, bak.bitis, gun_baslangic, gun_bitis):
                ogeler.append(
                    (zaman.bicimle(bak.baslangic), 0, 0, {
                        "baslangic": zaman.bicimle(bak.baslangic),
                        "bitis": zaman.bicimle(bak.bitis),
                        "tur": "BAKIM",
                    })
                )
        from .model import Durum
        for r in self.depo.rezervasyonlar_for_kaynak(id):
            if r.durum in (Durum.ONAYLI, Durum.KULLANIMDA) and r.baslangic.date() == gun_date:
                ogeler.append(
                    (zaman.bicimle(r.baslangic), 1, r.no, {
                        "baslangic": zaman.bicimle(r.baslangic),
                        "bitis": zaman.bicimle(r.bitis),
                        "tur": "REZERVASYON",
                        "rezervasyon": r.id,
                    })
                )
        ogeler.sort(key=lambda t: (t[0], t[1], t[2]))
        return {"komut": "sorgu", "durum": "TAMAM", "doluluk": [o[3] for o in ogeler]}

    def kullanici_ekle(self, id: str, ad: str, rol: str, sertifikalar: list[str], bakiye, guvenilirlik) -> dict:
        kod = dogrulama.dogrula_kullanici_ekle(self.depo, id, rol, bakiye, guvenilirlik)
        if kod is not None:
            return {"komut": "kullanici_ekle", "durum": "RED", "kod": kod}
        self.depo.kullanicilar[id] = Kullanici(
            id=id, ad=ad, rol=rol, sertifikalar=tuple(sertifikalar), bakiye=bakiye, guvenilirlik=guvenilirlik
        )
        return {"komut": "kullanici_ekle", "durum": "TAMAM"}

    def kaynak_ekle(self, id: str, ad: str, tur: str, izinli_roller: list[str]) -> dict:
        kod = dogrulama.dogrula_kaynak_ekle(self.depo, id, tur, izinli_roller)
        if kod is not None:
            return {"komut": "kaynak_ekle", "durum": "RED", "kod": kod}
        self.depo.kaynaklar[id] = Kaynak(id=id, ad=ad, tur=tur, izinli_roller=tuple(izinli_roller))
        return {"komut": "kaynak_ekle", "durum": "TAMAM"}

    # ------------------------------------------------------------------
    # Dağıtıcı (CLI için)
    # ------------------------------------------------------------------

    def calistir(self, komut: dict) -> dict:
        ad = komut.get("komut") if isinstance(komut, dict) else None
        try:
            if ad == "saat":
                return self.saat(komut["zaman"])
            if ad == "rezervasyon":
                return self.rezervasyon(komut["kullanici"], komut["kaynak"], komut["baslangic"], komut["bitis"])
            if ad == "paket":
                return self.paket(komut["kullanici"], komut["kalemler"])
            if ad == "fiyat":
                return self.fiyat(komut["kullanici"], komut["kaynak"], komut["baslangic"], komut["bitis"])
            if ad == "iptal":
                return self.iptal(komut["rezervasyon"])
            if ad == "giris":
                return self.giris(komut["rezervasyon"])
            if ad == "cikis":
                return self.cikis(komut["rezervasyon"])
            if ad == "bekleme":
                return self.bekleme(komut["kullanici"], komut["kaynak"], komut["baslangic"], komut["bitis"])
            if ad == "sorgu":
                tur = komut["tur"]
                if tur == "kullanici":
                    return self.sorgu_kullanici(komut["id"])
                if tur == "kaynak":
                    return self.sorgu_kaynak(komut["id"], komut["gun"])
                return {"komut": "sorgu", "durum": "RED", "kod": "GECERSIZ_KOMUT"}
            if ad == "kullanici_ekle":
                return self.kullanici_ekle(
                    komut["id"],
                    komut["ad"],
                    komut["rol"],
                    komut.get("sertifikalar", []),
                    komut["bakiye"],
                    komut["guvenilirlik"],
                )
            if ad == "kaynak_ekle":
                return self.kaynak_ekle(komut["id"], komut["ad"], komut["tur"], komut.get("izinli_roller", []))
        except (KeyError, TypeError, ValueError, AttributeError):
            return {"komut": ad, "durum": "RED", "kod": "GECERSIZ_KOMUT"}

        return {"komut": ad, "durum": "RED", "kod": "GECERSIZ_KOMUT"}

    # ------------------------------------------------------------------
    # Görünüm API'si (salt okunur, GUI için)
    # ------------------------------------------------------------------

    def simdi(self) -> str:
        return gorunum.simdi(self.depo)

    def parametreler(self) -> dict:
        return gorunum.parametreler(self.depo)

    def kullanicilar(self) -> list[dict]:
        return gorunum.kullanicilar(self.depo)

    def kaynaklar(self) -> list[dict]:
        return gorunum.kaynaklar(self.depo)

    def gun_gorunumu(self, gun: str) -> dict:
        return gorunum.gun_gorunumu(self.depo, gun)

    def rezervasyon_detayi(self, id: str) -> dict | None:
        return gorunum.rezervasyon_detayi(self.depo, id)

    def kullanici_bekleme_kayitlari(self, id: str) -> list[dict]:
        return gorunum.kullanici_bekleme_kayitlari(self.depo, id)

    def hata_aciklamasi(self, kod: str) -> str:
        return gorunum.hata_aciklamasi(kod)

    def red_aciklamasi(self, kullanici: str, kaynak: str, baslangic: str, bitis: str, kod: str) -> str:
        return gorunum.red_aciklamasi(self.depo, kullanici, kaynak, baslangic, bitis, kod)

    def uygun_araliklar(self, kullanici: str, kaynak: str, baslangic: str, bitis: str, adet: int = 3) -> dict:
        return gorunum.uygun_araliklar(self.depo, kullanici, kaynak, baslangic, bitis, adet)

    def sonraki_olay_zamani(self) -> str | None:
        return gorunum.sonraki_olay_zamani(self.depo)

    def ucret_dokumu(self, kullanici: str, kaynak: str, baslangic: str, bitis: str) -> dict:
        return gorunum.ucret_dokumu(self.depo, kullanici, kaynak, baslangic, bitis)

    def doluluk_seridi(self, gun: str) -> dict:
        return gorunum.doluluk_seridi(self.depo, gun)

    def ekleme_aciklamasi(self, kod: str, komut: dict) -> str:
        return gorunum.ekleme_aciklamasi(self.depo, kod, komut)

    def iptal_onizleme(self, id: str) -> dict | None:
        return gorunum.iptal_onizleme(self.depo, id)


def _p(metin: str):
    return zaman.parse(metin)
