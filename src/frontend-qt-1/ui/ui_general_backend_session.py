# -*- coding: utf-8 -*-

import numpy as np

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QImage

class BackendFrame:
    def __init__(self, image, color_points = []):
        """ Represents frame (QImage) and corresponding color points. """
        self._image = image
        self._color_points = color_points
    
    def image(self):
        return self._image
    
    def color_points(self):
        return self._color_points
    
    @staticmethod
    def frameToCv2(frame):
        incoming_image = frame.image().rgbSwapped()
        ptr = incoming_image.constBits()
        ptr.setsize(incoming_image.byteCount())
        
        image_cv2 = np.array(ptr, dtype = np.uint8).reshape(
            (frame.image().height(), frame.image().width(), 3)
        )
        
        return image_cv2, frame.color_points()
    
    @staticmethod
    def cv2ToFrame(cv2_image, color_points = []):
        image = QImage(
            cv2_image.data,
            cv2_image.shape[1], cv2_image.shape[0],
            QImage.Format_RGB888
        ).rgbSwapped()
        return BackendFrame(image, color_points)

class FrontQtGeneralBackendSession(QObject):
    requestFinished = pyqtSignal()
    disconnected = pyqtSignal()
    
    def __init__(self):
        QObject.__init__(self)
        
        self._run_context = {}
        
        self._request_completed = False
        self._output_frame = None
    
    def authenticate(self):
        return False
    
    def extrapolateColorPoints(self, frame_from, frame_to):
        raise Exception('Not implemented')
    
    def colorizeByPoints(self, frame):
        raise Exception('Not implemented')
    
    def isCompleted(self):
        return self._request_completed
    
    def outputFrame(self):
        return self._output_frame
