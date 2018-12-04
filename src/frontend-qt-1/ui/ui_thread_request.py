# -*- coding: utf-8 -*-

import requests

from PyQt5.QtCore import QThread

class FrontQtRequestThread(QThread):
    def __init__(self):
        QThread.__init__(self)
        
        self._response = None
        self._request_content = b''
        
        self.setRemoteUrl(None)
        self.setRemoteAuthData(None, None)
    
    def __del__(self):
        self.wait()
    
    def setRemoteUrl(self, url):
        self._remote_url = url
    
    def remoteUrl(self):
        return self._remote_url
    
    def setRemoteAuthData(self, username, password):
        self._remote_username = username
        self._remote_password = password
    
    def remoteAuthData(self):
        return (self._remote_username, self._remote_password)
    
    def setRequestContent(self, content):
        self._request_content = content
    
    def requestContent(self):
        return self._request_content
    
    def response(self):
        return self._response
    
    def run(self):
        if self._remote_url is not None:
            auth_details = (
                None if self._remote_username is None else
                requests.auth.HTTPBasicAuth(
                    self._remote_username, self._remote_password
                )
            )
            try:
                self._response = requests.post(
                    self._remote_url, data = self._request_content,
                    headers = {'content-type': 'application/json'},
                    auth = auth_details
                )
            except requests.ConnectionError:
                self._response = None
