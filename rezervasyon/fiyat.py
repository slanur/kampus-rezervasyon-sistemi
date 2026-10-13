"""K5 — ücretlendirme. Tüm hesap `Fraction` ile yapılır (kayan nokta yok)."""
from __future__ import annotations

import math
from datetime import datetime, time, timedelta
from fractions import Fraction

from . import sabitler
from .depo import Depo
from .model import Durum

_SAYILAN_DURUMLAR = (Durum.ONAYLI, Durum.KULLANIMDA)


def _doluluk(depo: Depo, tur_adi: str, gun, bant_b: datetime, bant_e: datetime) -> Fraction:
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
    sayi = depo.turdeki_kaynak_sayisi(tur_adi)
    if sayi == 0:
        return Fraction(0)
    return Fraction(int(round(dolu_dk)), sayi * 120)


def hesapla(depo: Depo, kaynak_id: str, baslangic: datetime, bitis: datetime) -> int:
    kaynak = depo.kaynaklar[kaynak_id]
    tur = depo.turler[kaynak.tur]
    gun = baslangic.date()
    toplam = Fraction(0)

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

        doluluk = _doluluk(depo, kaynak.tur, gun, bant_b, bant_e)
        bant_carpan = 1 + Fraction(math.floor(4 * doluluk), 4)

        pik = tur.enerji_yogun and zaman_pik_mi(bant_bas_saat, bant_bit_saat)
        pik_carpan = sabitler.PIK_CARPAN if pik else sabitler.NORMAL_CARPAN

        toplam += Fraction(tur.temel_ucret) * Fraction(1, 4) * bant_carpan * pik_carpan * dilim_sayisi

    return math.floor(toplam + Fraction(1, 2))


def zaman_pik_mi(bant_bas_saat: int, bant_bit_saat: int) -> bool:
    return bant_bas_saat >= sabitler.PIK_BASLANGIC and bant_bit_saat <= sabitler.PIK_BITIS
