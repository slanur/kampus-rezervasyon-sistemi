"""Zaman ayrıştırma/biçimlendirme ve aralık yardımcıları.

Tüm aralıklar yarı açıktır: [baslangic, bitis). Saat dilimi kullanılmaz,
naive datetime yeterlidir.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from . import sabitler


def parse(metin: str) -> datetime:
    return datetime.strptime(metin, sabitler.ZAMAN_BICIMI)


def bicimle(zaman: datetime) -> str:
    return zaman.strftime(sabitler.ZAMAN_BICIMI)


def gun_parse(metin: str) -> date:
    return datetime.strptime(metin, sabitler.GUN_BICIMI).date()


def on_besin_katı_mi(zaman: datetime) -> bool:
    return zaman.minute % sabitler.DILIM_DK == 0


def kesisir(b1: datetime, e1: datetime, b2: datetime, e2: datetime) -> bool:
    """Yarı açık [b, e) aralıkları kesişir mi?"""
    return b1 < e2 and e1 > b2


def calisma_saati_disinda_mi(baslangic: datetime, bitis: datetime) -> bool:
    cal_b = time(*sabitler.CALISMA_BASLANGIC)
    cal_e = time(*sabitler.CALISMA_BITIS)
    if baslangic.date() != bitis.date():
        return True
    if baslangic.time() < cal_b:
        return True
    if bitis.time() > cal_e:
        return True
    return False


def pazartesi_gece_yarisi_mi(zaman: datetime) -> bool:
    return zaman.weekday() == 0 and zaman.time() == time(0, 0)


def sonraki_pazartesi_gece_yarisi(simdiki: datetime) -> datetime:
    """`simdiki`den KESİNLİKLE SONRAKİ ilk Pazartesi 00:00'ı döndürür."""
    temel = datetime.combine(simdiki.date(), time(0, 0))
    gun_fark = (7 - simdiki.weekday()) % 7
    aday = temel + timedelta(days=gun_fark)
    if aday <= simdiki:
        aday += timedelta(days=7)
    return aday


def pik_mi(bant_baslangic_saat: int, bant_bitis_saat: int) -> bool:
    return (
        bant_baslangic_saat >= sabitler.PIK_BASLANGIC
        and bant_bitis_saat <= sabitler.PIK_BITIS
    )
