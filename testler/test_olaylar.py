from testler.yardimci import motor


def test_giris_b_eksi_10_tam_sinirda_gecerli():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")
    m.saat("2027-03-08T08:50")  # b - 10dk, tam sınır
    assert m.giris(r["rezervasyon_id"])["durum"] == "TAMAM"


def test_giris_b_eksi_11_penceresi_disi():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T09:00", "2027-03-08T09:30")
    m.saat("2027-03-08T08:49")  # b - 11dk, sınır dışı
    assert m.giris(r["rezervasyon_id"])["kod"] == "GIRIS_PENCERESI_DISI"


def test_saat_b_artı_15te_giris_durum_hatasi_doner():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T08:30")
    m.saat("2027-03-08T08:15")  # tam gelmeme anı
    assert m.giris(r["rezervasyon_id"])["kod"] == "DURUM_HATASI"


def test_kullanimda_rezervasyon_iptal_durum_hatasi():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T08:30")
    m.giris(r["rezervasyon_id"])
    assert m.iptal(r["rezervasyon_id"])["kod"] == "DURUM_HATASI"


def test_onayli_rezervasyona_cikis_durum_hatasi():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T08:30")
    assert m.cikis(r["rezervasyon_id"])["kod"] == "DURUM_HATASI"


def test_iptal_tam_24saat_tam_iade():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-09T08:00", "2027-03-09T08:30")
    bakiye_once = m.sorgu_kullanici("u1")["bakiye"]
    sonuc = m.iptal(r["rezervasyon_id"])
    assert sonuc["iade"] == r["ucret"]
    assert sonuc["guvenilirlik"] == 80
    assert m.sorgu_kullanici("u1")["bakiye"] == bakiye_once + r["ucret"]


def test_iptal_tam_2saat_yarim_iade_asagi_yuvarlanir():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T10:30")  # ücret tek sayı olacak şekilde
    sonuc = m.iptal(r["rezervasyon_id"])
    assert sonuc["iade"] == r["ucret"] // 2
    assert sonuc["guvenilirlik"] == 80


def test_iptal_1saat45_sifir_iade_ve_eksi5():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T09:45", "2027-03-08T10:15")
    sonuc = m.iptal(r["rezervasyon_id"])
    assert sonuc["iade"] == 0
    assert sonuc["guvenilirlik"] == 75


def test_iptal_baslangic_gecmis_sifir_iade_eksi5():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T08:30")
    m.saat("2027-03-08T08:05")
    sonuc = m.iptal(r["rezervasyon_id"])
    assert sonuc["iade"] == 0
    assert sonuc["guvenilirlik"] == 75


def test_bitiste_otomatik_tamamlandi_arti_2_clamp_100():
    m = motor(lambda v: v["kullanicilar"].__setitem__(0, {**v["kullanicilar"][0], "guvenilirlik": 99}))
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T08:30")
    m.giris(r["rezervasyon_id"])
    sonuc = m.saat("2027-03-08T08:30")
    olay = sonuc["olaylar"][0]
    assert olay["tur"] == "TAMAMLANDI" and olay["guvenilirlik"] == 100


def test_gelmedi_10dan_0a_clamp():
    m = motor(lambda v: v["kullanicilar"].__setitem__(0, {**v["kullanicilar"][0], "guvenilirlik": 10}))
    m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T08:30")
    sonuc = m.saat("2027-03-08T08:15")
    olay = sonuc["olaylar"][0]
    assert olay["tur"] == "GELMEDI" and olay["guvenilirlik"] == 0


def test_erken_cikis_guvenilirlik_degismez_bitis_guncellenir_bekleme_taranir():
    m = motor()
    # ODA (h=0) kullanıyoruz ki erken çıkış sonrası hazırlık kontrolü devreye girmesin
    r = m.rezervasyon("u1", "ODA-1", "2027-03-08T08:00", "2027-03-08T09:00")
    m.giris(r["rezervasyon_id"])
    m.bekleme("u2", "ODA-1", "2027-03-08T08:00", "2027-03-08T09:00")  # KESISME -> bekleme kaydı
    sonuc = m.cikis(r["rezervasyon_id"])
    assert sonuc["yeni_durum"] == "TAMAMLANDI"
    assert sonuc["guvenilirlik"] == 80
    assert len(sonuc["olaylar"]) == 1 and sonuc["olaylar"][0]["tur"] == "OTOMATIK_ATAMA"
    detay = m.rezervasyon_detayi(r["rezervasyon_id"])
    assert detay["bitis"] == "2027-03-08T08:00"


def test_saat_geri_red():
    m = motor()
    m.saat("2027-03-08T09:00")
    assert m.saat("2027-03-08T08:30")["kod"] == "SAAT_GERI"


def test_ayni_saate_ilerletme_bos_olay_listesi():
    m = motor()
    sonuc = m.saat("2027-03-08T08:00")
    assert sonuc["durum"] == "TAMAM" and sonuc["olaylar"] == []


def test_iki_farkli_kaynakta_ayni_anda_gelmedi_ikisi_de_raporlanir():
    m = motor()
    m.rezervasyon("u1", "YAZ-1", "2027-03-08T08:00", "2027-03-08T08:30")
    m.rezervasyon("u2", "ODA-1", "2027-03-08T08:00", "2027-03-08T08:30")
    sonuc = m.saat("2027-03-08T08:15")
    gelmedi_turleri = [o for o in sonuc["olaylar"] if o["tur"] == "GELMEDI"]
    assert len(gelmedi_turleri) == 2


def test_haftalik_sifirlama_iki_pazartesi_gecilirse_iki_olay():
    m = motor()
    sonuc = m.saat("2027-03-22T00:00")  # 2 hafta sonrası (8, 15, 22 mart pazartesi)
    sifirlamalar = [o for o in sonuc["olaylar"] if o["tur"] == "HAFTALIK_SIFIRLAMA"]
    assert len(sifirlamalar) == 2
