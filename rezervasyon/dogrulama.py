"""K1–K4 ve K10 — rezervasyon talebinin 13 adımlı doğrulama zinciri.

Tek giriş noktası `dogrula()`dır. `rezervasyon`, `fiyat`, `paket` kalemleri,
`bekleme` ve otomatik atama hepsi bunu kullanır; yalnızca `bakiye_kontrol`
parametresi ve kullanılan `simdi` değişir (Bölüm 6, K10 tablosu).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import fiyat, sabitler, zaman
from .depo import Depo
from .model import Durum

_KESISME_DURUMLAR = (Durum.ONAYLI, Durum.KULLANIMDA)
_HAZIRLIK_DURUMLAR = (Durum.ONAYLI, Durum.KULLANIMDA, Durum.TAMAMLANDI)
_ARDISIK_DURUMLAR = (Durum.ONAYLI, Durum.KULLANIMDA, Durum.TAMAMLANDI)


def dogrula(
    depo: Depo,
    kullanici_id: str,
    kaynak_id: str,
    baslangic: datetime,
    bitis: datetime,
    simdi: datetime,
    bakiye_kontrol: bool,
) -> tuple[str | None, int | None]:
    """Dönüş: (kod, ucret). Geçerliyse kod None, ucret dolu olur."""

    # 1. BULUNAMADI
    kullanici = depo.kullanicilar.get(kullanici_id)
    kaynak = depo.kaynaklar.get(kaynak_id)
    if kullanici is None or kaynak is None:
        return "BULUNAMADI", None

    # 2. ZAMAN_ADIMI_HATASI
    if not zaman.on_besin_katı_mi(baslangic) or not zaman.on_besin_katı_mi(bitis) or bitis <= baslangic:
        return "ZAMAN_ADIMI_HATASI", None

    # 3. GECMIS_ZAMAN
    if baslangic < simdi:
        return "GECMIS_ZAMAN", None

    # 4. CALISMA_SAATI_DISI
    if zaman.calisma_saati_disinda_mi(baslangic, bitis):
        return "CALISMA_SAATI_DISI", None

    # 5. SURE_SINIRI
    rol = depo.roller[kullanici.rol]
    sure_dk = (bitis - baslangic).total_seconds() / 60
    if sure_dk < sabitler.ASGARI_SURE_DK or sure_dk > rol.azami_sure_dk:
        return "SURE_SINIRI", None

    # 6. ILERI_TARIH_SINIRI
    if baslangic > simdi + timedelta(hours=24 * ileri_gun_siniri(depo, kullanici)):
        return "ILERI_TARIH_SINIRI", None

    # 7. ROL_IZNI_YOK
    if kullanici.rol not in kaynak.izinli_roller:
        return "ROL_IZNI_YOK", None

    # 8. SERTIFIKA_YOK
    tur = depo.turler[kaynak.tur]
    if tur.sertifika and tur.sertifika not in kullanici.sertifikalar:
        return "SERTIFIKA_YOK", None

    # 9. BAKIM
    if kesisen_bakim(depo, kaynak_id, baslangic, bitis) is not None:
        return "BAKIM", None

    # 10. KESISME — önce TÜM rezervasyonlar için kesişme
    if kesisen_rezervasyon(depo, kaynak_id, baslangic, bitis) is not None:
        return "KESISME", None

    # 11. HAZIRLIK_IHLALI — sonra TÜM rezervasyonlar için hazırlık
    if hazirlik_ihlal_eden(depo, kaynak_id, baslangic, bitis) is not None:
        return "HAZIRLIK_IHLALI", None

    # 12. ARDISIK_KULLANIM
    if ardisik_ihlal_eden(depo, kullanici_id, kaynak_id, baslangic, bitis) is not None:
        return "ARDISIK_KULLANIM", None

    ucret = fiyat.hesapla(depo, kaynak_id, baslangic, bitis)

    # 13. BAKIYE_YETERSIZ
    if bakiye_kontrol and ucret > kullanici.bakiye:
        return "BAKIYE_YETERSIZ", None

    return None, ucret


# ---------------------------------------------------------------------------
# Adım 6 ve 9–12'nin koşulları. `dogrula()` yalnızca "ihlal var mı"ya bakar;
# görünüm katmanı aynı fonksiyonlarla ihlale yol açan kaydı bulup kullanıcıya
# gösterir — kural tek yerde kalır.
# ---------------------------------------------------------------------------

def ileri_gun_siniri(depo: Depo, kullanici) -> int:
    if kullanici.guvenilirlik < sabitler.GUVENILIRLIK_ESIK:
        return sabitler.ILERI_TARIH_DUSUK_GUVENILIRLIK_GUN
    return depo.roller[kullanici.rol].ileri_gun


def kesisen_bakim(depo: Depo, kaynak_id: str, baslangic: datetime, bitis: datetime):
    for bakim in depo.bakimlar_for(kaynak_id):
        if zaman.kesisir(baslangic, bitis, bakim.baslangic, bakim.bitis):
            return bakim
    return None


def kesisen_rezervasyon(depo: Depo, kaynak_id: str, baslangic: datetime, bitis: datetime):
    for r in depo.rezervasyonlar_for_kaynak(kaynak_id):
        if r.durum in _KESISME_DURUMLAR and zaman.kesisir(baslangic, bitis, r.baslangic, r.bitis):
            return r
    return None


def hazirlik_ihlal_eden(depo: Depo, kaynak_id: str, baslangic: datetime, bitis: datetime):
    h = timedelta(minutes=depo.turler[depo.kaynaklar[kaynak_id].tur].hazirlik_dk)
    for r in depo.rezervasyonlar_for_kaynak(kaynak_id):
        if r.durum in _HAZIRLIK_DURUMLAR and baslangic < r.bitis + h and bitis + h > r.baslangic:
            return r
    return None


def ardisik_ihlal_eden(depo: Depo, kullanici_id: str, kaynak_id: str, baslangic: datetime, bitis: datetime):
    bosluk = timedelta(minutes=sabitler.ARDISIK_BOSLUK_DK)
    for r in depo.rezervasyonlar_for_kaynak(kaynak_id):
        if (
            r.kullanici == kullanici_id
            and r.durum in _ARDISIK_DURUMLAR
            and baslangic < r.bitis + bosluk
            and bitis + bosluk > r.baslangic
        ):
            return r
    return None


# ---------------------------------------------------------------------------
# K10-ek — kullanıcı ve kaynak ekleme doğrulaması
# ---------------------------------------------------------------------------

def dogrula_kullanici_ekle(depo: Depo, id: str, rol: str, bakiye, guvenilirlik) -> str | None:
    if id in depo.kullanicilar:
        return "ID_MEVCUT"
    if rol not in depo.roller:
        return "TANIMSIZ_DEGER"
    rol_obj = depo.roller[rol]
    if type(bakiye) is not int or bakiye < 0 or bakiye > rol_obj.haftalik_kota:
        return "GECERSIZ_DEGER"
    if type(guvenilirlik) is not int or not (0 <= guvenilirlik <= 100):
        return "GECERSIZ_DEGER"
    return None


def dogrula_kaynak_ekle(depo: Depo, id: str, tur: str, izinli_roller) -> str | None:
    if id in depo.kaynaklar:
        return "ID_MEVCUT"
    if tur not in depo.turler:
        return "TANIMSIZ_DEGER"
    if any(rol not in depo.roller for rol in izinli_roller):
        return "TANIMSIZ_DEGER"
    return None
