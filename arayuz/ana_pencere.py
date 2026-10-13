"""Ana pencere — tek bir `QWebEngineView` barındırır.

Arayüz HTML/CSS/JS ile çizilir (`arayuz/web/`); Python tarafı yalnızca
`Kopru` (QWebChannel) üzerinden çekirdek modülün fonksiyonlarını JS'e
açar. İş kuralı burada da, JS'te de bulunmaz — hepsi `rezervasyon/`
paketindedir (Bölüm 12-13, PROJE_ANALIZI.md).
"""
from __future__ import annotations

import os

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow

from .kopru import Kopru
from .oturum import Oturum

_WEB_KOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class AnaPencere(QMainWindow):
    def __init__(self, ilk_dosya: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Kampüs Kaynak Rezervasyon Sistemi")

        istenen_genislik, istenen_yukseklik = 1560, 940
        self.setMinimumSize(1000, 620)

        ekran = QGuiApplication.primaryScreen()
        kullanilabilir = ekran.availableGeometry() if ekran else None
        if kullanilabilir is not None and (
            kullanilabilir.width() < istenen_genislik + 60
            or kullanilabilir.height() < istenen_yukseklik + 60
        ):
            # Ekran istenen boyuttan küçükse pencere ekranın dışına taşıp alt
            # kısmı erişilemez hale gelir (OS pencereyi kırpar, sayfa içi
            # kaydırma bunu çözmez) — bu durumda tam ekran açılır.
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.resize(istenen_genislik, istenen_yukseklik)
            self.move(
                kullanilabilir.x() + (kullanilabilir.width() - istenen_genislik) // 2,
                kullanilabilir.y() + (kullanilabilir.height() - istenen_yukseklik) // 2,
            )

        self._oturum = Oturum()
        self._ilk_dosya = os.path.abspath(ilk_dosya) if ilk_dosya else None

        self._view = QWebEngineView(self)
        self.setCentralWidget(self._view)

        self._kopru = Kopru(self._oturum, self, self._ilk_dosya)
        self._kanal = QWebChannel(self._view.page())
        self._kanal.registerObject("kopru", self._kopru)
        self._view.page().setWebChannel(self._kanal)

        index_yolu = os.path.join(_WEB_KOK, "index.html")
        self._view.load(QUrl.fromLocalFile(index_yolu))
