# -*- coding: utf-8 -*-

import json
import urllib

import cv2

import common.models.model_routines as mr

from PyQt5.QtWidgets import qApp

from .ui_general_backend_session import BackendFrame, \
FrontQtGeneralBackendSession

from .ui_thread_request import FrontQtRequestThread

class FrontQtRemoteBackendSession(FrontQtGeneralBackendSession):
    def __init__(self, base_url, username = None, password = None):
        FrontQtGeneralBackendSession.__init__(self)
        
        self._request_thread = FrontQtRequestThread()
        self._request_thread.setRemoteAuthData(username, password)
        self._request_thread.finished.connect(self._requestThreadFinished)
        
        self._base_url = base_url
    
    def authenticate(self):
        self._request_thread.setRemoteUrl(
            urllib.parse.urljoin(self._base_url, 'autentication_check/')
        )
        self._request_thread.setRequestContent(b'')
        
        self._run_context = {
            'operation': 'autentication_check',
        }
        
        self._request_thread.start()
        while not self._request_thread.isFinished():
            qApp.processEvents()
        
        if self._request_thread.response() is None:
            return False
        
        return (self._request_thread.response().status_code == 200)
    
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
        
        request_dict =  {
            'image_from': mr.encode_image(frame_from_image_cv2),
            'image_to': mr.encode_image(frame_to_image_cv2),
            'color_points': frame_from_color_points
        }
        request_data = json.dumps(request_dict)
        
        self._request_thread.setRemoteUrl(
            urllib.parse.urljoin(self._base_url, 'extrapolate_points/')
        )
        self._request_thread.setRequestContent(request_data)
        
        self._run_context = {
            'operation': 'extrapolate_points',
            'original_image': frame_to_image_cv2.copy(),
            'color_points': frame_from_color_points
        }
        
        self._request_thread.start()
    
    def colorizeByPoints(self, frame):
        self._request_completed = False
        self._output_frame = None
        
        frame_image_cv2, frame_color_points = BackendFrame.frameToCv2(frame)
        
        request_dict =  {
            'image': mr.encode_image(frame_image_cv2),
            'color_points': frame_color_points
        }
        request_data = json.dumps(request_dict)
        
        self._request_thread.setRemoteUrl(
            urllib.parse.urljoin(self._base_url, 'colorize/')
        )
        self._request_thread.setRequestContent(request_data)
        
        self._run_context = {
            'operation': 'colorize',
            'original_image': frame_image_cv2.copy(),
            'color_points': frame_color_points
        }
        
        self._request_thread.start()
    
    def _requestThreadFinished(self):
        if self._run_context['operation'] == 'colorize':
            if self._request_thread.response() is None:
                self._output_frame = None
                self.disconnected.emit()
            elif self._request_thread.response().status_code != 200:
                self._output_frame = None
                self.disconnected.emit()
            else:
                try:
                    out_img = mr.decode_image(
                        self._request_thread.response().content
                    )
                    self._output_frame = BackendFrame.cv2ToFrame(
                        cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR),
                        self._run_context['color_points'][:]
                    )
                except Exception:
                    # Data corrupted
                    self._output_frame = None
                    self.disconnected.emit()
        elif self._run_context['operation'] == 'extrapolate_points':
            if self._request_thread.response() is None:
                self._output_frame = None
                self.disconnected.emit()
            elif self._request_thread.response().status_code != 200:
                self._output_frame = None
                self.disconnected.emit()
            else:
                try:
                    result_dict = json.loads(
                        self._request_thread.response().content
                    )
                    self._output_frame = BackendFrame.cv2ToFrame(
                        cv2.cvtColor(
                            mr.decode_image(result_dict['image']),
                            cv2.COLOR_RGB2BGR
                        ),
                        result_dict['color_points']
                    )
                except Exception:
                    # Data corrupted
                    self._output_frame = None
                    self.disconnected.emit()
        
        self._request_completed = True
        self.requestFinished.emit()
