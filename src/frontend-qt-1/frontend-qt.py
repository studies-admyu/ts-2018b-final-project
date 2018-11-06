#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from PyQt5.QtWidgets import QApplication

from ui.ui_window_main import FrontQtWindowMain

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FrontQtWindowMain()
    window.show()
    sys.exit(app.exec_())
