"""CLI'nin hiçbir girdiyle çökmediğini doğrular (Bölüm 7, "Bozuk girdi" KARARI)."""
from __future__ import annotations

import io
import json
import os

from rezervasyon.cli import calistir

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASLANGIC = os.path.join(KOK, "testler", "ornek", "baslangic.json")


def _calistir_satirlar(satirlar: list[str], tmp_path) -> list[dict]:
    komutlar_yolu = tmp_path / "komutlar.jsonl"
    komutlar_yolu.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    cikti = io.StringIO()
    calistir(BASLANGIC, str(komutlar_yolu), cikti=cikti)
    return [json.loads(s) for s in cikti.getvalue().splitlines() if s.strip()]


def test_bozuk_json_satiri_gecersiz_komut_doner(tmp_path):
    sonuclar = _calistir_satirlar(["bu json degil {{{"], tmp_path)
    assert len(sonuclar) == 1
    assert sonuclar[0]["durum"] == "RED"
    assert sonuclar[0]["kod"] == "GECERSIZ_KOMUT"


def test_gecerli_json_ama_nesne_degil(tmp_path):
    sonuclar = _calistir_satirlar(["42", '"sadece bir metin"', "[1,2,3]"], tmp_path)
    assert len(sonuclar) == 3
    assert all(s["durum"] == "RED" and s["kod"] == "GECERSIZ_KOMUT" for s in sonuclar)


def test_bilinmeyen_komut_adi(tmp_path):
    sonuclar = _calistir_satirlar([json.dumps({"komut": "ucarak_git"})], tmp_path)
    assert sonuclar[0]["kod"] == "GECERSIZ_KOMUT"


def test_eksik_alan_cokertmez(tmp_path):
    sonuclar = _calistir_satirlar([json.dumps({"komut": "rezervasyon", "kullanici": "u1"})], tmp_path)
    assert sonuclar[0]["durum"] == "RED"
    assert sonuclar[0]["kod"] == "GECERSIZ_KOMUT"


def test_bos_satirlar_atlanir_ve_sayaca_dahil_edilmez(tmp_path):
    satirlar = ["", "   ", json.dumps({"komut": "saat", "zaman": "2027-03-08T08:00"}), ""]
    sonuclar = _calistir_satirlar(satirlar, tmp_path)
    assert len(sonuclar) == 1
    assert sonuclar[0]["no"] == 1


def test_her_satir_icin_tam_bir_cikti_satiri_uretilir(tmp_path):
    satirlar = [
        json.dumps({"komut": "saat", "zaman": "2027-03-08T08:00"}),
        "gecersiz",
        json.dumps({"komut": "sorgu", "tur": "kullanici", "id": "yok"}),
    ]
    sonuclar = _calistir_satirlar(satirlar, tmp_path)
    assert [s["no"] for s in sonuclar] == [1, 2, 3]


def test_karma_dosya_cokmeden_baştan_sona_islenir(tmp_path):
    satirlar = [
        json.dumps({"komut": "kullanici_ekle", "id": "u1", "ad": "A", "rol": "OGRENCI", "sertifikalar": [], "bakiye": 120, "guvenilirlik": 80}),
        "{ tamamen bozuk",
        json.dumps({"komut": "paket", "kullanici": "u1"}),  # 'kalemler' eksik
        json.dumps({"komut": "sorgu", "tur": "kaynak", "id": "YAZ-2", "gun": "2027-03-08"}),
    ]
    sonuclar = _calistir_satirlar(satirlar, tmp_path)
    assert len(sonuclar) == 4
    assert [s["durum"] for s in sonuclar] == ["TAMAM", "RED", "RED", "TAMAM"]
