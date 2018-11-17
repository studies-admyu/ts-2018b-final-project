# -*- coding: utf-8 -*-

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QFormLayout, \
    QHBoxLayout, QVBoxLayout, QPushButton, QFileDialog

class FrontQtDialogNewProject(QDialog):
    
    def _createDialogLayout(self):
        self._ledVideoPath = QLineEdit()
        self._ledVideoPath.setMinimumWidth(200)
        self._ledVideoPath.setText('')
        
        self._btnVideoOpen = QPushButton()
        self._btnVideoOpen.setText('...')
        self._btnVideoOpen.adjustSize()
        self._btnVideoOpen.clicked.connect(self._selectVideoFile)
        
        fileLayout = QHBoxLayout()
        fileLayout.addWidget(self._ledVideoPath)
        fileLayout.addWidget(self._btnVideoOpen)
        
        formLayout = QFormLayout()
        formLayout.addRow('Input video:', fileLayout)
        
        self._bboxDialogButtons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal
        )
        self._bboxDialogButtons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self._bboxDialogButtons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        
        dialogLayout = QVBoxLayout()
        dialogLayout.addLayout(formLayout)
        dialogLayout.addWidget(self._bboxDialogButtons)
        
        self.setLayout(dialogLayout)
    
    def _selectVideoFile(self):
        input_video_filename = QFileDialog.getOpenFileName(self, 'Open input video')
        if len(input_video_filename[0]) > 0:
            self._ledVideoPath.setText(input_video_filename[0])
    
    def _resetDialog(self):
        self._ledVideoPath.clear()
    
    def getVideoFilename(self):
        return self._ledVideoPath.text()
        
    def __init__(self, parent = None):
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        
        self._createDialogLayout()
        self.setWindowTitle('New project')
