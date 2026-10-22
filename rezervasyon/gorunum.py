"""Salt okunur görünüm API'si — yalnızca GUI tüketir, durum değiştirmez.

Alt satır (lane) yerleşimi burada hesaplanır: hangi durumların çakışabileceği
bir kural bilgisi olduğu için GUI bunu bilmemeli (Bölüm 8.2, PROJE_ANALIZI.md).
"""
from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta
from fractions import Fraction

from . import dogrulama, fiyat, hata_kodlari, sabitler, zaman
from .depo import Depo
from .model import Durum

_AKTIF_DURUMLAR = (Durum.ONAYLI, Durum.KULLANIMDA, Durum.TAMAMLANDI)
_PASIF_DURUMLAR = (Durum.IPTAL, Durum.GELMEDI)


def simdi(depo: Depo) -> str:
    return zaman.bicimle(depo.saat)


def parametreler(depo: Depo) -> dict:
    sertifika_havuzu = set()
    for tur in depo.turler.values():
        if tur.sertifika:
            sertifika_havuzu.add(tur.sertifika)
    for kullanici in depo.kullanicilar.values():
        sertifika_havuzu.update(kullanici.sertifikalar)
    return {
        "turler": {ad: vars(t) | {"ad": ad} for ad, t in depo.turler.items()},
        "roller": {ad: vars(r) | {"ad": ad} for ad, r in depo.roller.items()},
        "sertifikalar": sorted(sertifika_havuzu),
        "bantlar": sabitler.BANTLAR,
        "pik": (sabitler.PIK_BASLANGIC, sabitler.PIK_BITIS),
        "calisma_saatleri": (sabitler.CALISMA_BASLANGIC, sabitler.CALISMA_BITIS),
    }


def kullanicilar(depo: Depo) -> list[dict]:
    return [
        {"id": u.id, "ad": u.ad, "rol": u.rol, "bakiye": u.bakiye, "guvenilirlik": u.guvenilirlik}
        for u in depo.kullanicilar.values()
    ]


def kaynaklar(depo: Depo) -> list[dict]:
    return [
        {"id": k.id, "ad": k.ad, "tur": k.tur, "izinli_roller": list(k.izinli_roller)}
        for k in depo.kaynaklar.values()
    ]


def _rezervasyon_sozluk(r) -> dict:
    return {
        "id": r.id,
        "kullanici": r.kullanici,
        "kaynak": r.kaynak,
        "baslangic": zaman.bicimle(r.baslangic),
        "bitis": zaman.bicimle(r.bitis),
        "ucret": r.ucret,
        "durum": r.durum.value,
        "paket": r.paket,
    }


def _lanelara_yerlestir(gun_date: date, rezlar: list) -> list[dict]:
    aktif = sorted((r for r in rezlar if r.durum in _AKTIF_DURUMLAR), key=lambda r: (r.baslangic, r.no))
    pasif = sorted((r for r in rezlar if r.durum in _PASIF_DURUMLAR), key=lambda r: (r.baslangic, r.no))

    sonuc = []
    for r in aktif:
        d = _rezervasyon_sozluk(r)
        d["alt_satir"] = 0
        sonuc.append(d)

    # greedy aralık bölümleme: her kayıt, çakışmadığı ilk alt satıra (>=1) girer
    lane_sonlari: list[datetime] = []  # lane i -> o lanedaki son bitiş
    for r in pasif:
        yerlesti = False
        for i, son_bitis in enumerate(lane_sonlari):
            if r.baslangic >= son_bitis:
                lane_sonlari[i] = r.bitis
                d = _rezervasyon_sozluk(r)
                d["alt_satir"] = i + 1
                sonuc.append(d)
                yerlesti = True
                break
        if not yerlesti:
            lane_sonlari.append(r.bitis)
            d = _rezervasyon_sozluk(r)
            d["alt_satir"] = len(lane_sonlari)
            sonuc.append(d)

    sonuc.sort(key=lambda d: (d["alt_satir"], d["baslangic"]))
    return sonuc


