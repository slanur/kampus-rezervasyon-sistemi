"""K9 — bekleme listesi: kayıt açma, sıralama, tarama ve temizlik."""
from __future__ import annotations

from datetime import datetime

from . import dogrulama, zaman
from .depo import Depo
from .model import BeklemeKaydi


def _sira_anahtari(depo: Depo, kayit: BeklemeKaydi):
    kullanici = depo.kullanicilar[kayit.kullanici]
    return (-kullanici.guvenilirlik, kayit.kayit_saati, kayit.no)


def sirali(depo: Depo, kaynak_id: str) -> list[BeklemeKaydi]:
    kayitlar = depo.bekleme_for_kaynak(kaynak_id)
    kayitlar.sort(key=lambda k: _sira_anahtari(depo, k))
    return kayitlar


def bekleme_ac(depo: Depo, kullanici_id: str, kaynak_id: str, baslangic: datetime, bitis: datetime) -> dict:
    kod, _ = dogrulama.dogrula(depo, kullanici_id, kaynak_id, baslangic, bitis, depo.saat, bakiye_kontrol=False)

    if kod is None:
        return {"komut": "bekleme", "durum": "RED", "kod": "BEKLEME_GEREKSIZ"}

    if kod not in ("KESISME", "HAZIRLIK_IHLALI"):
        return {"komut": "bekleme", "durum": "RED", "kod": kod}

    kayit = depo.yeni_bekleme(kullanici_id, kaynak_id, baslangic, bitis, depo.saat)
    sira = sirali(depo, kaynak_id).index(kayit) + 1
    return {"komut": "bekleme", "durum": "TAMAM", "bekleme_id": kayit.id, "sira": sira}


def tara(depo: Depo, kaynak_id: str, simdi: datetime) -> list[dict]:
    """Kaynakta yer boşaldığında çağrılır (iptal, gelmeme, çıkış)."""
    olaylar: list[dict] = []
    for kayit in sirali(depo, kaynak_id):
        if kayit.id not in depo.bekleme:
            continue
        kod, ucret = dogrulama.dogrula(
            depo, kayit.kullanici, kayit.kaynak, kayit.baslangic, kayit.bitis, simdi, bakiye_kontrol=True
        )
        if kod is None:
            r = depo.yeni_rezervasyon(kayit.kullanici, kayit.kaynak, kayit.baslangic, kayit.bitis, ucret)
            kullanici = depo.kullanicilar[kayit.kullanici]
            kullanici.bakiye -= ucret
            del depo.bekleme[kayit.id]
            olaylar.append(
                {
                    "zaman": zaman.bicimle(simdi),
                    "tur": "OTOMATIK_ATAMA",
                    "bekleme": kayit.id,
                    "rezervasyon": r.id,
                    "kullanici": kayit.kullanici,
                    "ucret": ucret,
                    "bakiye": kullanici.bakiye,
                }
            )
    return olaylar


def temizle(depo: Depo) -> None:
    """Başlangıcı simüle saatten önceye düşen kayıtları sessizce siler."""
    silinecekler = [k.id for k in depo.bekleme.values() if k.baslangic < depo.saat]
    for bid in silinecekler:
        del depo.bekleme[bid]
