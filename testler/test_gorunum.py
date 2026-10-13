from testler.yardimci import motor


def test_iptal_gelmedi_ustuste_binmeden_alt_satirlara_yerlesir():
    m = motor()
    r1 = m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")
    m.iptal(r1["rezervasyon_id"])
    r2 = m.rezervasyon("u2", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")  # aynı aralık, şimdi boş
    m.saat("2027-03-08T11:15")  # r2 gelmedi olur (giriş yapılmadı)

    gorunum = m.gun_gorunumu("2027-03-08")
    satirlar = gorunum["YAZ-1"]["rezervasyonlar"]
    alt_satirlar = {s["id"]: s["alt_satir"] for s in satirlar}
    assert alt_satirlar[r1["rezervasyon_id"]] != alt_satirlar[r2["rezervasyon_id"]]


def test_hazirlik_seridi_aktif_rezervasyonun_bitisinden_baslar():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")
    gorunum = m.gun_gorunumu("2027-03-08")
    seritler = gorunum["YAZ-1"]["hazirlik_seritleri"]
    assert seritler[0]["baslangic"] == "2027-03-08T11:00"
    assert seritler[0]["bitis"] == "2027-03-08T11:20"


def test_sorgu_kaynak_yalnizca_onayli_kullanimda_ve_bakim_listelenir():
    m = motor()
    r1 = m.rezervasyon("u1", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")
    m.iptal(r1["rezervasyon_id"])
    m.rezervasyon("u2", "YAZ-1", "2027-03-08T10:00", "2027-03-08T10:30")
    sonuc = m.sorgu_kaynak("YAZ-1", "2027-03-08")
    turler = [o["tur"] for o in sonuc["doluluk"]]
    assert turler == ["REZERVASYON"]


def test_red_aciklamasi_cakisan_rezervasyonu_adlandirir():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")
    sonuc = m.rezervasyon("u2", "YAZ-1", "2027-03-08T10:30", "2027-03-08T11:30")
    assert sonuc["kod"] == "KESISME"
    mesaj = m.red_aciklamasi("u2", "YAZ-1", "2027-03-08T10:30", "2027-03-08T11:30", sonuc["kod"])
    assert r["rezervasyon_id"] in mesaj
    assert "10:00–11:00" in mesaj


def test_red_aciklamasi_hazirlik_ihlalinde_sureyi_ve_kaydi_verir():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")
    sonuc = m.rezervasyon("u2", "YAZ-1", "2027-03-08T11:00", "2027-03-08T12:00")
    assert sonuc["kod"] == "HAZIRLIK_IHLALI"
    mesaj = m.red_aciklamasi("u2", "YAZ-1", "2027-03-08T11:00", "2027-03-08T12:00", sonuc["kod"])
    assert "20 dk" in mesaj and r["rezervasyon_id"] in mesaj


def test_red_aciklamasi_sure_sinirinda_rol_azamisini_soyler():
    m = motor()
    sonuc = m.rezervasyon("u1", "ODA-1", "2027-03-08T09:00", "2027-03-08T13:00")
    assert sonuc["kod"] == "SURE_SINIRI"
    mesaj = m.red_aciklamasi("u1", "ODA-1", "2027-03-08T09:00", "2027-03-08T13:00", sonuc["kod"])
    assert "OGRENCI" in mesaj and "3 sa" in mesaj and "4 sa" in mesaj


def test_red_aciklamasi_rol_izninde_izinli_rolleri_listeler():
    m = motor()
    sonuc = m.rezervasyon("u1", "CIH-1", "2027-03-08T09:00", "2027-03-08T10:00")
    assert sonuc["kod"] == "ROL_IZNI_YOK"
    mesaj = m.red_aciklamasi("u1", "CIH-1", "2027-03-08T09:00", "2027-03-08T10:00", sonuc["kod"])
    assert "ARASTIRMACI" in mesaj and "OGRENCI" in mesaj


def test_red_aciklamasi_bilinmeyen_baglamda_genel_aciklamaya_duser():
    m = motor()
    mesaj = m.red_aciklamasi("yok", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00", "BULUNAMADI")
    assert mesaj == m.hata_aciklamasi("BULUNAMADI")


def test_uygun_araliklar_en_yakin_gecerli_saati_onerir():
    m = motor()
    m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")
    # 10:30–11:30 çakışır; YAZICI hazırlığı 20 dk → aynı süreyle en yakın 11:30–12:30
    oneriler = m.uygun_araliklar("u2", "YAZ-1", "2027-03-08T10:30", "2027-03-08T11:30")
    ilk = oneriler["zaman"][0]
    assert (ilk["kaynak"], ilk["baslangic"], ilk["bitis"]) == ("YAZ-1", "2027-03-08T11:30", "2027-03-08T12:30")
    assert len(oneriler["zaman"]) == 3
    for o in oneriler["zaman"]:
        assert m.fiyat("u2", o["kaynak"], o["baslangic"], o["bitis"])["durum"] == "TAMAM"


def test_uygun_araliklar_ayni_saatte_erisilebilir_diger_kaynagi_onerir():
    m = motor()
    m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")
    oneriler = m.uygun_araliklar("u2", "YAZ-1", "2027-03-08T10:30", "2027-03-08T11:30")
    # u2 (OGRENCI, sertifikasız): CIH-1 rol, LAB-1 sertifika yüzünden elenir
    assert [o["kaynak"] for o in oneriler["kaynak"]] == ["ODA-1"]


def test_uygun_araliklar_durum_degistirmez():
    m = motor()
    m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")
    once = m.sorgu_kullanici("u2")
    m.uygun_araliklar("u2", "YAZ-1", "2027-03-08T10:30", "2027-03-08T11:30")
    assert m.sorgu_kullanici("u2") == once
    assert len(m.depo.rezervasyonlar) == 1


def test_uygun_araliklar_gecersiz_girdide_bos_doner():
    m = motor()
    assert m.uygun_araliklar("u1", "YAZ-1", "bozuk", "2027-03-08T11:00") == {"zaman": [], "kaynak": []}
    assert m.uygun_araliklar("u1", "YAZ-1", "2027-03-08T11:00", "2027-03-08T10:00") == {"zaman": [], "kaynak": []}


def test_iptal_onizleme_durum_degistirmez():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-09T08:00", "2027-03-09T08:30")
    onizleme = m.iptal_onizleme(r["rezervasyon_id"])
    assert onizleme["oran"] == 100
    detay = m.rezervasyon_detayi(r["rezervasyon_id"])
    assert detay["durum"] == "ONAYLI"  # önizleme durumu değiştirmedi
