"""Örnek senaryonun 19 işlemini, GUI'nin çağıracağı türden doğrudan Motor
fonksiyonlarıyla (calistir() dağıtıcısını KULLANMADAN) çalıştırır ve
sonuçların CLI/`beklenen.jsonl` ile aynı olduğunu doğrular.

Bu, dokümanın "19 işlem arayüzden yapıldığında aynı sonuçlar görülmelidir"
şartının otomatik kanıtıdır (Bölüm 16.1, PROJE_ANALIZI.md).
"""
from __future__ import annotations

import json
import os

from rezervasyon.motor import Motor
from testler.karsilastir import satirlari_karsilastir

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORNEK = os.path.join(KOK, "testler", "ornek")


def _dogrudan_cagir(motor: Motor, komut: dict) -> dict:
    ad = komut["komut"]
    if ad == "saat":
        return motor.saat(komut["zaman"])
    if ad == "rezervasyon":
        return motor.rezervasyon(komut["kullanici"], komut["kaynak"], komut["baslangic"], komut["bitis"])
    if ad == "paket":
        return motor.paket(komut["kullanici"], komut["kalemler"])
    if ad == "fiyat":
        return motor.fiyat(komut["kullanici"], komut["kaynak"], komut["baslangic"], komut["bitis"])
    if ad == "iptal":
        return motor.iptal(komut["rezervasyon"])
    if ad == "giris":
        return motor.giris(komut["rezervasyon"])
    if ad == "cikis":
        return motor.cikis(komut["rezervasyon"])
    if ad == "bekleme":
        return motor.bekleme(komut["kullanici"], komut["kaynak"], komut["baslangic"], komut["bitis"])
    if ad == "sorgu" and komut["tur"] == "kullanici":
        return motor.sorgu_kullanici(komut["id"])
    if ad == "sorgu" and komut["tur"] == "kaynak":
        return motor.sorgu_kaynak(komut["id"], komut["gun"])
    if ad == "kullanici_ekle":
        return motor.kullanici_ekle(
            komut["id"], komut["ad"], komut["rol"], komut.get("sertifikalar", []), komut["bakiye"], komut["guvenilirlik"]
        )
    if ad == "kaynak_ekle":
        return motor.kaynak_ekle(komut["id"], komut["ad"], komut["tur"], komut.get("izinli_roller", []))
    raise AssertionError(f"bilinmeyen komut: {ad}")


def test_19_islem_gui_fonksiyonlariyla_ayni_sonucu_verir() -> None:
    motor = Motor.dosyadan(os.path.join(ORNEK, "baslangic.json"))

    with open(os.path.join(ORNEK, "komutlar.jsonl"), encoding="utf-8") as f:
        komutlar = [json.loads(s) for s in f if s.strip()]
    with open(os.path.join(ORNEK, "beklenen.jsonl"), encoding="utf-8") as f:
        beklenenler = [json.loads(s) for s in f if s.strip()]

    assert len(komutlar) == len(beklenenler)

    tum_farklar: list[str] = []
    for i, (komut, beklenen) in enumerate(zip(komutlar, beklenenler), start=1):
        beklenen_no_haric = {k: v for k, v in beklenen.items() if k != "no"}
        sonuc = _dogrudan_cagir(motor, komut)
        for fark in satirlari_karsilastir(beklenen_no_haric, sonuc):
            tum_farklar.append(f"işlem {i} ({komut['komut']}): {fark}")

    assert not tum_farklar, "\n".join(tum_farklar)
