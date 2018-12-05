# -*- coding: utf-8 -*-

LOADING_RADIUS = 1

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel

class FrontQtLoadingWidget(QLabel):
    def __init__(self):
        QLabel.__init__(self)