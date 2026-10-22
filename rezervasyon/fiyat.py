"""K5 — ücretlendirme. Tüm hesap `Fraction` ile yapılır (kayan nokta yok)."""
from __future__ import annotations

import math
from datetime import datetime, time, timedelta
from fractions import Fraction

from . import sabitler
from .depo import Depo
from .model import Durum

_SAYILAN_DURUMLAR = (Durum.ONAYLI, Durum.KULLANIMDA)


def _dolu_dakika(depo: Depo, tur_adi: str, gun, bant_b: datetime, bant_e: datetime) -> tuple[int, int]:
    """(o bantta dolu dakika, türdeki kaynak sayısı) — doluluğun payı ve paydası."""
    dolu_dk = 0
    for kaynak in depo.kaynaklar.values():
        if kaynak.tur != tur_adi:
            continue
        for r in depo.rezervasyonlar_for_kaynak(kaynak.id):
            if r.durum not in _SAYILAN_DURUMLAR:
                continue
            if r.baslangic.date() != gun:
                continue
            ust = min(r.bitis, bant_e)
            alt = max(r.baslangic, bant_b)
            if ust > alt:
                dolu_dk += (ust - alt).total_seconds() / 60
    return int(round(dolu_dk)), depo.turdeki_kaynak_sayisi(tur_adi)


def bant_carpani(doluluk: Fraction) -> Fraction:
    return 1 + Fraction(math.floor(4 * doluluk), 4)


def bant_dokumu(depo: Depo, kaynak_id: str, baslangic: datetime, bitis: datetime) -> list[dict]:
    """Talebin kapladığı her bant için ücretin ara değerleri.

    `hesapla()` ücreti bu satırların toplamından üretir; böylece arayüzde
    gösterilen döküm ile gerçek ücret hiçbir zaman birbirinden ayrışmaz.
    """
    kaynak = depo.kaynaklar[kaynak_id]
    tur = depo.turler[kaynak.tur]
    gun = baslangic.date()
    satirlar = []

    for bant_bas_saat, bant_bit_saat in sabitler.BANTLAR:
        bant_b = datetime.combine(gun, time(bant_bas_saat, 0))
        bant_e = datetime.combine(gun, time(bant_bit_saat, 0))
        ust = min(bitis, bant_e)
        alt = max(baslangic, bant_b)
        if ust <= alt:
            continue
        dilim_sayisi = int((ust - alt).total_seconds() // (sabitler.DILIM_DK * 60))
        if dilim_sayisi <= 0:
            continue

        dolu_dk, kaynak_sayisi = _dolu_dakika(depo, kaynak.tur, gun, bant_b, bant_e)
        doluluk = Fraction(dolu_dk, kaynak_sayisi * 120) if kaynak_sayisi else Fraction(0)
        bant_carpan = bant_carpani(doluluk)

        pik = tur.enerji_yogun and zaman_pik_mi(bant_bas_saat, bant_bit_saat)
        pik_carpan = sabitler.PIK_CARPAN if pik else sabitler.NORMAL_CARPAN

        dilim_ucreti = Fraction(tur.temel_ucret) * Fraction(1, 4)
        satirlar.append({
            "bant_b": bant_b, "bant_e": bant_e, "alt": alt, "ust": ust,
            "dilim_sayisi": dilim_sayisi, "dilim_ucreti": dilim_ucreti,
            "dolu_dk": dolu_dk, "kaynak_sayisi": kaynak_sayisi, "doluluk": doluluk,
            "bant_carpan": bant_carpan, "pik": pik, "pik_carpan": pik_carpan,
            "tutar": dilim_ucreti * bant_carpan * pik_carpan * dilim_sayisi,
        })
    return satirlar


def yuvarla(toplam: Fraction) -> int:
    """En yakın tam sayı; tam 0,5 yukarı."""
    return math.floor(toplam + Fraction(1, 2))


def hesapla(depo: Depo, kaynak_id: str, baslangic: datetime, bitis: datetime) -> int:
    return yuvarla(sum((s["tutar"] for s in bant_dokumu(depo, kaynak_id, baslangic, bitis)), Fraction(0)))


def zaman_pik_mi(bant_bas_saat: int, bant_bit_saat: int) -> bool:
    return bant_bas_saat >= sabitler.PIK_BASLANGIC and bant_bit_saat <= sabitler.PIK_BITIS