def gun_gorunumu(depo: Depo, gun: str) -> dict:
    gun_date = zaman.gun_parse(gun)
    gun_baslangic = datetime.combine(gun_date, datetime.min.time())
    gun_bitis = gun_baslangic + timedelta(days=1)

    sonuc: dict[str, dict] = {}
    for kaynak in depo.kaynaklar.values():
        rezlar = [r for r in depo.rezervasyonlar_for_kaynak(kaynak.id) if r.baslangic.date() == gun_date]
        satirlar = _lanelara_yerlestir(gun_date, rezlar)

        tur = depo.turler[kaynak.tur]
        hazirlik_seritleri = []
        if tur.hazirlik_dk > 0:
            for r in rezlar:
                if r.durum in _AKTIF_DURUMLAR:
                    hazirlik_seritleri.append(
                        {
                            "baslangic": zaman.bicimle(r.bitis),
                            "bitis": zaman.bicimle(r.bitis + timedelta(minutes=tur.hazirlik_dk)),
                            "rezervasyon": r.id,
                        }
                    )

        bakimlar = []
        for b in depo.bakimlar_for(kaynak.id):
            if zaman.kesisir(b.baslangic, b.bitis, gun_baslangic, gun_bitis):
                bakimlar.append({"baslangic": zaman.bicimle(b.baslangic), "bitis": zaman.bicimle(b.bitis)})

        bekleme_kayitlari = [
            {
                "id": k.id,
                "kullanici": k.kullanici,
                "baslangic": zaman.bicimle(k.baslangic),
                "bitis": zaman.bicimle(k.bitis),
                "sira": i + 1,
            }
            for i, k in enumerate(_bekleme_sirali(depo, kaynak.id))
            if k.baslangic.date() == gun_date
        ]

        sonuc[kaynak.id] = {
            "kaynak": kaynak.id,
            "ad": kaynak.ad,
            "tur": kaynak.tur,
            "rezervasyonlar": satirlar,
            "bakimlar": bakimlar,
            "hazirlik_seritleri": hazirlik_seritleri,
            "bekleme_kayitlari": bekleme_kayitlari,
        }
    return sonuc


def _bekleme_sirali(depo: Depo, kaynak_id: str):
    from . import bekleme as bekleme_mod
    return bekleme_mod.sirali(depo, kaynak_id)


def rezervasyon_detayi(depo: Depo, id: str) -> dict | None:
    r = depo.rezervasyonlar.get(id)
    if r is None:
        return None
    return _rezervasyon_sozluk(r) | {"no": r.no}


def kullanici_bekleme_kayitlari(depo: Depo, id: str) -> list[dict]:
    sonuc = []
    for k in depo.bekleme.values():
        if k.kullanici != id:
            continue
        sira = _bekleme_sirali(depo, k.kaynak).index(k) + 1
        sonuc.append(
            {
                "id": k.id,
                "kaynak": k.kaynak,
                "baslangic": zaman.bicimle(k.baslangic),
                "bitis": zaman.bicimle(k.bitis),
                "sira": sira,
            }
        )
    return sonuc


def hata_aciklamasi(kod: str) -> str:
    return hata_kodlari.aciklama(kod)


def _saat_metni(t: datetime) -> str:
    return t.strftime("%H:%M")


def _aralik_metni(b: datetime, e: datetime, referans: date) -> str:
    if b.date() == e.date() == referans:
        return f"{_saat_metni(b)}–{_saat_metni(e)}"
    return f"{b.strftime('%d.%m %H:%M')}–{e.strftime('%d.%m %H:%M')}"


def _sure_metni(dk: int) -> str:
    saat, dakika = divmod(dk, 60)
    if saat and dakika:
        return f"{saat} sa {dakika} dk"
    return f"{saat} sa" if saat else f"{dakika} dk"


