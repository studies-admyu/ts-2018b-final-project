#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

from PyQt5.QtWidgets import QApplication

from data import colorize_image as CI

from ui.ui_window_main import FrontQtWindowMain

MODEL_CONTEXT = {
    'gpu_id': -1,
    'load_size': 256,
    'pretrained_model': (
        'pretrained_models/checkpoints/siggraph_pretrained/' +
        'latest_net_G.pth'
    )
}

if __name__ == '__main__':
    if not os.path.exists(MODEL_CONTEXT['pretrained_model']):
        sys.stderr.write(
            'ERROR: Unable to find pretrained model in %s\n' % (
                MODEL_CONTEXT['pretrained_model']
            )
        )
        sys.exit(1)
    
    # Init model first
    colorization_model = CI.ColorizeImageTorch(
        Xd = MODEL_CONTEXT['load_size']
    )
    colorization_model.prep_net(
        MODEL_CONTEXT['gpu_id'], MODEL_CONTEXT['pretrained_model']
    )
    
    # Init QApplication then
    app = QApplication(sys.argv)
    window = FrontQtWindowMain(colorization_model, MODEL_CONTEXT)
    window.show()
    sys.exit(app.exec_())
