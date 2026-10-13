"""Alan modeli — Bölüm 3/4 (PDF) ve Bölüm 4 (PROJE_ANALIZI.md)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Durum(StrEnum):
    ONAYLI = "ONAYLI"
    KULLANIMDA = "KULLANIMDA"
    TAMAMLANDI = "TAMAMLANDI"
    IPTAL = "IPTAL"
    GELMEDI = "GELMEDI"


@dataclass(frozen=True)
class KaynakTuru:
    ad: str
    hazirlik_dk: int
    temel_ucret: int
    enerji_yogun: bool
    sertifika: str | None


@dataclass(frozen=True)
class Rol:
    ad: str
    haftalik_kota: int
    ileri_gun: int
    azami_sure_dk: int


@dataclass(frozen=True)
class Kaynak:
    id: str
    ad: str
    tur: str
    izinli_roller: tuple[str, ...]


@dataclass
class Kullanici:
    id: str
    ad: str
    rol: str
    sertifikalar: tuple[str, ...]
    bakiye: int
    guvenilirlik: int


@dataclass
class Rezervasyon:
    id: str
    no: int
    kullanici: str
    kaynak: str
    baslangic: datetime
    bitis: datetime
    ucret: int
    durum: Durum
    paket: str | None = None


@dataclass(frozen=True)
class BakimPenceresi:
    kaynak: str
    baslangic: datetime
    bitis: datetime


@dataclass
class BeklemeKaydi:
    id: str
    no: int
    kullanici: str
    kaynak: str
    baslangic: datetime
    bitis: datetime
    kayit_saati: datetime
