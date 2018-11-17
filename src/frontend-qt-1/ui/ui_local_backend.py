# -*- coding: utf-8 -*-

import numpy as np
import cv2

from skimage import color as skcl

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QImage

from .ui_thread_inference import FrontQtInferenceThread

class BackendFrame:
    def __init__(self, image, color_points = []):
        """ Represents frame (QImage) and corresponding color points. """
        self._image = image
        self._color_points = color_points
    
    def image(self):
        return self._image
    
    def color_points(self):
        return self._color_points

class FrontQtLocalBackend(QObject):
    inferenceFinished = pyqtSignal()
    
    def __init__(self, model, model_context):
        QObject.__init__(self)
        
        self._inference_completed = False
        self._run_context = {}
        self._output_frame = None
        
        self._model_thread = FrontQtInferenceThread()
        self._model_thread.finished.connect(self._modelThreadFinished)
        self.setModel(model, model_context)
    
    def setModel(self, model, model_context):
        self._model = model
        self._model_context = model_context
        self._model_thread.setModel(model)
    
    def model(self):
        return self._model
    
    def modelContext(self):
        return self._model_context
    
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
    
    def makeGrayscale(self, frame):
        self._inference_completed = False
        self._output_frame = None
        frame_image_cv2, frame_color_points = self.frameToCv2(frame)
        frame_image_gray3_cv2 = cv2.cvtColor(
            frame_image_cv2, cv2.COLOR_BGR2GRAY
        )
        self._output_frame = self.cv2ToFrame(
            frame_image_gray3_cv2, frame_color_points
        )
        self._inference_completed = True
        self.inferenceFinished.emit()
    
    def extrapolateColorPoints(self, frame_from, frame_to):
        self._inference_completed = False
        self._output_frame = None
        
        # Extract necessary images and points
        frame_from_image_cv2, frame_from_color_points = self.frameToCv2(
            frame_from
        )
        
        # Don't extrapolate if there are no points
        if len(frame_from_color_points) == 0:
            self._output_frame = BackendFrame(
                frame_to.image(), []
            )
            self._inference_completed = True
            self.inferenceFinished.emit()
            return
        
        frame_to_image_cv2, _ = self.frameToCv2(frame_to)
        
        old_gray = cv2.cvtColor(
            frame_from_image_cv2, cv2.COLOR_BGR2GRAY
        )
        new_gray = cv2.cvtColor(
            frame_to_image_cv2, cv2.COLOR_BGR2GRAY
        )
        
        lk_params = dict(
            winSize = (15, 15), maxLevel = 2,
            criteria = (
                cv2.TermCriteria_EPS | cv2.TermCriteria_COUNT, 10, 0.03
            )
        )
        
        old_points = np.array(
            [[[p['x'], p['y']]] for p in frame_from_color_points]
        ).astype(np.float32)
        new_points, st_new, err = cv2.calcOpticalFlowPyrLK(
            old_gray, new_gray, old_points, None, **lk_params
        )
        new_points = new_points[:, 0, :]
        
        ERROR_THRESHOLD = 1e5
        image_size = np.array(new_gray.shape[::-1], dtype = np.int)
        
        # Mark points excluded by algo
        valid_points = (st_new.flatten() > 0)
        # Mark points excluded by error threshold
        valid_points &= (err.flatten() < ERROR_THRESHOLD)
        
        # Round and neighbour-adjust new pixels
        new_pixels = new_points.round().astype(np.int)
        new_pixels[new_pixels >= image_size] -= 1
        new_pixels[new_pixels < 0] += 1
        
        # Mark pixels out of frame rect
        valid_points &= (new_pixels >= 0).all(axis = 1).flatten()
        valid_points &= (new_pixels < image_size).all(axis = 1).flatten()
        
        new_points = [
            {
                'x': new_pixels[i, 0], 'y': new_pixels[i, 1],
                'color': frame_from_color_points[i]['color']
            } for i in range(len(frame_from_color_points)) if valid_points[i]
        ]
        
        self._output_frame = BackendFrame(frame_to.image(), new_points)
        self._inference_completed = True
        self.inferenceFinished.emit()
    
    def colorizeByPoints(self, frame):
        self._inference_completed = False
        self._output_frame = None
        
        w = int(max((
            frame.image().width(), frame.image().height()
        )) / self._model_context['load_size'])
        
        frame_image_cv2, frame_color_points = self.frameToCv2(frame)
        frame_image_gray3_cv2 = cv2.cvtColor(
            cv2.cvtColor(frame_image_cv2, cv2.COLOR_BGR2GRAY),
            cv2.COLOR_GRAY2RGB
        )
        
        incoming_frame_gray_cv2 = cv2.resize(
            frame_image_gray3_cv2, (
                self._model_context['load_size'],
                self._model_context['load_size']
            ),
            interpolation = cv2.INTER_CUBIC
        )
        
        im = np.zeros(incoming_frame_gray_cv2.shape, dtype = np.uint8)
        mask = np.zeros(
            tuple(list(incoming_frame_gray_cv2.shape[:-1]) + [1]),
            dtype = np.uint8
        )
        
        for color_point in frame_color_points:
            point = (
                np.array([color_point['x'], color_point['y']]) *
                self._model_context['load_size'] /
                np.array(frame_image_cv2.shape[1::-1])
            ).astype(np.uint)
            
            tl = tuple((point - w).tolist())
            br = tuple((point + w).tolist())
            
            cv2.rectangle(mask, tl, br, 255, -1)
            cv2.rectangle(
                im, tl, br,
                [
                    color_point['color'][0], color_point['color'][1],
                    color_point['color'][2]
                ],
                -1
            )
            
        im_mask0 = (mask > 0.0).transpose((2, 0, 1))
        im_ab0 = skcl.rgb2lab(im).transpose((2, 0, 1))[1:3, :, :]
        
        self._model.set_image(incoming_frame_gray_cv2)
        self._model_thread.setForwardArgsList([im_ab0, im_mask0])
        
        frame_image_l = skcl.rgb2lab(frame_image_cv2)[:, :, 0]
        
        self._run_context = {
            'operation': 'colorize',
            'frame_l': frame_image_l.copy(),
            'color_points': frame_color_points
        }
        
        self._model_thread.start()
    
    def _modelThreadFinished(self):
        if self._run_context['operation'] == 'colorize':
            out_ab = self._model.output_ab.transpose((1, 2, 0))
            out_ab = cv2.resize(
                out_ab, self._run_context['frame_l'].shape[::-1],
                interpolation = cv2.INTER_CUBIC
            )
            out_lab = np.concatenate(
                (self._run_context['frame_l'][..., np.newaxis], out_ab),
                axis = 2
            )
            out_img = (np.clip(skcl.lab2rgb(out_lab), 0, 1) * 255).astype(
                np.uint8
            )
            
            model_output_frame = self.cv2ToFrame(
                out_img, self._run_context['color_points']
            )
            
            self._output_frame = BackendFrame(
                model_output_frame.image().rgbSwapped(),
                model_output_frame.color_points()
            )
        
        self._inference_completed = True
        self.inferenceFinished.emit()
    
    def isCompleted(self):
        return self._inference_completed
    
    def outputFrame(self):
        return self._output_frame
