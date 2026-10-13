from testler.yardimci import motor


def test_bulunamadi_kullanici():
    m = motor()
    assert m.rezervasyon("yok", "YAZ-1", "2027-03-08T11:00", "2027-03-08T12:00")["kod"] == "BULUNAMADI"


def test_bulunamadi_kaynak():
    m = motor()
    assert m.rezervasyon("u1", "yok", "2027-03-08T11:00", "2027-03-08T12:00")["kod"] == "BULUNAMADI"


def test_bitis_baslangica_esit_zaman_adimi_hatasi():
    m = motor()
    assert m.rezervasyon("u1", "YAZ-1", "2027-03-08T11:00", "2027-03-08T11:00")["kod"] == "ZAMAN_ADIMI_HATASI"


def test_baslangic_simule_saate_esit_gecerli():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T08:30")
    assert r["durum"] == "TAMAM"


def test_baslangic_simule_saatten_once_gecmis_zaman():
    m = motor()
    assert m.rezervasyon("u1", "YAZ-1", "2027-03-08T07:45", "2027-03-08T08:15")["kod"] == "GECMIS_ZAMAN"


def test_calisma_saati_21_22_gecerli():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T21:00", "2027-03-08T22:00")
    assert r["durum"] == "TAMAM"


def test_calisma_saati_disi_22_15():
    m = motor()
    assert m.rezervasyon("u1", "YAZ-1", "2027-03-08T21:30", "2027-03-08T22:15")["kod"] == "CALISMA_SAATI_DISI"


def test_calisma_saati_disi_07_45_baslangic():
    m = motor()
    assert m.rezervasyon("u1", "YAZ-1", "2027-03-08T07:45", "2027-03-08T08:30")["kod"] in (
        "GECMIS_ZAMAN",
        "CALISMA_SAATI_DISI",
    )


def test_gun_asimi_calisma_saati_disi():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T21:30", "2027-03-09T00:00")
    assert r["kod"] == "CALISMA_SAATI_DISI"


def test_sure_tam_30_dk_gecerli():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T11:00", "2027-03-08T11:30")
    assert r["durum"] == "TAMAM"


def test_sure_15_dk_cok_kisa():
    m = motor()
    assert m.rezervasyon("u1", "YAZ-1", "2027-03-08T11:00", "2027-03-08T11:15")["kod"] == "SURE_SINIRI"


def test_sure_azami_tam_gecerli():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T11:00")  # OGRENCI azami 180dk
    assert r["durum"] == "TAMAM"


def test_sure_azami_asildi():
    m = motor()
    assert m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T11:15")["kod"] == "SURE_SINIRI"


def test_ileri_tarih_sinirina_tam_esit_gecerli():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-15T08:00", "2027-03-15T08:30")
    assert r["durum"] == "TAMAM"


def test_ileri_tarih_siniri_asildi():
    m = motor()
    assert m.rezervasyon("u1", "YAZ-1", "2027-03-15T08:15", "2027-03-15T08:45")["kod"] == "ILERI_TARIH_SINIRI"


def test_guvenilirlik_49_ileri_tarih_1_gune_iner():
    m = motor(lambda v: v["kullanicilar"].__setitem__(0, {**v["kullanicilar"][0], "guvenilirlik": 49}))
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-09T08:00", "2027-03-09T08:30")
    assert r["durum"] == "TAMAM"
    assert m.rezervasyon("u1", "YAZ-1", "2027-03-09T09:00", "2027-03-09T09:30")["kod"] == "ILERI_TARIH_SINIRI"


def test_rol_sertifika_ikisi_de_eksik_once_rol_doner():
    m = motor()
    assert m.rezervasyon("u1", "CIH-1", "2027-03-08T11:00", "2027-03-08T12:00")["kod"] == "ROL_IZNI_YOK"


def test_sertifika_yok():
    m = motor()
    assert m.rezervasyon("u2", "LAB-1", "2027-03-08T11:00", "2027-03-08T12:00")["kod"] == "SERTIFIKA_YOK"


def test_bakim_10da_biten_rezervasyon_10da_baslayabilir():
    m = motor(lambda v: v["bakim_pencereleri"].append(
        {"kaynak": "YAZ-1", "baslangic": "2027-03-08T08:00", "bitis": "2027-03-08T10:00"}
    ))
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")
    assert r["durum"] == "TAMAM"


def test_hazirlik_oncesinde_bosluk_varsa_da_ihlal():
    m = motor()
    # mevcut: 14:00-16:00 (h=20 için YAZICI). Yeni talep ÖNCESİNDE 13:00-13:45, boşluk 15dk < 20dk
    m.rezervasyon("u3", "YAZ-1", "2027-03-08T14:00", "2027-03-08T16:00")
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T13:00", "2027-03-08T13:45")
    assert r["kod"] == "HAZIRLIK_IHLALI"


def test_oda_h0_bitisik_rezervasyon_gecerli():
    m = motor()
    m.rezervasyon("u1", "ODA-1", "2027-03-08T14:00", "2027-03-08T16:00")
    r = m.rezervasyon("u2", "ODA-1", "2027-03-08T16:00", "2027-03-08T17:00")
    assert r["durum"] == "TAMAM"


def test_tamamlandi_hazirlikta_sayilir_kesismede_sayilmaz():
    m = motor()
    # saat 08:00'de başlayan, giriş penceresi içinde kalan kısa bir rezervasyon
    r1 = m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T08:30")
    assert m.giris(r1["rezervasyon_id"])["durum"] == "TAMAM"
    cikis_sonuc = m.cikis(r1["rezervasyon_id"])  # erken çıkış: bitis = saat = 08:00
    assert cikis_sonuc["durum"] == "TAMAM"

    # YAZ-1'de artık TAMAMLANDI, bitiş 08:00 olan bir kayıt var. Aynı noktada başlayan
    # yeni talep onunla kesişmez (yarı açık aralık) ama hazırlık ihlali verebilir.
    sonuc = m.fiyat("u2", "YAZ-1", "2027-03-08T08:00", "2027-03-08T08:30")
    assert sonuc["kod"] != "KESISME"
    assert sonuc["kod"] == "HAZIRLIK_IHLALI"  # h=20, TAMAMLANDI hazırlıkta sayılır


def test_iptal_gelmedi_araligina_yeni_talep_gecerli():
    m = motor()
    r1 = m.rezervasyon("u1", "YAZ-1", "2027-03-08T11:00", "2027-03-08T12:00")
    m.iptal(r1["rezervasyon_id"])
    r2 = m.rezervasyon("u2", "YAZ-1", "2027-03-08T11:00", "2027-03-08T12:00")
    assert r2["durum"] == "TAMAM"


def test_bir_rezervasyonla_hazirlik_digeriyle_kesisme_kesisme_oncelikli():
    m = motor()
    # r1: 10:00-11:00 (ONAYLI). hazırlık 11:20'ye kadar.
    m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")
    # r2: 11:30-12:30 -> r1 ile sadece hazırlık ilişkisi var mı kontrol edelim (boşluk 30 < 20? hayır 30>20 ok)
    m.rezervasyon("u1", "YAZ-1", "2027-03-08T12:00", "2027-03-08T13:00")
    # yeni talep 11:00-12:15: r1 ile kesişmez (11:00>=11:00 kesişme sınırında), r2(12:00-13:00) ile kesişir
    r = m.rezervasyon("u2", "YAZ-1", "2027-03-08T11:00", "2027-03-08T12:15")
    assert r["kod"] == "KESISME"