def red_aciklamasi(depo: Depo, kullanici_id: str, kaynak_id: str, baslangic: str, bitis: str, kod: str) -> str:
    """Ret kodunu, talebin kendi bağlamıyla (rol, çakışan kayıt, süre…) açıklar."""
    genel = hata_kodlari.aciklama(kod)
    kullanici = depo.kullanicilar.get(kullanici_id)
    kaynak = depo.kaynaklar.get(kaynak_id)
    try:
        b, e = zaman.parse(baslangic), zaman.parse(bitis)
    except (TypeError, ValueError):
        return genel
    if kullanici is None or kaynak is None:
        return genel

    rol = depo.roller[kullanici.rol]
    tur = depo.turler[kaynak.tur]
    gun = b.date()

    if kod == "ZAMAN_ADIMI_HATASI":
        if e <= b:
            return "Bitiş saati başlangıç saatinden sonra olmalı."
        return f"Saatler {sabitler.DILIM_DK} dakikanın katı olmalı (ör. 10:00, 10:15, 10:30)."
    if kod == "GECMIS_ZAMAN":
        return f"Başlangıç ({b.strftime('%d.%m %H:%M')}) simüle saatin ({depo.saat.strftime('%d.%m %H:%M')}) gerisinde kalıyor."
    if kod == "CALISMA_SAATI_DISI":
        cb, ce = time(*sabitler.CALISMA_BASLANGIC), time(*sabitler.CALISMA_BITIS)
        return f"Kaynaklar yalnızca aynı gün içinde {cb:%H:%M}–{ce:%H:%M} arasında kullanılabilir."
    if kod == "SURE_SINIRI":
        sure = int((e - b).total_seconds() // 60)
        if sure < sabitler.ASGARI_SURE_DK:
            return f"En kısa rezervasyon {sabitler.ASGARI_SURE_DK} dk; seçilen süre {_sure_metni(sure)}."
        return (
            f"{kullanici.rol} rolü tek seferde en fazla {_sure_metni(rol.azami_sure_dk)} rezerve edebilir; "
            f"seçilen süre {_sure_metni(sure)}."
        )
    if kod == "ILERI_TARIH_SINIRI":
        sinir = dogrulama.ileri_gun_siniri(depo, kullanici)
        if kullanici.guvenilirlik < sabitler.GUVENILIRLIK_ESIK:
            return (
                f"Güvenilirliğiniz {kullanici.guvenilirlik} ({sabitler.GUVENILIRLIK_ESIK}'nin altında) olduğu için "
                f"en fazla {sinir} gün sonrası için rezervasyon yapabilirsiniz."
            )
        return f"{kullanici.rol} rolü en fazla {sinir} gün sonrası için rezervasyon yapabilir."
    if kod == "ROL_IZNI_YOK":
        if not kaynak.izinli_roller:
            return f"{kaynak.ad} hiçbir role açık değil; bu kaynak rezerve edilemez."
        izinli = ", ".join(kaynak.izinli_roller)
        return f"{kaynak.ad} yalnızca şu rollere açık: {izinli}. Sizin rolünüz {kullanici.rol}."
    if kod == "SERTIFIKA_YOK":
        return f"{kaynak.tur} türündeki kaynaklar için {tur.sertifika} sertifikası gerekiyor."
    if kod == "BAKIM":
        bakim = dogrulama.kesisen_bakim(depo, kaynak_id, b, e)
        if bakim is not None:
            return f"{kaynak.ad} {_aralik_metni(bakim.baslangic, bakim.bitis, gun)} arasında bakımda."
    if kod == "KESISME":
        r = dogrulama.kesisen_rezervasyon(depo, kaynak_id, b, e)
        if r is not None:
            return f"Bu aralık {r.id} rezervasyonuyla ({_aralik_metni(r.baslangic, r.bitis, gun)}) çakışıyor."
    if kod == "HAZIRLIK_IHLALI":
        r = dogrulama.hazirlik_ihlal_eden(depo, kaynak_id, b, e)
        if r is not None:
            return (
                f"{kaynak.tur} kaynaklarında iki kullanım arasında {tur.hazirlik_dk} dk hazırlık süresi gerekiyor; "
                f"{r.id} ({_aralik_metni(r.baslangic, r.bitis, gun)}) ile arada yeterli boşluk yok."
            )
    if kod == "ARDISIK_KULLANIM":
        r = dogrulama.ardisik_ihlal_eden(depo, kullanici_id, kaynak_id, b, e)
        if r is not None:
            return (
                f"Aynı kaynaktaki rezervasyonlarınız arasında en az {sabitler.ARDISIK_BOSLUK_DK} dk olmalı; "
                f"{r.id} ({_aralik_metni(r.baslangic, r.bitis, gun)}) çok yakın."
            )
    if kod == "BAKIYE_YETERSIZ":
        ucret = fiyat.hesapla(depo, kaynak_id, b, e)
        return f"Bu rezervasyon {ucret} KP tutuyor, bakiyeniz {kullanici.bakiye} KP."
    return genel


def ekleme_aciklamasi(depo: Depo, kod: str, komut: dict) -> str:
    """`kullanici_ekle` / `kaynak_ekle` reddini, hangi alanın sorunlu olduğunu söyleyerek açıklar.

    Kontroller `dogrulama`daki ekleme kurallarıyla aynı sırayı izler.
    """
    genel = hata_kodlari.aciklama(kod)
    kullanici_mi = komut.get("komut") == "kullanici_ekle"
    if kod == "ID_MEVCUT":
        ne = "kullanıcı" if kullanici_mi else "kaynak"
        return f"{komut.get('id')} kimliğiyle bir {ne} zaten var."
    if kod == "TANIMSIZ_DEGER":
        if kullanici_mi:
            return f"{komut.get('rol')} rolü başlangıç dosyasında tanımlı değil."
        if komut.get("tur") not in depo.turler:
            return f"{komut.get('tur')} türü başlangıç dosyasında tanımlı değil."
        tanimsiz = [r for r in komut.get("izinli_roller") or [] if r not in depo.roller]
        return f"Şu roller başlangıç dosyasında tanımlı değil: {', '.join(tanimsiz)}."
    if kod == "GECERSIZ_DEGER" and kullanici_mi:
        rol = depo.roller.get(komut.get("rol"))
        bakiye, guvenilirlik = komut.get("bakiye"), komut.get("guvenilirlik")
        if rol is not None and (type(bakiye) is not int or not 0 <= bakiye <= rol.haftalik_kota):
            return (
                f"Bakiye 0 ile {komut.get('rol')} rolünün haftalık kotası ({rol.haftalik_kota}) arasında "
                f"bir tam sayı olmalı; girilen: {bakiye}."
            )
        return f"Güvenilirlik 0 ile 100 arasında bir tam sayı olmalı; girilen: {guvenilirlik}."
    return genel


def _sayi_metni(deger: Fraction) -> str:
    """Kesri Türkçe ondalık yazımla gösterir: 9/2 -> "4,5", 45/8 -> "5,625"."""
    if deger.denominator == 1:
        return str(deger.numerator)
    return f"{float(deger):.3f}".rstrip("0").rstrip(".").replace(".", ",")


def ucret_dokumu(depo: Depo, kullanici_id: str, kaynak_id: str, baslangic: str, bitis: str) -> dict:
    """Bir talebin ücretinin bant bant dökümü (K5). Durum değiştirmez.

    Talep `fiyat` komutunun kontrollerinden geçmiyorsa yalnızca hata kodu döner.
    Satırlar `fiyat.bant_dokumu()`ndan gelir; toplam, modülün gerçek ücretiyle aynıdır.
    """
    try:
        b, e = zaman.parse(baslangic), zaman.parse(bitis)
    except (TypeError, ValueError):
        return {"gecerli": False, "kod": "ZAMAN_ADIMI_HATASI"}
    kod, ucret = dogrulama.dogrula(depo, kullanici_id, kaynak_id, b, e, depo.saat, bakiye_kontrol=False)
    if kod is not None:
        return {"gecerli": False, "kod": kod}

    kaynak = depo.kaynaklar[kaynak_id]
    tur = depo.turler[kaynak.tur]
    satirlar = fiyat.bant_dokumu(depo, kaynak_id, b, e)
    toplam = sum((s["tutar"] for s in satirlar), Fraction(0))
    return {
        "gecerli": True,
        "kaynak": kaynak.id,
        "tur": kaynak.tur,
        "temel_ucret": tur.temel_ucret,
        "enerji_yogun": tur.enerji_yogun,
        "pik": [sabitler.PIK_BASLANGIC, sabitler.PIK_BITIS],
        "satirlar": [
            {
                "bant": f"{_saat_metni(s['bant_b'])}–{_saat_metni(s['bant_e'])}",
                "aralik": f"{_saat_metni(s['alt'])}–{_saat_metni(s['ust'])}",
                "dilim": s["dilim_sayisi"],
                "dilim_ucreti": _sayi_metni(s["dilim_ucreti"]),
                "dolu_dk": s["dolu_dk"],
                "kaynak_sayisi": s["kaynak_sayisi"],
                "kapasite_dk": s["kaynak_sayisi"] * 120,
                "doluluk": _sayi_metni(s["doluluk"]),
                "bant_carpan": _sayi_metni(s["bant_carpan"]),
                "pik": s["pik"],
                "pik_carpan": _sayi_metni(s["pik_carpan"]),
                "tutar": _sayi_metni(s["tutar"]),
            }
            for s in satirlar
        ],
        "toplam": _sayi_metni(toplam),
        "ucret": ucret,
    }


def doluluk_seridi(depo: Depo, gun: str) -> dict:
    """Seçilen günde her tür için bant bant doluluk ve bant çarpanı (K5). Durum değiştirmez.

    Takvimin üstündeki ısı şeridini besler; kullanıcı ucuz saatleri bir bakışta görür.
    """
    gun_date = zaman.gun_parse(gun)
    turler = []
    for tur_adi, tur in depo.turler.items():
        if depo.turdeki_kaynak_sayisi(tur_adi) == 0:
            continue
        bantlar = []
        for bant_bas_saat, bant_bit_saat in sabitler.BANTLAR:
            bant_b = datetime.combine(gun_date, time(bant_bas_saat, 0))
            bant_e = datetime.combine(gun_date, time(bant_bit_saat, 0))
            dolu_dk, sayi = fiyat._dolu_dakika(depo, tur_adi, gun_date, bant_b, bant_e)
            doluluk = Fraction(dolu_dk, sayi * 120)
            bantlar.append({
                "bant": f"{_saat_metni(bant_b)}–{_saat_metni(bant_e)}",
                "dolu_dk": dolu_dk,
                "kapasite_dk": sayi * 120,
                "doluluk_yuzde": round(float(doluluk) * 100),
                "bant_carpan": _sayi_metni(fiyat.bant_carpani(doluluk)),
                "seviye": min(4, math.floor(4 * doluluk)),
                "pik": (pik := tur.enerji_yogun and fiyat.zaman_pik_mi(bant_bas_saat, bant_bit_saat)),
                "pik_carpan": _sayi_metni(sabitler.PIK_CARPAN if pik else sabitler.NORMAL_CARPAN),
            })
        turler.append({"tur": tur_adi, "kaynak_sayisi": depo.turdeki_kaynak_sayisi(tur_adi), "bantlar": bantlar})
    return {"turler": turler}


_ONERI_GUN_UFKU = 7
_KAYNAK_ONERI_ADEDI = 2


def uygun_araliklar(
    depo: Depo, kullanici_id: str, kaynak_id: str, baslangic: str, bitis: str, adet: int = 3
) -> dict:
    """Geçersiz bir talep için geçerli alternatifler (durum değiştirmez).

    `zaman`: aynı kaynak ve aynı süreyle, istenen başlangıca en yakın aralıklar
    (önce aynı gün, sonra sonraki günler). `kaynak`: aynı aralıkta uygun olan
    diğer kaynaklar (önce aynı türdekiler). Her aday `dogrula()`dan geçer.
    """
    bos = {"zaman": [], "kaynak": []}
    kullanici = depo.kullanicilar.get(kullanici_id)
    kaynak = depo.kaynaklar.get(kaynak_id)
    try:
        b, e = zaman.parse(baslangic), zaman.parse(bitis)
    except (TypeError, ValueError):
        return bos
    sure = e - b
    if kullanici is None or kaynak is None or sure <= timedelta(0):
        return bos

    def oneri(kid: str, bb: datetime, ee: datetime) -> dict | None:
        kod, ucret = dogrulama.dogrula(depo, kullanici_id, kid, bb, ee, depo.saat, bakiye_kontrol=True)
        if kod is not None:
            return None
        return {
            "kaynak": kid,
            "kaynak_ad": depo.kaynaklar[kid].ad,
            "baslangic": zaman.bicimle(bb),
            "bitis": zaman.bicimle(ee),
            "ucret": ucret,
        }

    zaman_onerileri: list[dict] = []
    adim = timedelta(minutes=sabitler.DILIM_DK)
    for ofset in range(_ONERI_GUN_UFKU + 1):
        gun = b.date() + timedelta(days=ofset)
        t = datetime.combine(gun, time(*sabitler.CALISMA_BASLANGIC))
        son = datetime.combine(gun, time(*sabitler.CALISMA_BITIS)) - sure
        adaylar = []
        while t <= son:
            if t != b:
                adaylar.append(t)
            t += adim
        # en yakın önce; eşitlikte ileri saat tercih edilir
        adaylar.sort(key=lambda a: (abs(a - b), a < b))
        for a in adaylar:
            o = oneri(kaynak_id, a, a + sure)
            if o is not None:
                zaman_onerileri.append(o)
                if len(zaman_onerileri) == adet:
                    break
        if len(zaman_onerileri) == adet:
            break

    kaynak_onerileri: list[dict] = []
    digerleri = sorted(
        (k for k in depo.kaynaklar.values() if k.id != kaynak_id),
        key=lambda k: (k.tur != kaynak.tur, k.id),
    )
    for k in digerleri:
        o = oneri(k.id, b, e)
        if o is not None:
            kaynak_onerileri.append(o)
            if len(kaynak_onerileri) == _KAYNAK_ONERI_ADEDI:
                break

    return {"zaman": zaman_onerileri, "kaynak": kaynak_onerileri}


def sonraki_olay_zamani(depo: Depo) -> str | None:
    from .olaylar import _sonraki_olay_zamani
    t = _sonraki_olay_zamani(depo, depo.saat)
    return zaman.bicimle(t) if t else None


def iptal_onizleme(depo: Depo, id: str) -> dict | None:
    r = depo.rezervasyonlar.get(id)
    if r is None or r.durum != Durum.ONAYLI:
        return None
    kullanici = depo.kullanicilar[r.kullanici]
    rol = depo.roller[kullanici.rol]
    kalan = r.baslangic - depo.saat

    if kalan >= timedelta(hours=sabitler.IADE_TAM_SINIR_SAAT):
        hesaplanan_iade, guv_delta, oran = r.ucret, 0, 100
    elif kalan >= timedelta(hours=sabitler.IADE_YARIM_SINIR_SAAT):
        hesaplanan_iade, guv_delta, oran = r.ucret // 2, 0, 50
    else:
        hesaplanan_iade, guv_delta, oran = 0, sabitler.GUVENILIRLIK_GEC_IPTAL, 0

    iade_eklenen = max(0, min(hesaplanan_iade, rol.haftalik_kota - kullanici.bakiye))
    return {"oran": oran, "iade": iade_eklenen, "guvenilirlik_delta": guv_delta}
