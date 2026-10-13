"""`baslangic.json` dosyasını okuyup bir Depo kurar."""
from __future__ import annotations

import json

from . import zaman
from .depo import Depo
from .model import BakimPenceresi, Kaynak, KaynakTuru, Kullanici, Rol


def yukle(yol: str) -> Depo:
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    return yukle_sozlukten(veri)


def yukle_sozlukten(veri: dict) -> Depo:
    depo = Depo()
    depo.saat = zaman.parse(veri["saat"])

    for ad, t in veri.get("kaynak_turleri", {}).items():
        depo.turler[ad] = KaynakTuru(
            ad=ad,
            hazirlik_dk=t["hazirlik_dk"],
            temel_ucret=t["temel_ucret"],
            enerji_yogun=bool(t["enerji_yogun"]),
            sertifika=t.get("sertifika"),
        )

    for ad, r in veri.get("roller", {}).items():
        depo.roller[ad] = Rol(
            ad=ad,
            haftalik_kota=r["haftalik_kota"],
            ileri_gun=r["ileri_gun"],
            azami_sure_dk=r["azami_sure_dk"],
        )

    for k in veri.get("kaynaklar", []):
        depo.kaynaklar[k["id"]] = Kaynak(
            id=k["id"],
            ad=k["ad"],
            tur=k["tur"],
            izinli_roller=tuple(k.get("izinli_roller", [])),
        )

    for b in veri.get("bakim_pencereleri", []):
        depo.bakimlar.append(
            BakimPenceresi(
                kaynak=b["kaynak"],
                baslangic=zaman.parse(b["baslangic"]),
                bitis=zaman.parse(b["bitis"]),
            )
        )

    for u in veri.get("kullanicilar", []):
        depo.kullanicilar[u["id"]] = Kullanici(
            id=u["id"],
            ad=u["ad"],
            rol=u["rol"],
            sertifikalar=tuple(u.get("sertifikalar", [])),
            bakiye=u["bakiye"],
            guvenilirlik=u["guvenilirlik"],
        )

    return depo
