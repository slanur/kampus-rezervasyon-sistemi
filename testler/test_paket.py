from testler.yardimci import motor


def _kalem(kaynak, b, e):
    return {"kaynak": kaynak, "baslangic": b, "bitis": e}


def test_bulunamadi_kullanici_yok():
    m = motor()
    sonuc = m.paket("yok", [_kalem("ODA-1", "2027-03-08T09:00", "2027-03-08T10:00"), _kalem("YAZ-1", "2027-03-08T09:00", "2027-03-08T10:00")])
    assert sonuc["kod"] == "BULUNAMADI"


def test_tek_kalem_paket_boyutu():
    m = motor()
    sonuc = m.paket("u3", [_kalem("ODA-1", "2027-03-08T09:00", "2027-03-08T10:00")])
    assert sonuc["kod"] == "PAKET_BOYUTU" and sonuc["kalemler"] == []


def test_bes_kalem_paket_boyutu():
    m = motor()
    kalemler = [_kalem("ODA-1", "2027-03-08T09:00", "2027-03-08T09:30")] * 5
    sonuc = m.paket("u3", kalemler)
    assert sonuc["kod"] == "PAKET_BOYUTU" and sonuc["kalemler"] == []


def test_guvenilirlik_49_paket_yasak():
    m = motor(lambda v: v["kullanicilar"].__setitem__(2, {**v["kullanicilar"][2], "guvenilirlik": 49}))
    sonuc = m.paket(
        "u3",
        [_kalem("ODA-1", "2027-03-08T09:00", "2027-03-08T10:00"), _kalem("CIH-1", "2027-03-08T09:00", "2027-03-08T10:00")],
    )
    assert sonuc["kod"] == "GUVENILIRLIK_DUSUK" and sonuc["kalemler"] == []


def test_bir_kalem_bozuk_paket_red_tum_kalemler_listelenir():
    m = motor()
    sonuc = m.paket(
        "u3",
        [
            _kalem("ODA-1", "2027-03-08T09:00", "2027-03-08T10:00"),
            _kalem("LAB-1", "2027-03-08T09:05", "2027-03-08T10:00"),  # zaman adımı hatalı
        ],
    )
    assert sonuc["kod"] == "PAKET_RED"
    assert sonuc["kalemler"][0] == {"sira": 0, "durum": "TAMAM"}
    assert sonuc["kalemler"][1]["durum"] == "RED"
    assert sonuc["kalemler"][1]["kod"] == "ZAMAN_ADIMI_HATASI"


def test_ayni_kaynakta_kalemler_kesisiyor_paket_ici_kesisme():
    m = motor()
    sonuc = m.paket(
        "u3",
        [
            _kalem("ODA-1", "2027-03-08T09:00", "2027-03-08T10:00"),
            _kalem("ODA-1", "2027-03-08T09:30", "2027-03-08T10:30"),
        ],
    )
    assert sonuc["kod"] == "PAKET_ICI_KESISME"
    assert all(k["durum"] == "TAMAM" for k in sonuc["kalemler"])


def test_ayni_kaynakta_hazirlik_ihlali_paket_ici_kesisme():
    m = motor()
    # CIH-1 h=15dk. 09:00-10:00 ve 10:00-11:00 kesişmez ama hazırlık ihlal eder.
    sonuc = m.paket(
        "u3",
        [
            _kalem("CIH-1", "2027-03-08T09:00", "2027-03-08T10:00"),
            _kalem("CIH-1", "2027-03-08T10:00", "2027-03-08T11:00"),
        ],
    )
    assert sonuc["kod"] == "PAKET_ICI_KESISME"


def test_toplam_bakiyeyi_asinca_bakiye_yetersiz():
    m = motor(lambda v: v["kullanicilar"].__setitem__(2, {**v["kullanicilar"][2], "bakiye": 5}))
    sonuc = m.paket(
        "u3",
        [_kalem("ODA-1", "2027-03-08T09:00", "2027-03-08T10:00"), _kalem("CIH-1", "2027-03-08T09:00", "2027-03-08T10:00")],
    )
    assert sonuc["kod"] == "BAKIYE_YETERSIZ"
    assert all(k["durum"] == "TAMAM" for k in sonuc["kalemler"])


def test_ayni_turde_iki_kalem_birbirinin_doluluguna_girmez_ve_tek_tek_iptal_edilebilir():
    m = motor()
    m.kaynak_ekle("ODA-2", "Toplantı Odası 2", "ODA", ["ARASTIRMACI"])
    sonuc = m.paket(
        "u3",
        [_kalem("ODA-1", "2027-03-08T10:00", "2027-03-08T11:00"), _kalem("ODA-2", "2027-03-08T10:00", "2027-03-08T11:00")],
    )
    assert sonuc["durum"] == "TAMAM"
    # ODA tek dolulukta sayılsaydı ikinci kalemin ücreti ilkinden etkilenirdi; enerji yoğun olmadığından ikisi de eşit baz ücret
    assert sonuc["ucretler"][0] == sonuc["ucretler"][1]

    iptal_sonuc = m.iptal(sonuc["rezervasyonlar"][0])
    assert iptal_sonuc["durum"] == "TAMAM"
    kalan = m.rezervasyon_detayi(sonuc["rezervasyonlar"][1])
    assert kalan["durum"] == "ONAYLI"
