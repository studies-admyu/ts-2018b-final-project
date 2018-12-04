# -*- coding: utf-8 -*-

import sys

from PyQt5.QtWidgets import QApplication

import common.models.model_routines as mr
from ui.ui_window_main import FrontQtWindowMain

if __name__ == '__main__':
    try:
        pretrained_path = mr.PRETRAINED_DEFAULT_PATH
        colorization_model = mr.init_model(
            pretrained_path = pretrained_path
        )
    except FileNotFoundError:
        sys.stderr.write(
            'ERROR: Unable to find pretrained model in %s\n' % (
                pretrained_path
            )
        )
        sys.exit(1)
    
    # Init QApplication then
    app = QApplication(sys.argv)
    window = FrontQtWindowMain(colorization_model)
    window.showMaximized()
    sys.exit(app.exec_())
