"""`testler/ornek` ve `testler/senaryolar/*` altındaki tüm senaryoları
CLI üzerinden çalıştırıp `beklenen.jsonl` ile alan alan karşılaştırır."""
from __future__ import annotations

import io
import os

import pytest

from rezervasyon.cli import calistir
from testler.karsilastir import dosyalari_karsilastir

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _senaryo_klasorleri() -> list[str]:
    sonuc = []
    ornek = os.path.join(KOK, "testler", "ornek")
    if os.path.isdir(ornek):
        sonuc.append(ornek)
    senaryolar_kok = os.path.join(KOK, "testler", "senaryolar")
    if os.path.isdir(senaryolar_kok):
        for ad in sorted(os.listdir(senaryolar_kok)):
            yol = os.path.join(senaryolar_kok, ad)
            if os.path.isdir(yol):
                sonuc.append(yol)
    return sonuc


@pytest.mark.parametrize("klasor", _senaryo_klasorleri(), ids=lambda p: os.path.basename(p))
def test_senaryo(klasor: str, tmp_path) -> None:
    baslangic = os.path.join(klasor, "baslangic.json")
    komutlar = os.path.join(klasor, "komutlar.jsonl")
    beklenen = os.path.join(klasor, "beklenen.jsonl")

    bulunan_yol = tmp_path / "bulunan.jsonl"
    with open(bulunan_yol, "w", encoding="utf-8") as f:
        calistir(baslangic, komutlar, cikti=f)

    farklar = dosyalari_karsilastir(beklenen, str(bulunan_yol))
    assert not farklar, "\n".join(farklar)
