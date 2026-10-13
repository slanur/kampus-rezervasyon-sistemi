from testler.yardimci import motor


def test_var_olan_kullanici_id_cakisir():
    m = motor()
    r = m.kullanici_ekle("u1", "Ad", "OGRENCI", [], 50, 80)
    assert r["durum"] == "RED" and r["kod"] == "ID_MEVCUT"


def test_var_olan_kaynak_id_cakisir():
    m = motor()
    r = m.kaynak_ekle("YAZ-1", "Ad", "YAZICI", ["OGRENCI"])
    assert r["durum"] == "RED" and r["kod"] == "ID_MEVCUT"


def test_id_mevcut_rol_tanimsizdan_once_kontrol_edilir():
    m = motor()
    r = m.kullanici_ekle("u1", "Ad", "TANIMSIZ_ROL", [], 50, 80)
    assert r["kod"] == "ID_MEVCUT"


def test_tanimsiz_rol():
    m = motor()
    r = m.kullanici_ekle("u9", "Ad", "UFOLOG", [], 50, 80)
    assert r["kod"] == "TANIMSIZ_DEGER"


def test_tanimsiz_tur():
    m = motor()
    r = m.kaynak_ekle("K9", "Ad", "ROKET", ["OGRENCI"])
    assert r["kod"] == "TANIMSIZ_DEGER"


def test_izinli_rollerden_biri_tanimsiz():
    m = motor()
    r = m.kaynak_ekle("K9", "Ad", "ODA", ["OGRENCI", "UZAYLI"])
    assert r["kod"] == "TANIMSIZ_DEGER"


def test_rol_tanimsiz_ve_bakiye_negatif_once_tanimsiz_deger_doner():
    m = motor()
    r = m.kullanici_ekle("u9", "Ad", "UFOLOG", [], -5, 80)
    assert r["kod"] == "TANIMSIZ_DEGER"


def test_bakiye_negatif():
    m = motor()
    r = m.kullanici_ekle("u9", "Ad", "OGRENCI", [], -1, 80)
    assert r["kod"] == "GECERSIZ_DEGER"


def test_bakiye_kota_asiyor():
    m = motor()
    r = m.kullanici_ekle("u9", "Ad", "OGRENCI", [], 121, 80)
    assert r["kod"] == "GECERSIZ_DEGER"


def test_bakiye_tam_kota_gecerli():
    m = motor()
    r = m.kullanici_ekle("u9", "Ad", "OGRENCI", [], 120, 80)
    assert r["durum"] == "TAMAM"


def test_bakiye_sifir_gecerli():
    m = motor()
    r = m.kullanici_ekle("u9", "Ad", "OGRENCI", [], 0, 80)
    assert r["durum"] == "TAMAM"


def test_guvenilirlik_negatif():
    m = motor()
    assert m.kullanici_ekle("u9", "Ad", "OGRENCI", [], 50, -1)["kod"] == "GECERSIZ_DEGER"


def test_guvenilirlik_101():
    m = motor()
    assert m.kullanici_ekle("u9", "Ad", "OGRENCI", [], 50, 101)["kod"] == "GECERSIZ_DEGER"


def test_guvenilirlik_ondalikli():
    m = motor()
    assert m.kullanici_ekle("u9", "Ad", "OGRENCI", [], 50, 50.5)["kod"] == "GECERSIZ_DEGER"


def test_guvenilirlik_bool_gecersiz():
    m = motor()
    assert m.kullanici_ekle("u9", "Ad", "OGRENCI", [], 50, True)["kod"] == "GECERSIZ_DEGER"


def test_kaynak_ekle_bakiye_guvenilirlik_denetlenmez():
    m = motor()
    r = m.kaynak_ekle("K9", "Ad", "ODA", [])
    assert r["durum"] == "TAMAM"


def test_kaynak_ekle_sonrasi_dolulluk_paydasi_degisir_oncesi_ucret_sabit_kalir():
    m = motor()
    r1 = m.rezervasyon("u1", "YAZ-1", "2027-03-08T11:00", "2027-03-08T13:00")
    assert r1["durum"] == "TAMAM" and r1["ucret"] == 36  # tek yazıcı, doluluk 0

    m.kaynak_ekle("YAZ-2", "Yeni Yazıcı", "YAZICI", ["OGRENCI"])

    # Geçmişte alınan r1'in ücreti değişmedi
    rez = m.rezervasyon_detayi("r1")
    assert rez["ucret"] == 36

    # yeni talep artık 2 yazıcıya göre dolulluk hesaplar
    r2 = m.fiyat("u2", "YAZ-2", "2027-03-08T11:00", "2027-03-08T13:00")
    assert r2["durum"] == "TAMAM"


def test_eklenen_kullanici_haftalik_sifirlamaya_dahil_olur():
    m = motor()
    m.kullanici_ekle("u9", "Yeni", "OGRENCI", [], 10, 80)
    sonuc = m.saat("2027-03-15T00:00")
    assert sonuc["durum"] == "TAMAM"
    assert any(o["tur"] == "HAFTALIK_SIFIRLAMA" for o in sonuc["olaylar"])
    assert m.sorgu_kullanici("u9")["bakiye"] == 120


def test_eklenen_kaynakta_bakim_yoktur():
    m = motor()
    m.kaynak_ekle("YAZ-9", "Ad", "YAZICI", ["OGRENCI"])
    r = m.rezervasyon("u1", "YAZ-9", "2027-03-08T11:00", "2027-03-08T12:00")
    assert r["durum"] == "TAMAM"


def test_eklenen_kaynaga_izinsiz_rol():
    m = motor()
    m.kaynak_ekle("YAZ-9", "Ad", "YAZICI", ["ARASTIRMACI"])
    r = m.rezervasyon("u1", "YAZ-9", "2027-03-08T11:00", "2027-03-08T12:00")
    assert r["kod"] == "ROL_IZNI_YOK"
