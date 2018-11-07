# -*- coding: utf-8 -*-

import cv2
import numpy as np

from skimage import color as skcl

from PyQt5.QtCore import pyqtSignal, Qt, QRectF, QPoint
from PyQt5.QtGui import QPalette, QImage, QPixmap, QTransform, QPainterPath, \
    QColor, QPen, QBrush, QMouseEvent
from PyQt5.QtWidgets import QFrame, QGraphicsView, QGraphicsScene, \
    QGraphicsItem, QVBoxLayout, QStyle, QGraphicsPixmapItem, QLabel, \
    QStackedWidget

from .ui_thread_inference import FrontQtInferenceThread

_COLOR_POINT_RADIUS = 3
_COLOR_POINT_DEFAULT_COLOR = QColor.fromRgb(128, 128, 128)

class _FrontQtVideoFramePoint(QGraphicsItem):
    def boundingRect(self):
        return QRectF(
            -_COLOR_POINT_RADIUS, -_COLOR_POINT_RADIUS,
            _COLOR_POINT_RADIUS + 1, _COLOR_POINT_RADIUS + 1
        )
    
    def shape(self):
        shapePath = QPainterPath()
        shapePath.addEllipse(self.boundingRect())
        return shapePath
    
    def paint(self, painter, option, widget):
        brush = painter.brush()
        pen = painter.pen()
        
        new_pen = QPen(Qt.black)
        new_pen.setWidth(1 if option.state & QStyle.State_Selected else 0)
        new_brush = QBrush(self._color)
        
        painter.setPen(new_pen)
        painter.setBrush(new_brush)
        painter.drawEllipse(self.boundingRect())
        
        painter.setBrush(brush)
        painter.setPen(pen)
    
    def color(self):
        return self._color
    
    def setColor(self, new_color):
        self._color = new_color
    
    def __init__(self):
        QGraphicsItem.__init__(self)
        self.setColor(QColor(_COLOR_POINT_DEFAULT_COLOR))
        self.setFlags(
            QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable
        )
        self.setAcceptHoverEvents(True)

class _FrontQtVideoFrameViewport(QGraphicsView):
    mouse_moved = pyqtSignal(QMouseEvent)
    mouse_pressed = pyqtSignal(QMouseEvent)
    mouse_released = pyqtSignal(QMouseEvent)
    
    def __init__(self):
        QGraphicsView.__init__(self)
        self._scale_factor = 1.0
    
    def wheelEvent(self, event):
        QGraphicsView.wheelEvent(self, event)
        if event.modifiers() & Qt.ControlModifier:
            transform = QTransform()
            if event.angleDelta().y() > 0:
                self._scale_factor *= 1.25
            elif event.angleDelta().y() < 0:
                self._scale_factor *= 0.8
            transform.scale(self._scale_factor, self._scale_factor)
            self.setTransform(transform)
    
    def mouseMoveEvent(self, event):
        QGraphicsView.mouseMoveEvent(self, event)
        self.mouse_moved.emit(event)
    
    def mousePressEvent(self, event):
        QGraphicsView.mousePressEvent(self, event)
        self.mouse_pressed.emit(event)
    
    def mouseReleaseEvent(self, event):
        QGraphicsView.mouseReleaseEvent(self, event)
        self.mouse_released.emit(event)
    
