"""K7 — paket rezervasyon. Atomik: ya tüm kalemler alınır ya da hiçbiri."""
from __future__ import annotations

from datetime import datetime

from . import dogrulama, sabitler, zaman
from .depo import Depo


def _ici_kesisme_var_mi(depo: Depo, dogrulanan: list[dict]) -> bool:
    for i in range(len(dogrulanan)):
        for j in range(i + 1, len(dogrulanan)):
            x, y = dogrulanan[i], dogrulanan[j]
            if x["kaynak"] != y["kaynak"]:
                continue
            tur = depo.turler[depo.kaynaklar[x["kaynak"]].tur]
            h = tur.hazirlik_dk
            hazirlik_ihlal = (
                x["baslangic"] < y["bitis"] + _td(h) and x["bitis"] + _td(h) > y["baslangic"]
            )
            ardisik_ihlal = (
                x["baslangic"] < y["bitis"] + _td(sabitler.ARDISIK_BOSLUK_DK)
                and x["bitis"] + _td(sabitler.ARDISIK_BOSLUK_DK) > y["baslangic"]
            )
            if hazirlik_ihlal or ardisik_ihlal:
                return True
    return False


def _td(dakika: int):
    from datetime import timedelta
    return timedelta(minutes=dakika)


def paket(depo: Depo, kullanici_id: str, kalemler: list[dict]) -> dict:
    # 1. BULUNAMADI
    kullanici = depo.kullanicilar.get(kullanici_id)
    if kullanici is None:
        return {"komut": "paket", "durum": "RED", "kod": "BULUNAMADI", "kalemler": []}

    # 2. PAKET_BOYUTU
    if not (sabitler.PAKET_MIN_KALEM <= len(kalemler) <= sabitler.PAKET_MAX_KALEM):
        return {"komut": "paket", "durum": "RED", "kod": "PAKET_BOYUTU", "kalemler": []}

    # 3. GUVENILIRLIK_DUSUK
    if kullanici.guvenilirlik < sabitler.GUVENILIRLIK_ESIK:
        return {"komut": "paket", "durum": "RED", "kod": "GUVENILIRLIK_DUSUK", "kalemler": []}

    # 4. PAKET_RED — her kalem K10 adım 1-12 ile (bakiye hariç) doğrulanır
    dogrulanan: list[dict] = []
    kalem_sonuclari: list[dict] = []
    herhangi_basarisiz = False
    for sira, kalem in enumerate(kalemler):
        b = zaman.parse(kalem["baslangic"])
        e = zaman.parse(kalem["bitis"])
        kod, ucret = dogrulama.dogrula(depo, kullanici_id, kalem["kaynak"], b, e, depo.saat, bakiye_kontrol=False)
        if kod is None:
            kalem_sonuclari.append({"sira": sira, "durum": "TAMAM"})
            dogrulanan.append({"kaynak": kalem["kaynak"], "baslangic": b, "bitis": e, "ucret": ucret})
        else:
            herhangi_basarisiz = True
            kalem_sonuclari.append({"sira": sira, "durum": "RED", "kod": kod})

    if herhangi_basarisiz:
        return {"komut": "paket", "durum": "RED", "kod": "PAKET_RED", "kalemler": kalem_sonuclari}

    # 5. PAKET_ICI_KESISME
    if _ici_kesisme_var_mi(depo, dogrulanan):
        tumu_tamam = [{"sira": i, "durum": "TAMAM"} for i in range(len(kalemler))]
        return {"komut": "paket", "durum": "RED", "kod": "PAKET_ICI_KESISME", "kalemler": tumu_tamam}

    # 6. BAKIYE_YETERSIZ
    toplam = sum(k["ucret"] for k in dogrulanan)
    if toplam > kullanici.bakiye:
        tumu_tamam = [{"sira": i, "durum": "TAMAM"} for i in range(len(kalemler))]
        return {"komut": "paket", "durum": "RED", "kod": "BAKIYE_YETERSIZ", "kalemler": tumu_tamam}

    # Başarı — rezervasyonları oluştur
    paket_id = depo.sonraki_p_id()
    rezervasyon_idleri = []
    ucretler = []
    for kalem in dogrulanan:
        r = depo.yeni_rezervasyon(
            kullanici_id, kalem["kaynak"], kalem["baslangic"], kalem["bitis"], kalem["ucret"], paket=paket_id
        )
        rezervasyon_idleri.append(r.id)
        ucretler.append(kalem["ucret"])

    kullanici.bakiye -= toplam
    return {
        "komut": "paket",
        "durum": "TAMAM",
        "paket_id": paket_id,
        "rezervasyonlar": rezervasyon_idleri,
        "ucretler": ucretler,
        "toplam": toplam,
        "bakiye": kullanici.bakiye,
    }
