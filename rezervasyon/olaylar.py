"""K8 — durum makinesi geçişleri (giris/cikis/iptal) ve K11 — saat ilerletme
olay motoru (Bölüm 9, PROJE_ANALIZI.md)."""
from __future__ import annotations

from datetime import datetime, timedelta

from . import bekleme, sabitler, zaman
from .depo import Depo
from .model import Durum


def _clamp(deger: int) -> int:
    return max(sabitler.GUVENILIRLIK_MIN, min(sabitler.GUVENILIRLIK_MAX, deger))


def giris(depo: Depo, rezervasyon_id: str) -> dict:
    r = depo.rezervasyonlar.get(rezervasyon_id)
    if r is None:
        return {"komut": "giris", "durum": "RED", "kod": "BULUNAMADI"}
    if r.durum != Durum.ONAYLI:
        return {"komut": "giris", "durum": "RED", "kod": "DURUM_HATASI"}
    pencere_alt = r.baslangic - timedelta(minutes=sabitler.GIRIS_PENCERESI_ONCE_DK)
    pencere_ust = r.baslangic + timedelta(minutes=sabitler.GIRIS_PENCERESI_SONRA_DK)
    if not (pencere_alt <= depo.saat <= pencere_ust):
        return {"komut": "giris", "durum": "RED", "kod": "GIRIS_PENCERESI_DISI"}
    r.durum = Durum.KULLANIMDA
    return {"komut": "giris", "durum": "TAMAM", "yeni_durum": r.durum.value}


def cikis(depo: Depo, rezervasyon_id: str) -> dict:
    r = depo.rezervasyonlar.get(rezervasyon_id)
    if r is None:
        return {"komut": "cikis", "durum": "RED", "kod": "BULUNAMADI"}
    if r.durum != Durum.KULLANIMDA:
        return {"komut": "cikis", "durum": "RED", "kod": "DURUM_HATASI"}
    r.bitis = depo.saat
    r.durum = Durum.TAMAMLANDI
    kullanici = depo.kullanicilar[r.kullanici]
    olaylar = bekleme.tara(depo, r.kaynak, depo.saat)
    return {
        "komut": "cikis",
        "durum": "TAMAM",
        "yeni_durum": r.durum.value,
        "guvenilirlik": kullanici.guvenilirlik,
        "olaylar": olaylar,
    }


def iptal(depo: Depo, rezervasyon_id: str) -> dict:
    r = depo.rezervasyonlar.get(rezervasyon_id)
    if r is None:
        return {"komut": "iptal", "durum": "RED", "kod": "BULUNAMADI"}
    if r.durum != Durum.ONAYLI:
        return {"komut": "iptal", "durum": "RED", "kod": "DURUM_HATASI"}

    kullanici = depo.kullanicilar[r.kullanici]
    rol = depo.roller[kullanici.rol]
    kalan = r.baslangic - depo.saat

    if kalan >= timedelta(hours=sabitler.IADE_TAM_SINIR_SAAT):
        hesaplanan_iade = r.ucret
        guv_delta = 0
    elif kalan >= timedelta(hours=sabitler.IADE_YARIM_SINIR_SAAT):
        hesaplanan_iade = r.ucret // 2
        guv_delta = 0
    else:
        hesaplanan_iade = 0
        guv_delta = sabitler.GUVENILIRLIK_GEC_IPTAL

    iade_eklenen = max(0, min(hesaplanan_iade, rol.haftalik_kota - kullanici.bakiye))
    kullanici.bakiye += iade_eklenen
    kullanici.guvenilirlik = _clamp(kullanici.guvenilirlik + guv_delta)
    r.durum = Durum.IPTAL

    olaylar = bekleme.tara(depo, r.kaynak, depo.saat)
    return {
        "komut": "iptal",
        "durum": "TAMAM",
        "iade": iade_eklenen,
        "bakiye": kullanici.bakiye,
        "guvenilirlik": kullanici.guvenilirlik,
        "olaylar": olaylar,
    }


# ---------------------------------------------------------------------------
# K11 — saat ilerletme
# ---------------------------------------------------------------------------

def _sonraki_olay_zamani(depo: Depo, sonra: datetime) -> datetime | None:
    adaylar: list[datetime] = [zaman.sonraki_pazartesi_gece_yarisi(sonra)]
    for r in depo.rezervasyonlar.values():
        if r.durum == Durum.KULLANIMDA and r.bitis > sonra:
            adaylar.append(r.bitis)
        if r.durum == Durum.ONAYLI:
            gelmedi_an = r.baslangic + timedelta(minutes=sabitler.GELMEDI_ESIK_DK)
            if gelmedi_an > sonra:
                adaylar.append(gelmedi_an)
    return min(adaylar) if adaylar else None


def saat(depo: Depo, yeni_zaman_str: str) -> dict:
    yeni = zaman.parse(yeni_zaman_str)
    if yeni < depo.saat:
        return {"komut": "saat", "durum": "RED", "kod": "SAAT_GERI"}

    olaylar: list[dict] = []

    while True:
        t = _sonraki_olay_zamani(depo, depo.saat)
        if t is None or t > yeni:
            break

        depo.saat = t
        bekleme.temizle(depo)

        if zaman.pazartesi_gece_yarisi_mi(t):
            for kullanici in depo.kullanicilar.values():
                rol = depo.roller[kullanici.rol]
                kullanici.bakiye = rol.haftalik_kota
            olaylar.append({"zaman": zaman.bicimle(t), "tur": "HAFTALIK_SIFIRLAMA"})

        tamamlananlar = sorted(
            (r for r in depo.rezervasyonlar.values() if r.durum == Durum.KULLANIMDA and r.bitis == t),
            key=lambda r: r.no,
        )
        for r in tamamlananlar:
            r.durum = Durum.TAMAMLANDI
            kullanici = depo.kullanicilar[r.kullanici]
            kullanici.guvenilirlik = _clamp(kullanici.guvenilirlik + sabitler.GUVENILIRLIK_TAMAMLANDI)
            olaylar.append(
                {
                    "zaman": zaman.bicimle(t),
                    "tur": "TAMAMLANDI",
                    "rezervasyon": r.id,
                    "kullanici": r.kullanici,
                    "guvenilirlik": kullanici.guvenilirlik,
                }
            )

        gelmeyenler = sorted(
            (
                r
                for r in depo.rezervasyonlar.values()
                if r.durum == Durum.ONAYLI
                and r.baslangic + timedelta(minutes=sabitler.GELMEDI_ESIK_DK) == t
            ),
            key=lambda r: r.no,
        )
        bosalan: list[str] = []
        for r in gelmeyenler:
            r.durum = Durum.GELMEDI
            kullanici = depo.kullanicilar[r.kullanici]
            kullanici.guvenilirlik = _clamp(kullanici.guvenilirlik + sabitler.GUVENILIRLIK_GELMEDI)
            olaylar.append(
                {
                    "zaman": zaman.bicimle(t),
                    "tur": "GELMEDI",
                    "rezervasyon": r.id,
                    "kullanici": r.kullanici,
                    "guvenilirlik": kullanici.guvenilirlik,
                }
            )
            if r.kaynak not in bosalan:
                bosalan.append(r.kaynak)

        for kaynak_id in bosalan:
            olaylar.extend(bekleme.tara(depo, kaynak_id, t))

    depo.saat = yeni
    bekleme.temizle(depo)
    return {"komut": "saat", "durum": "TAMAM", "olaylar": olaylar}