class FrontQtVideoFrameEditor(QFrame):
    frame_eyedropper_color = pyqtSignal(QColor)
    frame_mouse_move = pyqtSignal(int, int)
    frame_mouse_leave = pyqtSignal()
    
    EDIT_MODE_HAND = 0
    EDIT_MODE_EYEDROPPER = 1
    EDIT_MODE_ADD_POINT = 2
    EDIT_MODE_EDIT_POINT = 3
    EDIT_MODE_REMOVE_POINT = 4
    
    SCENE_MODE_ORIGINAL = 0
    SCENE_MODE_GRAYSCALE = 1
    SCENE_MODE_COLORIZED = 2
    
    def reset(self):
        empty_pixmap = QPixmap(16, 16)
        empty_pixmap.fill(Qt.black)
        
        self._scene.clear()
        self._bg_item = self._scene.addPixmap(empty_pixmap)
        self._bg_item.setZValue(-1.0)
        
        self._main_widget_stack.setVisible(False)
        self._main_widget_stack.setCurrentIndex(0)
        
        self._vcap = None
        self._frame_image_orig = None
        self._video_filename = ''
        self._mouse_in_frame = False
        
        self.setEditMode(self.EDIT_MODE_HAND)
        self.setSceneMode(self.SCENE_MODE_ORIGINAL)
        self.setCurrentColor(_COLOR_POINT_DEFAULT_COLOR)
    
    def __init__(self):
        QFrame.__init__(self)
        
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QPalette.Dark)
        
        self._scene_widget = _FrontQtVideoFrameViewport()
        self._scene_widget.setAutoFillBackground(True)
        self._scene_widget.setBackgroundRole(QPalette.Window)
        self._scene_widget.setVisible(False)
        self._scene_widget.setMouseTracking(True)
        self._scene_widget.setInteractive(True)
        self._scene_widget.setFrameStyle(QFrame.Sunken | QFrame.StyledPanel)
        
        self._scene_widget.mouse_moved.connect(self._frameViewMouseMoveEvent)
        self._scene_widget.mouse_pressed.connect(
            self._frameViewMousePressEvent
        )
        self._scene_widget.mouse_released.connect(
            self._frameViewMouseReleaseEvent
        )
        
        self._scene = QGraphicsScene()
        self._scene_widget.setScene(self._scene)
        
        self._calculation_widget = QLabel()
        self._calculation_widget.setAutoFillBackground(True)
        self._calculation_widget.setBackgroundRole(QPalette.Window)
        self._calculation_widget.setText('Calculating...')
        self._calculation_widget.setAlignment(Qt.AlignCenter)
        self._calculation_widget.setFrameStyle(
            QFrame.Sunken | QFrame.StyledPanel
        )
        
        self._main_widget_stack = QStackedWidget()
        self._main_widget_stack.insertWidget(0, self._scene_widget)
        self._main_widget_stack.insertWidget(1, self._calculation_widget)
        
        top_layout = QVBoxLayout()
        top_layout.addWidget(self._main_widget_stack)
        top_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(top_layout)
        
        self._model_thread = FrontQtInferenceThread()
        self._model_thread.finished.connect(self._modelInferenceCompleted)
        
        self.setModel(None, None)
        
        self.reset()
    
    def openVideoFile(self, filename):
        self.reset()
        
        self._vcap = cv2.VideoCapture(filename)
        _, first_frame = self._vcap.read()
        first_frame_gray3 = cv2.cvtColor(
            cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2RGB
        )
        
        self._frame_image_orig = QImage(
            first_frame.data,
            first_frame.shape[1], first_frame.shape[0],
            QImage.Format_RGB888
        ).rgbSwapped()
        self._frame_image_gray3 = QImage(
            first_frame_gray3.data,
            first_frame_gray3.shape[1], first_frame_gray3.shape[0],
            QImage.Format_RGB888
        )
        self._frame_image_model_output = QImage(
            first_frame_gray3.copy().data,
            first_frame_gray3.shape[1], first_frame_gray3.shape[0],
            QImage.Format_RGB888
        )

        self.setSceneMode(self.sceneMode())
        self._main_widget_stack.setVisible(True)
        
    def _frameViewMouseMoveEvent(self, event):
        scene_point = self._scene_widget.mapToScene(
            QPoint(event.x(), event.y())
        ).toPoint()
        if not self._frame_image_orig.rect().contains(scene_point):
            if self._mouse_in_frame:
                self.frame_mouse_leave.emit()
                self._mouse_in_frame = False
            return
            
        self._mouse_in_frame = True
        self.frame_mouse_move.emit(scene_point.x(), scene_point.y())
        if (
            (self._editMode == self.EDIT_MODE_EYEDROPPER) and
            (event.buttons() & Qt.LeftButton)
        ):
            self.frame_eyedropper_color.emit(
                QColor.fromRgb(self._frame_image_orig.pixel(
                    scene_point.x(), scene_point.y()
                ))
            )
    
    def _frameViewMousePressEvent(self, event):
        scene_point = self._scene_widget.mapToScene(
            QPoint(event.x(), event.y())
        ).toPoint()
        if not self._frame_image_orig.rect().contains(scene_point):
            if self._mouse_in_frame:
                self.frame_mouse_leave.emit()
                self._mouse_in_frame = False
            return
            
        self._mouse_in_frame = True
        if self._editMode == self.EDIT_MODE_EYEDROPPER:
            self.frame_eyedropper_color.emit(
                QColor.fromRgb(self._frame_image_orig.pixel(
                    scene_point.x(), scene_point.y()
                ))
            )
    
    def _frameViewMouseReleaseEvent(self, event):
        scene_point = self._scene_widget.mapToScene(
            QPoint(event.x(), event.y())
        ).toPoint()
        if not self._frame_image_orig.rect().contains(scene_point):
            if self._mouse_in_frame:
                self.frame_mouse_leave.emit()
                self._mouse_in_frame = False
            return
        
        self._mouse_in_frame = True
        if self._editMode == self.EDIT_MODE_EYEDROPPER:
            self.frame_eyedropper_color.emit(
                QColor.fromRgb(self._frame_image_orig.pixel(
                    scene_point.x(), scene_point.y()
                ))
            )
        if self._editMode == self.EDIT_MODE_ADD_POINT:
            item = self._scene.itemAt(
                scene_point.x(), scene_point.y(),
                self._scene_widget.transform()
            )
            if isinstance(item, QGraphicsPixmapItem):
                new_point = _FrontQtVideoFramePoint()
                new_point.setPos(scene_point.x(), scene_point.y())
                new_point.setZValue(1.0)
                new_point.setColor(self._current_color)
                self._scene.addItem(new_point)
        elif self._editMode == self.EDIT_MODE_REMOVE_POINT:
            item = self._scene.itemAt(
                scene_point.x(), scene_point.y(),
                self._scene_widget.transform()
            )
            if isinstance(item, _FrontQtVideoFramePoint):
                item.setZValue(-2)
                item.setVisible(False)             
    
    def setEditMode(self, mode):
        self._editMode = mode
        
        if self._editMode == self.EDIT_MODE_HAND:
            self._scene_widget.setDragMode(QGraphicsView.ScrollHandDrag)
            self._scene_widget.setCursor(Qt.ArrowCursor)
        elif self._editMode == self.EDIT_MODE_EDIT_POINT:
            self._scene_widget.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self._scene_widget.setDragMode(QGraphicsView.NoDrag)
            self._scene_widget.setCursor(Qt.CrossCursor)
    
    def editMode(self):
        return self._editMode
    
    def setSceneMode(self, mode):
        self._sceneMode = mode
        if self._frame_image_orig is None:
            return
        
        if self._sceneMode == self.SCENE_MODE_ORIGINAL:
            self._bg_item.setPixmap(QPixmap.fromImage(self._frame_image_orig))
        elif self._sceneMode == self.SCENE_MODE_GRAYSCALE:
            self._bg_item.setPixmap(QPixmap.fromImage(self._frame_image_gray3))
        elif self._sceneMode == self.SCENE_MODE_COLORIZED:
            self._bg_item.setPixmap(
                QPixmap.fromImage(self._frame_image_model_output)
            )
        self._scene.update()
    
    def sceneMode(self):
        return self._sceneMode
    
    def setCurrentColor(self, new_color):
        self._current_color = new_color
        
        selected_points = self._scene.selectedItems()
        for point in selected_points:
            point.setColor(new_color)
        
        self._scene.update()
    
    def currentColor(self):
        return self._current_color
    
    def setModel(self, model, context):
        self._model = model
        self._model_context = context
        self._model_thread.setModel(self._model)
    
    def model(self):
        return self._model
    
    def modelContext(self):
        return self._model_context
    
    def _preprocess_model_input(self):
        w = int(max((
            self._frame_image_orig.width(), self._frame_image_orig.height()
        )) / self._model_context['load_size'])
        
        ptr = self._frame_image_gray3.constBits()
        ptr.setsize(self._frame_image_gray3.byteCount())
        
        frame_gray_cv2 = np.array(ptr, dtype = np.uint8).reshape((
            self._frame_image_gray3.height(), self._frame_image_gray3.width(),
            3
        ))
        
        incoming_frame_gray_cv2 = cv2.resize(
            frame_gray_cv2, (
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
        
        for item in self._scene.items():
            if not isinstance(item, _FrontQtVideoFramePoint):
                continue
            if not item.isVisible():
                continue
            
            point = (
                np.array([item.x(), item.y()]) *
                self._model_context['load_size'] /
                np.array(frame_gray_cv2.shape[1::-1])
            ).astype(np.uint)
            
            tl = tuple((point - w).tolist())
            br = tuple((point + w).tolist())
            
            cv2.rectangle(mask, tl, br, 255, -1)
            cv2.rectangle(
                im, tl, br,
                [
                    item.color().red(), item.color().green(),
                    item.color().blue()
                ],
                -1
            )
            
        im_mask0 = (mask > 0.0).transpose((2, 0, 1))
        im_ab0 = skcl.rgb2lab(im).transpose((2, 0, 1))[1:3, :, :]
        
        self._model.set_image(incoming_frame_gray_cv2)
        self._model_thread.setForwardArgsList([im_ab0, im_mask0])
    
    def _postprocess_model_output(self):
        incoming_frame = self._frame_image_orig.rgbSwapped()
        
        ptr = incoming_frame.constBits()
        ptr.setsize(incoming_frame.byteCount())
        
        incoming_frame_cv2 = np.array(ptr, dtype = np.uint8).reshape(
            (incoming_frame.height(), incoming_frame.width(), 3)
        )
        
        incoming_frame_l = skcl.rgb2lab(incoming_frame_cv2)[:, :, 0]
        
        out_ab = self._model.output_ab.transpose((1, 2, 0))
        out_ab = cv2.resize(
            out_ab, incoming_frame_l.shape[::-1],
            interpolation = cv2.INTER_CUBIC
        )
        out_lab = np.concatenate(
            (incoming_frame_l[..., np.newaxis], out_ab), axis = 2
        )
        out_img = (np.clip(skcl.lab2rgb(out_lab), 0, 1) * 255).astype(np.uint8)
        
        self._frame_image_model_output = QImage(
            out_img.data,
            out_img.shape[1], out_img.shape[0],
            QImage.Format_RGB888
        )
        
        # Update pixmap
        self.setSceneMode(self.sceneMode())
    
    def modelInference(self):
        if self._model is None:
            return
        self._main_widget_stack.setCurrentIndex(1)
        self._preprocess_model_input()
        self._model_thread.start()
    
    def _modelInferenceCompleted(self):
        if self._model is None:
            return
        self._postprocess_model_output()
        self._main_widget_stack.setCurrentIndex(0)
