# -*- coding: utf-8 -*-

import common.models.model_routines as mr

from .ui_general_backend_session import BackendFrame, \
FrontQtGeneralBackendSession

from .ui_thread_inference import FrontQtInferenceThread

class FrontQtLocalBackendSession(FrontQtGeneralBackendSession):
    def __init__(self, model):
        FrontQtGeneralBackendSession.__init__(self)
        
        self._model_thread = FrontQtInferenceThread(model)
        self._model_thread.finished.connect(self._modelThreadFinished)
    
    def setModel(self, model):
        self._model_thread.setModel(model)
    
    def model(self):
        return self._model_thread.model()
    
    def authenticate(self):
        return (self.model() is not None)
    
    def extrapolateColorPoints(self, frame_from, frame_to):
        self._request_completed = False
        self._output_frame = None
        
        # Extract necessary images and points
        frame_from_image_cv2, frame_from_color_points = \
            BackendFrame.frameToCv2(frame_from)
        
        # Don't extrapolate if there are no points
        if len(frame_from_color_points) == 0:
            self._output_frame = BackendFrame(
                frame_to.image(), []
            )
            self._request_completed = True
            self.requestFinished.emit()
            return
        
        frame_to_image_cv2, _ = BackendFrame.frameToCv2(frame_to)
        
        new_points = mr.extrapolatePoints(
            frame_from_image_cv2, frame_from_color_points, frame_to_image_cv2
        )
        
        output_frame = BackendFrame(frame_to.image(), new_points)
        self.colorizeByPoints(output_frame)
    
    def colorizeByPoints(self, frame):
        self._request_completed = False
        self._output_frame = None
        
        frame_image_cv2, frame_color_points = BackendFrame.frameToCv2(frame)
        
        incoming_frame_gray_cv2, frame_image_l, im_mask0, im_ab0 = \
            mr.preprocessColorization(
                frame_image_cv2, frame_color_points,
                self.model().Xd
            )
        
        self.model().set_image(incoming_frame_gray_cv2)
        self._model_thread.setForwardArgsList([im_ab0, im_mask0])
        
        self._run_context = {
            'operation': 'colorize',
            'frame_l': frame_image_l.copy(),
            'color_points': frame_color_points
        }
        
        self._model_thread.start()
    
    def _modelThreadFinished(self):
        if self._run_context['operation'] == 'colorize':
            out_img = mr.postprocessColorization(
                self._run_context['frame_l'], self.model().output_ab
            )
            
            model_output_frame = BackendFrame.cv2ToFrame(
                out_img, self._run_context['color_points']
            )
            
            self._output_frame = BackendFrame(
                model_output_frame.image().rgbSwapped(),
                model_output_frame.color_points()
            )
        
        self._request_completed = True
        self.requestFinished.emit()
