"""Proje dokümanında sabit geçen tüm sayısal kurallar burada tutulur.

Tür/rol/kaynak adları, kotalar ve ücretler burada YOKTUR — onlar başlangıç
dosyasından okunur. Bu dosyadaki değerler yalnızca dokümanın "kural" olarak
tanımladığı, parametreleştirilmeyen sabitlerdir (K1-K11).
"""
from fractions import Fraction

DILIM_DK = 15
ASGARI_SURE_DK = 30
CALISMA_BASLANGIC = (8, 0)     # 08:00
CALISMA_BITIS = (22, 0)        # 22:00

# K5 — ücret bantları (saat, saat) yarı açık [bas, bit)
BANTLAR = [(8, 10), (10, 12), (12, 14), (14, 16), (16, 18), (18, 20), (20, 22)]
PIK_BASLANGIC = 10
PIK_BITIS = 16
PIK_CARPAN = Fraction(3, 2)
NORMAL_CARPAN = Fraction(1, 1)

# K8 — giriş penceresi, gelmeme eşiği
GIRIS_PENCERESI_ONCE_DK = 10
GIRIS_PENCERESI_SONRA_DK = 15
GELMEDI_ESIK_DK = 15

# K4 — art arda kullanım boşluğu
ARDISIK_BOSLUK_DK = 60

# K6 — iade tablosu eşikleri (saat)
IADE_TAM_SINIR_SAAT = 24
IADE_YARIM_SINIR_SAAT = 2

# K8 — güvenilirlik delta değerleri
GUVENILIRLIK_GELMEDI = -15
GUVENILIRLIK_GEC_IPTAL = -5
GUVENILIRLIK_TAMAMLANDI = 2
GUVENILIRLIK_ERKEN_CIKIS = 0
GUVENILIRLIK_MIN = 0
GUVENILIRLIK_MAX = 100
GUVENILIRLIK_ESIK = 50          # altındaysa ileri tarih 1 güne iner, paket yasak
ILERI_TARIH_DUSUK_GUVENILIRLIK_GUN = 1

# K7 — paket boyutu
PAKET_MIN_KALEM = 2
PAKET_MAX_KALEM = 4

# Zaman biçimi
ZAMAN_BICIMI = "%Y-%m-%dT%H:%M"
GUN_BICIMI = "%Y-%m-%d"
