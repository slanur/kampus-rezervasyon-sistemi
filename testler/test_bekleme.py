from testler.yardimci import motor


def test_gecerli_talep_icin_bekleme_gereksiz():
    m = motor()
    sonuc = m.bekleme("u1", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")
    assert sonuc["kod"] == "BEKLEME_GEREKSIZ"


def test_yalnizca_bakiye_yetersizse_bekleme_gereksiz():
    m = motor(lambda v: v["kullanicilar"].__setitem__(0, {**v["kullanicilar"][0], "bakiye": 0}))
    sonuc = m.bekleme("u1", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")
    assert sonuc["kod"] == "BEKLEME_GEREKSIZ"


def test_sertifika_yoksa_bekleme_o_kodu_doner():
    m = motor()
    sonuc = m.bekleme("u2", "LAB-1", "2027-03-08T09:00", "2027-03-08T09:30")
    assert sonuc["kod"] == "SERTIFIKA_YOK"


def test_siralama_guvenilirlik_sonra_kayit_saati_sonra_no():
    m = motor()
    m.rezervasyon("u3", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")  # yeri dolduran
    b1 = m.bekleme("u1", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")  # güv 80
    m.saat("2027-03-08T08:05")
    b2 = m.bekleme("u2", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")  # güv 80, sonra kaydoldu
    assert b1["sira"] == 1
    assert b2["sira"] == 2


def test_ilk_kayit_bakiye_yetmez_ikinci_atanir():
    m = motor(lambda v: v["kullanicilar"].__setitem__(0, {**v["kullanicilar"][0], "bakiye": 0}))
    r = m.rezervasyon("u3", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")
    m.bekleme("u1", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")  # u1 bakiye 0
    m.bekleme("u2", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")  # u2 bakiye 120

    sonuc = m.iptal(r["rezervasyon_id"])
    olay = sonuc["olaylar"][0]
    assert olay["kullanici"] == "u2"
    # u1'in kaydı listede kalmış olmalı
    assert len(m.kullanici_bekleme_kayitlari("u1")) == 1


def test_baslangici_gecmis_kayit_silinir():
    m = motor()
    m.rezervasyon("u3", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")
    m.bekleme("u1", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")
    assert len(m.kullanici_bekleme_kayitlari("u1")) == 1
    m.saat("2027-03-08T09:31")  # başlangıç artık geçmişte kaldı
    assert len(m.kullanici_bekleme_kayitlari("u1")) == 0


def test_kesisme_kullanicinin_kendi_rezervasyonuyla_da_bekleme_acilabilir():
    m = motor()
    m.rezervasyon("u1", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")
    sonuc = m.bekleme("u1", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")
    assert sonuc["durum"] == "TAMAM"
