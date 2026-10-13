"""Komut satırı arayüzü: baslangic.json + komutlar.jsonl -> sonuclar.jsonl (stdout)."""
from __future__ import annotations

import json
import sys

from .motor import Motor


def calistir(baslangic_yolu: str, komutlar_yolu: str, cikti=sys.stdout) -> None:
    motor = Motor.dosyadan(baslangic_yolu)
    no = 0
    with open(komutlar_yolu, encoding="utf-8") as f:
        for ham_satir in f:
            satir = ham_satir.strip()
            if not satir:
                continue
            no += 1
            try:
                komut = json.loads(satir)
                sonuc = motor.calistir(komut)
            except Exception:
                sonuc = {"komut": None, "durum": "RED", "kod": "GECERSIZ_KOMUT"}
            cikti_satiri = {"no": no, **sonuc}
            cikti.write(json.dumps(cikti_satiri, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    if len(argv) != 3:
        print("Kullanım: python -m rezervasyon baslangic.json komutlar.jsonl", file=sys.stderr)
        return 1
    calistir(argv[1], argv[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
