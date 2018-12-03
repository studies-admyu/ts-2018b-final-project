# -*- coding: utf-8 -*-

from PyQt5.QtCore import Qt, QSignalMapper
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtWidgets import QMainWindow, QAction, QMenu, QMessageBox, qApp, \
    QLabel, QDockWidget, QToolButton, QPushButton, QGridLayout, QFrame, \
    QColorDialog, QFileDialog

from .ui_dialog_new_project import FrontQtDialogNewProject
from .ui_widget_video_frame_editor import FrontQtVideoFrameEditor

class FrontQtWindowMain(QMainWindow):
    
    def _createDialogs(self):
        self._dlgNewProject = FrontQtDialogNewProject(self)
    
    def _createActions(self):
        self._actNew = QAction('&New project...')
        self._actNew.setShortcut('Ctrl+N')
        self._actNew.triggered.connect(self._newProject)
        
        self._actOpen = QAction('&Open project...')
        self._actOpen.setShortcut('Ctrl+O')
        self._actOpen.triggered.connect(self._openProject)
        
        self._actSaveAs = QAction('Save project &as...')
        self._actSaveAs.setShortcut('Ctrl+S')
        self._actSaveAs.triggered.connect(self._saveProjectAs)
        
        self._actQuit = QAction('&Quit')
        self._actQuit.triggered.connect(self.close)
        
        self._actExportVideo = QAction('E&xport video...')
        self._actExportVideo.setShortcut('Ctrl+X')
        self._actExportVideo.triggered.connect(self._exportInferencedVideo)
        
        self._actExportFramePoints = QAction('Export &frame points...')
        self._actExportFramePoints.setShortcut('Ctrl+F')
        self._actExportFramePoints.triggered.connect(self._exportColorPoints)
        
        self._actImportFramePoints = QAction('I&mport frame points...')
        self._actImportFramePoints.setShortcut('Ctrl+M')
        self._actImportFramePoints.triggered.connect(self._importColorPoints)
        
        self._actDeleteSelected = QAction('&Delete')
        self._actDeleteSelected.setShortcut('Del')
        self._actDeleteSelected.triggered.connect(
            self._wgtFrameEditor.deleteSelectedPoints
        )
        
        self._actCopySelected = QAction('&Copy')
        self._actCopySelected.setShortcut('Ctrl+C')
        self._actCopySelected.triggered.connect(
            self._wgtFrameEditor.copySelectedPoints
        )
        
        self._actPaste = QAction('&Paste')
        self._actPaste.setShortcut('Ctrl+V')
        self._actPaste.triggered.connect(
            self._wgtFrameEditor.pastePoints
        )
        
        self._actAbout = QAction('&About...')
        self._actAbout.triggered.connect(self.about)
        
        self._actAboutQt = QAction('About Qt...')
        self._actAboutQt.triggered.connect(qApp.aboutQt)
    
    def _createMenu(self):
        self._mnuFile = QMenu('&File')
        self._mnuFile.addAction(self._actNew)
        self._mnuFile.addAction(self._actOpen)
        self._mnuFile.addAction(self._actSaveAs)
        self._mnuFile.addSeparator()
        self._mnuFile.addAction(self._actExportVideo)
        self._mnuFile.addAction(self._actExportFramePoints)
        self._mnuFile.addAction(self._actImportFramePoints)
        self._mnuFile.addSeparator()
        self._mnuFile.addAction(self._actQuit)
        
        self._mnuEdit = QMenu('&Edit')
        self._mnuEdit.addAction(self._actDeleteSelected)
        self._mnuEdit.addAction(self._actCopySelected)
        self._mnuEdit.addAction(self._actPaste)
        
        self._mnuView = QMenu('&View')
        
        self._mnuHelp = QMenu('&Help')
        self._mnuHelp.addAction(self._actAbout)
        self._mnuHelp.addAction(self._actAboutQt)
        
        self.menuBar().addMenu(self._mnuFile)
        self.menuBar().addMenu(self._mnuEdit)
        self.menuBar().addMenu(self._mnuView)
        self.menuBar().addMenu(self._mnuHelp)
    
    def _createBackground(self):
        self._wgtFrameEditor = FrontQtVideoFrameEditor()
        self._wgtFrameEditor.frame_mouse_move.connect(self._frameMouseMove)
        self._wgtFrameEditor.frame_mouse_leave.connect(self._frameMouseLeave)
        self._wgtFrameEditor.frame_eyedropper_color.connect(
            self._setPickedColor
        )
        self._wgtFrameEditor.frame_changed.connect(
            self._videoFrameChanged
        )
        self._wgtFrameEditor.points_selection_changed.connect(
            self._updateUI
        )
        self._wgtFrameEditor.state_changed.connect(self._updateUI)
        
        self.setCentralWidget(self._wgtFrameEditor)
    
    def _createStatusBar(self):
        self._lblImagePos = QLabel()
        self._lblImagePos.setText('X: 9999 Y: 9999')
        self._lblImagePos.adjustSize()
        self._lblImagePos.setFixedWidth(self._lblImagePos.width())
        self._lblImagePos.setText('')
        
        self._lblVideoPos = QLabel()
        self._lblVideoPos.setText('Frame: 0/0')
        
        self.statusBar().addPermanentWidget(self._lblImagePos)
        self.statusBar().addPermanentWidget(self._lblVideoPos)
    
    def _createPaintDock(self):
        self._dwgPaint = QDockWidget('Painting', self)
        self._dwgPaint.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        
        dockLayout = QGridLayout()
        
        self._btnCurrentColor = QPushButton()
        self._btnCurrentColor.setToolTip('Select current color')
        self._btnCurrentColor.setAutoFillBackground(True)
        self._btnCurrentColor.clicked.connect(self._pickPointColor)
        dockLayout.addWidget(self._btnCurrentColor, 0, 0, 1, 3)
        
        self._sgmToolSignalMapper = QSignalMapper(self)
        self._sgmToolSignalMapper.mapped.connect(self._changeEditMode)
        self._toolButtons = { k: QToolButton() for k in self._toolKeyList }
        for i, key in enumerate(self._toolKeyList):
            if key ==  self._wgtFrameEditor.EDIT_MODE_HAND:
                self._toolButtons[key].setToolTip('Hand')
                self._toolButtons[key].setIcon(
                    QIcon('images/icons/16x16_color/hand.png')
                )
                row, col = 1, 0
            elif key == self._wgtFrameEditor.EDIT_MODE_EYEDROPPER:
                self._toolButtons[key].setToolTip('Color picker')
                self._toolButtons[key].setIcon(
                    QIcon('images/icons/16x16_color/color_picker.png')
                )
                row, col = 1, 2
            elif key == self._wgtFrameEditor.EDIT_MODE_ADD_POINT:
                self._toolButtons[key].setToolTip('Add color point')
                self._toolButtons[key].setIcon(
                    QIcon('images/icons/16x16_color/pencil_add.png')
                )
                row, col = 2, 0
            elif key == self._wgtFrameEditor.EDIT_MODE_EDIT_POINT:
                self._toolButtons[key].setToolTip('Edit color point')
                self._toolButtons[key].setIcon(
                    QIcon('images/icons/16x16_color/pencil_go.png')
                )
                row, col = 2, 1
            elif key == self._wgtFrameEditor.EDIT_MODE_REMOVE_POINT:
                self._toolButtons[key].setToolTip('Delete color point')
                self._toolButtons[key].setIcon(
                    QIcon('images/icons/16x16_color/pencil_delete.png')
                )
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
                self._sceneModeButtons[key].setIcon(
                    QIcon('images/icons/16x16_color/color_wheel.png')
                )
                row, col = 0, 0
            elif key == self._wgtFrameEditor.SCENE_MODE_GRAYSCALE:
                self._sceneModeButtons[key].setToolTip('Grayscale')
                self._sceneModeButtons[key].setIcon(
                    QIcon('images/icons/16x16_gray/color_wheel.png')
                )
                row, col = 0, 1
            elif key == self._wgtFrameEditor.SCENE_MODE_COLORIZED:
                self._sceneModeButtons[key].setToolTip('Colorized')
                self._sceneModeButtons[key].setIcon(
                    QIcon('images/icons/16x16_color/two_pictures.png')
                )
                row, col = 0, 2
            self._sceneModeButtons[key].setCheckable(True)
            self._sgmSceneModeSignalMapper.setMapping(
                self._sceneModeButtons[key], key
            )
            self._sceneModeButtons[key].clicked.connect(
                self._sgmSceneModeSignalMapper.map
            )
            dockLayout.addWidget(self._sceneModeButtons[key], row, col)
        
        self._tbtnInferenceModel = QToolButton()
        self._tbtnInferenceModel.setToolTip('Calculate colorization')
        self._tbtnInferenceModel.setIcon(
            QIcon('images/icons/16x16_color/magic_wand_2.png')
        )
        self._tbtnInferenceModel.clicked.connect(
            self._wgtFrameEditor.modelInference
        )
        dockLayout.addWidget(self._tbtnInferenceModel, 1, 1)
        
        dockFrame = QFrame()
        dockFrame.setLayout(dockLayout)
        
        self._dwgView.setWidget(dockFrame)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._dwgView)
        self._mnuView.addAction(self._dwgView.toggleViewAction())
    
    def _initModel(self, model, model_context):
        self._wgtFrameEditor.setModel(model, model_context)
    
    def reset(self):
        self._pickedColor = QColor.fromRgb(128, 128, 128)
        self._updatePickedColorButton()
        self._changeEditMode(self._toolKeyList[0])
        self._changeSceneMode(self._sceneModesList[0])
        
        self._updateUI()
    
    def about(self):
        QMessageBox.information(self, 'About', '<b>Qt Frontend</b>')
    
    def _updateUI(self):
        project_opened = (len(self._wgtFrameEditor.currentFilename()) > 0)
        points_selected = (len(self._wgtFrameEditor.selectedPoints()) > 0)
        edit_state = (
            self._wgtFrameEditor.state() ==
            self._wgtFrameEditor.STATE_FRAME_EDIT
        )
        
        self._actNew.setEnabled(edit_state)
        self._actOpen.setEnabled(edit_state)
        self._actQuit.setEnabled(edit_state)
        
        self._actSaveAs.setEnabled(project_opened and edit_state)
        self._actExportVideo.setEnabled(project_opened and edit_state)
        self._actExportFramePoints.setEnabled(project_opened and edit_state)
        self._actImportFramePoints.setEnabled(project_opened and edit_state)
        
        self._actCopySelected.setEnabled(
            project_opened and points_selected and edit_state)
        self._actDeleteSelected.setEnabled(
            project_opened and points_selected and edit_state
        )
        self._actPaste.setEnabled(project_opened and edit_state)
        
        self._tbtnInferenceModel.setEnabled(project_opened and edit_state)
    
    def _updatePickedColorButton(self):
        max_dimension = max((
            self._btnCurrentColor.width(), self._btnCurrentColor.height()
        ))
        back_pixmap = QPixmap(max_dimension, max_dimension)
        back_pixmap.fill(self._wgtFrameEditor.currentColor())
        self._btnCurrentColor.setIcon(QIcon(back_pixmap))
    
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
        
        if not self._wgtFrameEditor.openVideoFile(
            self._dlgNewProject.getVideoFilename()
        ):
            QMessageBox.critical(
                self, 'New project', 'Unable to open video <b>%s</b>.' %
                (self._dlgNewProject.getVideoFilename())
            )
        
        self.reset()
    
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
    
    def _videoFrameChanged(self):
        self._lblVideoPos.setText(
            'Frame: %u/%u' % (
                self._wgtFrameEditor.currentFrame(),
                self._wgtFrameEditor.framesCount()
            )
        )
        self._lblVideoPos.adjustSize()
    
    def _openProject(self):
        project_filename = QFileDialog.getOpenFileName(
            self, 'Open project file'
        )
        if len(project_filename[0]) == 0:
            return
        
        try:
            self._wgtFrameEditor.openProject(project_filename[0])
        except Exception:
            self._wgtFrameEditor.reset()
            QMessageBox.critical(
                self, 'Open project error', 'Unable to open project file ' +
                ('<i>%s</i>' % (project_filename[0])) +
                ' due to wrong file format or access restrictions.'
            )
        self.reset()
    
    def _saveProjectAs(self):
        if len(self._wgtFrameEditor.currentFilename()) == 0:
            return
        project_filename = QFileDialog.getSaveFileName(
            self, 'Save project file'
        )
        if len(project_filename[0]) == 0:
            return
        try:
            self._wgtFrameEditor.saveProject(project_filename[0])
        except Exception:
            QMessageBox.critical(
                self, 'Save project error', 'Unable to save current project ' +
                'to file ' +
                ('<i>%s</i>' % (project_filename[0])) +
                ' due to access restrictions.'
            )
        self._updateUI()
    
    def _exportInferencedVideo(self):
        if len(self._wgtFrameEditor.currentFilename()) == 0:
            return
        
        output_formats = [
            self._wgtFrameEditor.VIDEO_FORMAT_PNG_SEQUENCE,
            self._wgtFrameEditor.VIDEO_FORMAT_X264
        ]
        extension_dict = {
            'Sequenced png files (*.png)': output_formats[0],
            'MPEG4 video files (*.mp4)': output_formats[1]
        }
        
        output_video_filename = QFileDialog.getSaveFileName(
            self, 'Export video',
            filter = ';;'.join(extension_dict.keys())
        )
        if len(output_video_filename[0]) == 0:
            return
        if not self._wgtFrameEditor.exportInferencedVideo(
            output_video_filename[0], extension_dict[output_video_filename[1]]
        ):
            QMessageBox.critical(
                self, 'Export video',
                ('Unable to export video to file ' +
                '<i>%s</i>. Please check your installed codecs, ' +
                'access restrictions or free storage amount.') % (
                    output_video_filename[0]
                )
            )
    
    def _exportColorPoints(self):
        if len(self._wgtFrameEditor.currentFilename()) == 0:
            return
        export_filename = QFileDialog.getSaveFileName(
            self, 'Export color points file'
        )
        if len(export_filename[0]) == 0:
            return
        try:
            self._wgtFrameEditor.exportColorPoints(export_filename[0])
        except Exception:
            QMessageBox.critical(
                self, 'Export color points error',
                'Unable to export color points to file ' +
                ('<i>%s</i>' % (export_filename[0])) +
                ' due to access restrictions.'
            )
    
    def _importColorPoints(self):
        if len(self._wgtFrameEditor.currentFilename()) == 0:
            return
        import_filename = QFileDialog.getOpenFileName(
            self, 'Import color points file'
        )
        if len(import_filename[0]) == 0:
            return
        try:
            self._wgtFrameEditor.importColorPoints(import_filename[0])
        except Exception:
            QMessageBox.critical(
                self, 'Import color points error',
                'Unable to import color points from file ' +
                ('<i>%s</i>' % (import_filename[0])) +
                ' due to wrong file format or access restrictions.'
            )
        self._updateUI()
    
    def __init__(self, model = None, model_context = None):
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
        
        self._createBackground()
        self._createDialogs()
        self._createActions()
        self._createMenu()
        self._createStatusBar()
        self._createPaintDock()
        self._createViewDock()
        self._initModel(model, model_context)
        
        self.setWindowTitle('Qt Frontend')
        self.setWindowIcon(
            QIcon('images/icons/32x32_color/convert_gray_to_color.png')
        )
        self.reset()
