# -*- coding: utf-8 -*-

from PyQt5.QtCore import QThread

class FrontQtInferenceThread(QThread):
    def __init__(self, model = None):
        QThread.__init__(self)
        self.setModel(model)
        self.setForwardArgsList([])
    
    def __del__(self):
        self.wait()
    
    def setModel(self, model):
        self._model = model
    
    def model(self):
        return self._model
    
    def setForwardArgsList(self, args_list):
        self._args_list = args_list
    
    def forwardArgsList(self):
        return self._args_list
    
    def run(self):
        if (self._model is not None) and isinstance(self._args_list, list):
            self._model.net_forward(*self._args_list)
