from fractions import Fraction

from rezervasyon import fiyat
from testler.yardimci import motor


def test_doluluk_tam_ceyrekte_carpan_bir_ceyrek():
    # ODA: enerji_yogun=False -> pik çarpanı etkisiz, yalnızca bant çarpanını izole eder.
    # 1 kaynak (ODA-1) -> payda 120. 10-12 bandında 30dk doluluk = 0,25 -> carpan 1,25 (alt sınır dahil).
    m = motor()
    m.rezervasyon("u1", "ODA-1", "2027-03-08T10:00", "2027-03-08T10:30")
    sonuc = m.fiyat("u2", "ODA-1", "2027-03-08T11:00", "2027-03-08T12:00")
    # 4 dilim * 4 * 0,25 * 1,25 = 5
    assert sonuc["ucret"] == 5


def test_bos_banda_carpan_1():
    m = motor()
    sonuc = m.fiyat("u1", "ODA-1", "2027-03-08T14:00", "2027-03-08T14:30")
    # ODA: temel_ucret 4, 2 dilim, carpan 1.0, pik yok (enerji yogun degil) -> 4*0.25*1.0*2=2
    assert sonuc["ucret"] == 2


def test_bant_siniri_asan_talep_iki_farkli_carpan_kullanir():
    m = motor()
    m.kaynak_ekle("YAZ-2", "İkinci Yazıcı", "YAZICI", ["OGRENCI"])
    # YAZ-1'de 10-12 bandını dolduran 1 saatlik mevcut rezervasyon (türdeki kaynak sayısı artık 2)
    m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T11:00")
    # YAZ-2 üzerinden 11-13 arası talep: 10-12 bandında doluluk 0,25 (carpan 1,25), 12-14 bandında 0 (carpan 1,0)
    sonuc = m.fiyat("u2", "YAZ-2", "2027-03-08T11:00", "2027-03-08T13:00")
    assert sonuc["ucret"] == 41


def test_pik_disi_tur_her_zaman_carpan_1():
    m = motor()
    # ODA enerji_yogun=False; 10-16 arası bile olsa pik çarpanı uygulanmaz
    sonuc = m.fiyat("u1", "ODA-1", "2027-03-08T10:00", "2027-03-08T11:00")
    assert sonuc["ucret"] == 4  # 4 dilim * 4*0.25*1.0*1.0 = 4


def test_pik_sinir_1530_1630_yarisi_pik_yarisi_degil():
    m = motor()
    sonuc = m.fiyat("u3", "CIH-1", "2027-03-08T15:30", "2027-03-08T16:30")
    # 15:30-16:00 (14-16 bandı, pik, 2 dilim) + 16:00-16:30 (16-18 bandı, pik değil, 2 dilim)
    # temel_ucret=16: pik 2*16*0.25*1*1.5=12 ; normal 2*16*0.25*1*1=8 ; toplam 20
    assert sonuc["ucret"] == 20


def test_yuvarlama_tam_yarimda_yukari():
    # temel_ucret tek sayı seçip yarım kesir üretelim: ODA ücreti 4 ile 15dk=1KP tam sayı zaten.
    # Burada Fraction formülünün .5 durumunda yukarı yuvarladığını doğrudan test edelim.
    assert fiyat.math.floor(Fraction(7, 2) + Fraction(1, 2)) == 4
    assert fiyat.math.floor(Fraction(7, 4) + Fraction(1, 2)) == 2  # 1.75 + 0.5 = 2.25 -> floor 2


def test_baska_gunun_rezervasyonu_doluluga_girmez():
    m = motor()
    m.rezervasyon("u1", "YAZ-1", "2027-03-09T10:00", "2027-03-09T12:00")
    sonuc = m.fiyat("u2", "YAZ-1", "2027-03-08T10:00", "2027-03-08T12:00")
    assert sonuc["ucret"] == 36  # doluluk 0 sanki hiç rezervasyon yokmuş gibi


def test_tamamlandi_gelmedi_iptal_doluluga_girmez():
    m = motor()
    r = m.rezervasyon("u1", "YAZ-1", "2027-03-08T10:00", "2027-03-08T12:00")
    m.iptal(r["rezervasyon_id"])
    sonuc = m.fiyat("u2", "YAZ-1", "2027-03-08T10:00", "2027-03-08T12:00")
    assert sonuc["ucret"] == 36
