# -*- coding: utf-8 -*-

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QFormLayout, \
    QVBoxLayout, QRadioButton

class FrontQtDialogConnectBackend(QDialog):
    
    def _createDialogLayout(self):
        self._rbtnLocal = QRadioButton()
        self._rbtnLocal.setText('Local backend')
        self._rbtnLocal.setChecked(True)
        self._rbtnLocal.toggled.connect(self._updateRemoteForm)
        
        self._rbtnRemote = QRadioButton()
        self._rbtnRemote.setText('Remote backend')
        self._rbtnRemote.setChecked(False)
        self._rbtnRemote.toggled.connect(self._updateRemoteForm)
        
        self._ledRemoteURL = QLineEdit()
        self._ledRemoteURL.setMinimumWidth(200)
        
        self._ledRemoteUser = QLineEdit()
        self._ledRemoteUser.setMinimumWidth(200)
        
        self._ledRemotePass = QLineEdit()
        self._ledRemotePass.setMinimumWidth(200)
        self._ledRemotePass.setEchoMode(QLineEdit.Password)
        
        formLayout = QFormLayout()
        formLayout.addRow('URL:', self._ledRemoteURL)
        formLayout.addRow('Username:', self._ledRemoteUser)
        formLayout.addRow('Password:', self._ledRemotePass)
        
        regions_layout = QVBoxLayout()
        regions_layout.addWidget(self._rbtnLocal)
        regions_layout.addWidget(self._rbtnRemote)
        regions_layout.addLayout(formLayout)
        
        self._bboxDialogButtons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal
        )
        self._bboxDialogButtons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self._bboxDialogButtons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        
        dialogLayout = QVBoxLayout()
        dialogLayout.addLayout(regions_layout)
        dialogLayout.addWidget(self._bboxDialogButtons)
        
        self.setLayout(dialogLayout)
        self._resetDialog()
    
    def _resetDialog(self):
        self._rbtnLocal.setChecked(True)
        self._rbtnRemote.setChecked(False)
        self._ledRemoteURL.setText('http://127.0.0.1:80')
        self._ledRemoteUser.clear()
        self._ledRemotePass.clear()
        self._updateRemoteForm()
    
    def _updateRemoteForm(self):
        self._ledRemoteURL.setEnabled(self._rbtnRemote.isChecked())
        self._ledRemoteUser.setEnabled(self._rbtnRemote.isChecked())
        self._ledRemotePass.setEnabled(self._rbtnRemote.isChecked())
    
    def getBackendInfo(self):
        if self._rbtnLocal.isChecked():
            return {'type': 'local', 'url': '', 'user': '', 'pass': ''}
        else:
            return {
                'type': 'remote',
                'url': self._ledRemoteURL.text(),
                'user': self._ledRemoteUser.text(),
                'pass': self._ledRemotePass.text()
            }
    
    def showEvent(self, event):
        self._ledRemotePass.clear()
    
    def __init__(self, parent = None):
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        
        self._createDialogLayout()
        self.setWindowTitle('Connect to backend')
