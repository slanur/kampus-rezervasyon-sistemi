"""Masaüstü uygulaması giriş noktası: python -m arayuz [baslangic.json]"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .ana_pencere import AnaPencere


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Kampüs Kaynak Rezervasyon Sistemi")
    ilk_dosya = sys.argv[1] if len(sys.argv) > 1 else None
    pencere = AnaPencere(ilk_dosya)
    pencere.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
