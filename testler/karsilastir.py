"""Beklenen ve üretilen sonuç dosyalarını alan alan karşılaştırır.

Kural (proje dokümanı Bölüm 5): eksik veya farklı alan hata sayılır, fazla
alan serbesttir. İç içe sözlük/listeler de aynı kuralla (recursive) kontrol
edilir.
"""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class Fark:
    satir_no: int
    yol: str
    beklenen: object
    bulunan: object

    def __str__(self) -> str:
        return f"satır {self.satir_no}, alan '{self.yol}': beklenen={self.beklenen!r} bulunan={self.bulunan!r}"


def _karsilastir_deger(beklenen, bulunan, yol: str, farklar: list[str]) -> None:
    if isinstance(beklenen, dict):
        if not isinstance(bulunan, dict):
            farklar.append(f"'{yol}': sözlük bekleniyordu, {type(bulunan).__name__} bulundu")
            return
        for anahtar, deger in beklenen.items():
            alt_yol = f"{yol}.{anahtar}" if yol else anahtar
            if anahtar not in bulunan:
                farklar.append(f"'{alt_yol}': alan eksik")
                continue
            _karsilastir_deger(deger, bulunan[anahtar], alt_yol, farklar)
    elif isinstance(beklenen, list):
        if not isinstance(bulunan, list):
            farklar.append(f"'{yol}': liste bekleniyordu, {type(bulunan).__name__} bulundu")
            return
        if len(beklenen) != len(bulunan):
            farklar.append(f"'{yol}': {len(beklenen)} öğe bekleniyordu, {len(bulunan)} bulundu")
            return
        for i, (b, g) in enumerate(zip(beklenen, bulunan)):
            _karsilastir_deger(b, g, f"{yol}[{i}]", farklar)
    else:
        if beklenen != bulunan:
            farklar.append(f"'{yol}': beklenen={beklenen!r} bulunan={bulunan!r}")


def satirlari_karsilastir(beklenen_satir: dict, bulunan_satir: dict) -> list[str]:
    farklar: list[str] = []
    _karsilastir_deger(beklenen_satir, bulunan_satir, "", farklar)
    return farklar


def dosyalari_karsilastir(beklenen_yol: str, bulunan_yol: str) -> list[str]:
    tum_farklar: list[str] = []
    with open(beklenen_yol, encoding="utf-8") as fb, open(bulunan_yol, encoding="utf-8") as fu:
        beklenen_satirlar = [json.loads(s) for s in fb if s.strip()]
        bulunan_satirlar = [json.loads(s) for s in fu if s.strip()]

    if len(beklenen_satirlar) != len(bulunan_satirlar):
        tum_farklar.append(
            f"satır sayısı farklı: beklenen={len(beklenen_satirlar)} bulunan={len(bulunan_satirlar)}"
        )
        return tum_farklar

    for i, (b, u) in enumerate(zip(beklenen_satirlar, bulunan_satirlar), start=1):
        for fark in satirlari_karsilastir(b, u):
            tum_farklar.append(f"satır {i}: {fark}")
    return tum_farklar


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Kullanım: python karsilastir.py beklenen.jsonl bulunan.jsonl", file=sys.stderr)
        raise SystemExit(1)
    farklar = dosyalari_karsilastir(sys.argv[1], sys.argv[2])
    if farklar:
        for f in farklar:
            print(f)
        raise SystemExit(1)
    print("Tüm satırlar eşleşti.")
