# -*- coding: utf-8 -*-

from PyQt5.QtCore import Qt, QSignalMapper
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMainWindow, QAction, QMenu, QMessageBox, qApp, \
    QLabel, QDockWidget, QToolButton, QPushButton, QGridLayout, QFrame, \
    QColorDialog, QStackedWidget

from .ui_dialog_new_project import FrontQtDialogNewProject
from .ui_widget_video_frame_editor import FrontQtVideoFrameEditor

class FrontQtWindowMain(QMainWindow):
    
    def _createDialogs(self):
        self._dlgNewProject = FrontQtDialogNewProject(self)
    
    def _createActions(self):
        self._actNew = QAction('&New project...')
        self._actNew.triggered.connect(self._newProject)
        
        self._actOpen = QAction('&Open project...')
        self._actOpen.setEnabled(False) # Not implemented
        
        self._actSave = QAction('&Save project')
        self._actSave.setEnabled(False) # Not implemented
        
        self._actSaveAs = QAction('Save project &as...')
        self._actSaveAs.setEnabled(False) # Not implemented
        
        self._actQuit = QAction('&Quit')
        self._actQuit.triggered.connect(self.close)
        
        self._actAbout = QAction('&About...')
        self._actAbout.triggered.connect(self.about)
        
        self._actAboutQt = QAction('About Qt...')
        self._actAboutQt.triggered.connect(qApp.aboutQt)
    
    def _createMenu(self):
        self._mnuFile = QMenu('&File')
        self._mnuFile.addAction(self._actNew)
        self._mnuFile.addAction(self._actOpen)
        self._mnuFile.addAction(self._actSave)
        self._mnuFile.addAction(self._actSaveAs)
        self._mnuFile.addSeparator()
        self._mnuFile.addAction(self._actQuit)
        
        self._mnuView = QMenu('&View')
        
        self._mnuHelp = QMenu('&Help')
        self._mnuHelp.addAction(self._actAbout)
        self._mnuHelp.addAction(self._actAboutQt)
        
        self.menuBar().addMenu(self._mnuFile)
        self.menuBar().addMenu(self._mnuView)
        self.menuBar().addMenu(self._mnuHelp)
    
    def _createBackground(self):
        self._wgtFrameEditor = FrontQtVideoFrameEditor()
        self._wgtFrameEditor.frame_mouse_move.connect(self._frameMouseMove)
        self._wgtFrameEditor.frame_mouse_leave.connect(self._frameMouseLeave)
        self._wgtFrameEditor.frame_eyedropper_color.connect(
            self._setPickedColor
        )
        
        self.setCentralWidget(self._wgtFrameEditor)
    
    def _createStatusBar(self):
        self._lblImagePos = QLabel()
        self._lblImagePos.setText('X: 9999 Y: 9999')
        self._lblImagePos.adjustSize()
        self._lblImagePos.setFixedWidth(self._lblImagePos.width())
        self._lblImagePos.setText('')
        
        self.statusBar().addPermanentWidget(self._lblImagePos)
    
    def _createPaintDock(self):
        self._dwgPaint = QDockWidget('Painting', self)
        self._dwgPaint.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        
        dockLayout = QGridLayout()
        
        self._btnCurrentColor = QPushButton()
        self._btnCurrentColor.setToolTip('Pick point color')
        self._btnCurrentColor.setAutoFillBackground(True)
        self._btnCurrentColor.clicked.connect(self._pickPointColor)
        dockLayout.addWidget(self._btnCurrentColor, 0, 0, 1, 3)
        
        self._sgmToolSignalMapper = QSignalMapper(self)
        self._sgmToolSignalMapper.mapped.connect(self._changeEditMode)
        self._toolButtons = { k: QToolButton() for k in self._toolKeyList }
        for i, key in enumerate(self._toolKeyList):
            if key ==  self._wgtFrameEditor.EDIT_MODE_HAND:
                self._toolButtons[key].setToolTip('Hand')
                row, col = 1, 0
            elif key == self._wgtFrameEditor.EDIT_MODE_EYEDROPPER:
                self._toolButtons[key].setToolTip('Eyedropper')
                row, col = 1, 2
            elif key == self._wgtFrameEditor.EDIT_MODE_ADD_POINT:
                self._toolButtons[key].setToolTip('Add color point')
                row, col = 2, 0
            elif key == self._wgtFrameEditor.EDIT_MODE_EDIT_POINT:
                self._toolButtons[key].setToolTip('Edit color point')
                row, col = 2, 1
            elif key == self._wgtFrameEditor.EDIT_MODE_REMOVE_POINT:
                self._toolButtons[key].setToolTip('Remove color point')
                row, col = 2, 2
            self._toolButtons[key].setCheckable(True)
            self._sgmToolSignalMapper.setMapping(self._toolButtons[key], key)
            self._toolButtons[key].clicked.connect(self._sgmToolSignalMapper.map)
            dockLayout.addWidget(self._toolButtons[key], row, col)
        
        dockFrame = QFrame()
        dockFrame.setLayout(dockLayout)
        
        self._dwgPaint.setWidget(dockFrame)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._dwgPaint)
        self._mnuView.addAction(self._dwgPaint.toggleViewAction())
    
    def _createViewDock(self):
        self._dwgView = QDockWidget('Colorization', self)
        self._dwgView.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        
        dockLayout = QGridLayout()
        
        self._sgmSceneModeSignalMapper = QSignalMapper(self)
        self._sgmSceneModeSignalMapper.mapped.connect(self._changeSceneMode)
        self._sceneModeButtons = {
            k: QToolButton() for k in self._sceneModesList
        }
        for i, key in enumerate(self._sceneModesList):
            if key ==  self._wgtFrameEditor.SCENE_MODE_ORIGINAL:
                self._sceneModeButtons[key].setToolTip('Original')
                row, col = 0, 0
            elif key == self._wgtFrameEditor.SCENE_MODE_GRAYSCALE:
                self._sceneModeButtons[key].setToolTip('Grayscale')
                row, col = 0, 1
            elif key == self._wgtFrameEditor.SCENE_MODE_COLORIZED:
                self._sceneModeButtons[key].setToolTip('Colorized')
                row, col = 0, 2
            self._sceneModeButtons[key].setCheckable(True)
            self._sgmSceneModeSignalMapper.setMapping(
                self._sceneModeButtons[key], key
            )
            self._sceneModeButtons[key].clicked.connect(
                self._sgmSceneModeSignalMapper.map
            )
            dockLayout.addWidget(self._sceneModeButtons[key], row, col)
        
        dockFrame = QFrame()
        dockFrame.setLayout(dockLayout)
        
        self._dwgView.setWidget(dockFrame)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._dwgView)
        self._mnuView.addAction(self._dwgView.toggleViewAction())
    
    def _createPlaybackDock(self):
        self._dwgPlayback = QDockWidget('Playback', self)
        self._dwgPlayback.setAllowedAreas(
            Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea
        )
        
        dockFrame = QFrame()
        #dockFrame.setLayout(dockLayout)
        
        self._dwgPlayback.setWidget(dockFrame)
        self.addDockWidget(Qt.BottomDockWidgetArea, self._dwgPlayback)
        self._mnuView.addAction(self._dwgPlayback.toggleViewAction())
    
    def reset(self):
        self._pickedColor = QColor.fromRgb(128, 128, 128)
        self._updatePickedColorButton()
        self._changeEditMode(self._toolKeyList[0])
        self._changeSceneMode(self._sceneModesList[0])
    
    def about(self):
        QMessageBox.information(self, 'About', '<b>Qt Frontend</b>')
    
    def _updatePickedColorButton(self):
        palette = self._btnCurrentColor.palette()
        palette.setColor(
            self._btnCurrentColor.backgroundRole(),
            self._wgtFrameEditor.currentColor()
        )
        self._btnCurrentColor.setPalette(palette)
    
    def _setPickedColor(self, new_color):
        self._wgtFrameEditor.setCurrentColor(new_color)
        self._updatePickedColorButton()
    
    def _pickPointColor(self):
        self._setPickedColor(
            QColorDialog.getColor(self._wgtFrameEditor.currentColor(), self)
        )
    
    def _newProject(self):
        if self._dlgNewProject.exec() == 0:
            return
        
        self._wgtFrameEditor.openVideoFile(
            self._dlgNewProject.getVideoFilename()
        )
    
    def _frameMouseMove(self, x, y):
        self._lblImagePos.setText('X: %4d Y: %4d' % (x, y))
    
    def _frameMouseLeave(self):
        self._lblImagePos.setText('')
    
    def _changeEditMode(self, edit_mode):
        self._wgtFrameEditor.setEditMode(edit_mode)
        for key in self._toolKeyList:
            self._toolButtons[key].setChecked(key == edit_mode)
    
    def _changeSceneMode(self, scene_mode):
        self._wgtFrameEditor.setSceneMode(scene_mode)
        for key in self._sceneModesList:
            self._sceneModeButtons[key].setChecked(key == scene_mode)
    
    def __init__(self):
        QMainWindow.__init__(self)
        
        self._toolKeyList = (
            FrontQtVideoFrameEditor.EDIT_MODE_HAND,
            FrontQtVideoFrameEditor.EDIT_MODE_EYEDROPPER,
            FrontQtVideoFrameEditor.EDIT_MODE_ADD_POINT,
            FrontQtVideoFrameEditor.EDIT_MODE_EDIT_POINT,
            FrontQtVideoFrameEditor.EDIT_MODE_REMOVE_POINT
        )
        
        self._sceneModesList = (
            FrontQtVideoFrameEditor.SCENE_MODE_ORIGINAL,
            FrontQtVideoFrameEditor.SCENE_MODE_GRAYSCALE,
            FrontQtVideoFrameEditor.SCENE_MODE_COLORIZED
        )
        
        self._createDialogs()
        self._createActions()
        self._createMenu()
        self._createStatusBar()
        self._createBackground()
        self._createPaintDock()
        self._createViewDock()
        self._createPlaybackDock()
        
        self.setWindowTitle('Qt Frontend')
        self.setWindowState(Qt.WindowMaximized)
        self.reset()
