"""Bellekteki durum: parametreler, kaynaklar, kullanıcılar, rezervasyonlar,
bekleme kayıtları ve sayaçlar. Kalıcılık yok; her şey bu nesnede tutulur.
"""
from __future__ import annotations

from datetime import datetime

from .model import BakimPenceresi, BeklemeKaydi, Durum, Kaynak, KaynakTuru, Kullanici, Rezervasyon, Rol


class Depo:
    def __init__(self) -> None:
        self.saat: datetime | None = None
        self.turler: dict[str, KaynakTuru] = {}
        self.roller: dict[str, Rol] = {}
        self.kaynaklar: dict[str, Kaynak] = {}          # ekleme sırasıyla
        self.bakimlar: list[BakimPenceresi] = []
        self.kullanicilar: dict[str, Kullanici] = {}    # ekleme sırasıyla
        self.rezervasyonlar: dict[str, Rezervasyon] = {}
        self._kaynak_rez_index: dict[str, list[str]] = {}  # kaynak_id -> [rezervasyon_id,...]
        self.bekleme: dict[str, BeklemeKaydi] = {}
        self._r_sayac = 0
        self._p_sayac = 0
        self._b_sayac = 0

    # ---- sayaçlar -----------------------------------------------------
    def sonraki_r_no(self) -> int:
        self._r_sayac += 1
        return self._r_sayac

    def sonraki_p_id(self) -> str:
        self._p_sayac += 1
        return f"p{self._p_sayac}"

    def sonraki_b_no(self) -> int:
        self._b_sayac += 1
        return self._b_sayac

    # ---- sorgular -------------------------------------------------------
    def turdeki_kaynak_sayisi(self, tur: str) -> int:
        return sum(1 for k in self.kaynaklar.values() if k.tur == tur)

    def rezervasyonlar_for_kaynak(self, kaynak_id: str) -> list[Rezervasyon]:
        ids = self._kaynak_rez_index.get(kaynak_id, [])
        return [self.rezervasyonlar[i] for i in ids]

    def bakimlar_for(self, kaynak_id: str) -> list[BakimPenceresi]:
        return [b for b in self.bakimlar if b.kaynak == kaynak_id]

    # ---- değişiklik -------------------------------------------------------
    def yeni_rezervasyon(
        self,
        kullanici: str,
        kaynak: str,
        baslangic: datetime,
        bitis: datetime,
        ucret: int,
        paket: str | None = None,
    ) -> Rezervasyon:
        no = self.sonraki_r_no()
        rid = f"r{no}"
        r = Rezervasyon(
            id=rid,
            no=no,
            kullanici=kullanici,
            kaynak=kaynak,
            baslangic=baslangic,
            bitis=bitis,
            ucret=ucret,
            durum=Durum.ONAYLI,
            paket=paket,
        )
        self.rezervasyonlar[rid] = r
        self._kaynak_rez_index.setdefault(kaynak, []).append(rid)
        return r

    def yeni_bekleme(
        self,
        kullanici: str,
        kaynak: str,
        baslangic: datetime,
        bitis: datetime,
        kayit_saati: datetime,
    ) -> BeklemeKaydi:
        no = self.sonraki_b_no()
        bid = f"b{no}"
        kayit = BeklemeKaydi(
            id=bid,
            no=no,
            kullanici=kullanici,
            kaynak=kaynak,
            baslangic=baslangic,
            bitis=bitis,
            kayit_saati=kayit_saati,
        )
        self.bekleme[bid] = kayit
        return kayit

    def bekleme_for_kaynak(self, kaynak_id: str) -> list[BeklemeKaydi]:
        return [k for k in self.bekleme.values() if k.kaynak == kaynak_id]
