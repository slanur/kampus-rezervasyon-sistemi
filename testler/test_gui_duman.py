"""GUI duman testi (P2, Bölüm 16.1). PySide6 kurulu değilse atlanır.

Pencereyi başsız (offscreen) platformda açar, 19 işlemlik örnek senaryoyu
`Oturum` üzerinden oynatır ve günlükteki sonuçların `beklenen.jsonl` ile
aynı olduğunu doğrular — böylece GUI'nin kullandığı kod yolu da kabul
senaryosuna karşı sınanmış olur.
"""
from __future__ import annotations

import json
import os

import pytest

pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from arayuz.ana_pencere import AnaPencere  # noqa: E402
from testler.karsilastir import satirlari_karsilastir  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORNEK = os.path.join(KOK, "testler", "ornek")


@pytest.fixture(scope="module")
def app():
    uygulama = QApplication.instance() or QApplication([])
    yield uygulama


def test_pencere_acilir_ve_dosya_yuklenir(app):
    # AnaPencere artık QWebEngineView barındırır; dosya yükleme sayfa
    # yüklendikten SONRA (asenkron) tetiklenir. Testte pencerenin gerçekten
    # kurulabildiğini doğruluyoruz, ardından Oturum'u doğrudan kullanıyoruz
    # (web sayfasının gerçekten render olmasına bağlı değiliz).
    pencere = AnaPencere()
    assert pencere._oturum is not None
    pencere._oturum.dosya_yukle(os.path.join(ORNEK, "baslangic.json"))
    assert pencere._oturum.yuklu_mu()
    assert pencere._oturum.simdi() == "2027-03-08T08:00"
    pencere.close()


def test_19_islem_oturum_uzerinden_beklenenle_eslesir(app):
    pencere = AnaPencere()
    oturum = pencere._oturum
    oturum.dosya_yukle(os.path.join(ORNEK, "baslangic.json"))

    with open(os.path.join(ORNEK, "komutlar.jsonl"), encoding="utf-8") as f:
        komutlar = [json.loads(s) for s in f if s.strip()]
    with open(os.path.join(ORNEK, "beklenen.jsonl"), encoding="utf-8") as f:
        beklenenler = [json.loads(s) for s in f if s.strip()]

    for komut in komutlar:
        ad = komut["komut"]
        kwargs = {k: v for k, v in komut.items() if k != "komut"}
        if ad == "sorgu":
            fn = oturum.sorgu_kullanici if kwargs["tur"] == "kullanici" else oturum.sorgu_kaynak
            fn(**{k: v for k, v in kwargs.items() if k != "tur"})
        else:
            getattr(oturum, ad)(**kwargs)

    farklar = []
    for i, (kayit, beklenen) in enumerate(zip(oturum.gunluk, beklenenler), start=1):
        beklenen_no_haric = {k: v for k, v in beklenen.items() if k != "no"}
        for fark in satirlari_karsilastir(beklenen_no_haric, kayit["sonuc"]):
            farklar.append(f"işlem {i}: {fark}")
    assert not farklar, "\n".join(farklar)
    pencere.close()


def test_fiyat_onizlemesi_gunluge_yazilmaz(app):
    pencere = AnaPencere()
    oturum = pencere._oturum
    oturum.dosya_yukle(os.path.join(ORNEK, "baslangic.json"))

    onizleme = oturum.fiyat_onizleme("u3", "CIH-1", "2027-03-08T14:00", "2027-03-08T16:00")
    assert onizleme == {"komut": "fiyat", "durum": "TAMAM", "ucret": 48}
    assert oturum.gunluk == []

    # Bilinçli `fiyat` komutu ise günlüğe yazılır.
    oturum.fiyat("u3", "CIH-1", "2027-03-08T14:00", "2027-03-08T16:00")
    assert [k["komut"]["komut"] for k in oturum.gunluk] == ["fiyat"]
    pencere.close()


def test_geri_al_reddedilenleri_atlar_ve_gunlugu_korur(app):
    pencere = AnaPencere()
    oturum = pencere._oturum
    oturum.dosya_yukle(os.path.join(ORNEK, "baslangic.json"))

    oturum.kaynak_ekle("ODA-9", "Kapalı Oda", "ODA", [])                                 # TAMAM
    oturum.fiyat("u3", "CIH-1", "2027-03-08T14:00", "2027-03-08T16:00")                  # günlüğe yazılır
    oturum.rezervasyon("u3", "ODA-9", "2027-03-08T09:00", "2027-03-08T10:00")            # RED ROL_IZNI_YOK
    assert [k["komut"]["komut"] for k in oturum.gunluk] == ["kaynak_ekle", "fiyat", "rezervasyon"]

    # Son komut reddedildiği için geri alınan şey ODA-9'un eklenmesidir.
    sonuc = oturum.geri_al()
    assert sonuc["geri_alinan"]["komut"] == "kaynak_ekle"
    assert "ODA-9" not in [k["id"] for k in oturum.kaynaklar()]
    assert oturum.gunluk == []
    assert not oturum.geri_al_yapilabilir()
    pencere.close()


def test_geri_al_onceki_reddi_ve_fiyati_gunlukte_tutar(app):
    pencere = AnaPencere()
    oturum = pencere._oturum
    oturum.dosya_yukle(os.path.join(ORNEK, "baslangic.json"))

    oturum.kullanici_ekle("u3", "Deneme", "OGRENCI", [], 120, 100)                       # RED ID_MEVCUT
    oturum.fiyat("u3", "CIH-1", "2027-03-08T14:00", "2027-03-08T16:00")
    oturum.rezervasyon("u3", "ODA-1", "2027-03-08T09:00", "2027-03-08T10:00")            # TAMAM r1

    oturum.geri_al()
    assert [(k["komut"]["komut"], k["sonuc"]["durum"]) for k in oturum.gunluk] == [
        ("kullanici_ekle", "RED"), ("fiyat", "TAMAM")]
    assert oturum.motor.rezervasyon_detayi("r1") is None
    pencere.close()
