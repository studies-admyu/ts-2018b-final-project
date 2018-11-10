# -*- coding: utf-8 -*-

import math

import cv2
import numpy as np

from skimage import color as skcl

from PyQt5.QtCore import pyqtSignal, Qt, QRectF, QPoint, QPointF
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
    
    def _updateFrame(self, frame, frame_index):
        if frame_index not in self._frames_cache:
            self._frames_cache[frame_index] = None
        # Cache frame
        self._frames_cache[frame_index] = frame
        self._updateCachedFrame(frame_index)
    
    def _updateCachedFrame(self, frame_index):
        frame = self._frames_cache[frame_index]
        # Set current frame
        self._current_frame = frame_index
        
        frame_gray3 = cv2.cvtColor(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2RGB
        )
        self._frame_image_orig = QImage(
            frame.data,
            frame.shape[1], frame.shape[0],
            QImage.Format_RGB888
        ).rgbSwapped()
        self._frame_image_gray3 = QImage(
            frame_gray3.data,
            frame_gray3.shape[1], frame_gray3.shape[0],
            QImage.Format_RGB888
        )
        self._frame_image_model_output = QImage(
            frame_gray3.copy().data,
            frame_gray3.shape[1], frame_gray3.shape[0],
            QImage.Format_RGB888
        )

        self.setSceneMode(self.sceneMode())
    
    def _setCurrentPoints(self, points):
        items_list = []
        for item in self._scene.items():
            if not isinstance(item, _FrontQtVideoFramePoint):
                continue
            items_list.append(item)
        
        max_length = max((len(points), len(items_list)))
        
        for i in range(max_length):
            if i >= len(items_list):
                new_item = _FrontQtVideoFramePoint()
                self._scene.addItem(new_item)
                items_list.append(new_item)
            
            if i < len(points):
                item_pos = QPointF(
                    math.floor(points[i]['x']), math.floor(points[i]['y'])
                ) + QPointF(0.5, 0.5)
                item_color = QColor.fromRgb(
                    points[i]['color'][0], points[i]['color'][1],
                    points[i]['color'][2]
                )
                items_list[i].setPos(item_pos)
                items_list[i].setColor(item_color)
                items_list[i].setZValue(1.0)
                items_list[i].setVisible(True)
            else:
                items_list[i].setPos(0.0, 0.0)
                items_list[i].setZValue(-2.0)
                items_list[i].setVisible(False)
    
    def _getCurrentPoints(self):
        points_list = []
        for item in self._scene.items():
            if not isinstance(item, _FrontQtVideoFramePoint):
                continue
            if not item.isVisible():
                continue
            
            point = {
                'x': math.floor(item.x()),
                'y': math.floor(item.y()),
                'color': [
                    item.color().red(),
                    item.color().green(),
                    item.color().blue()
                ]
            }
            
            points_list.append(point)
        
        return points_list
    
    def _updateCachedPoints(self, frame_index):
        self._setCurrentPoints(self._points_cache[frame_index])
    
    def _updatePoints(self, cached_points, frame_index):
        self._points_cache[frame_index] = cached_points[:]
        self._updateCachedPoints(frame_index)
    
    def openVideoFile(self, filename):
        self.reset()
        
        self._vcap = cv2.VideoCapture(filename)
        self._frames_cache = {}
        self._points_cache = {}
        _, first_frame = self._vcap.read()
        
        self._updateFrame(first_frame.copy(), 1)
        self._main_widget_stack.setVisible(True)
    
    def _mapCursorToSceneCoordinates(self, point):
        return self._scene_widget.mapToScene(point)
    
    def _mapSceneCoordinatesToFramePixel(self, pointf):
        scene_pixel = QPoint(
            math.floor(pointf.x()),
            math.floor(pointf.y())
        )
        
        return (
            scene_pixel if self._bg_item.boundingRect().contains(pointf)
            else None
        )
    
    def _mapCursorToFramePixel(self, point):
        scene_coords = self._mapCursorToSceneCoordinates(point)
        return self._mapSceneCoordinatesToFramePixel(scene_coords)
    
    def _frameViewMouseMoveEvent(self, event):
        was_mouse_in_frame = self._mouse_in_frame
        frame_pixel = self._mapCursorToFramePixel(QPoint(event.x(), event.y()))
        self._mouse_in_frame = (frame_pixel is not None)
        
        if not self._mouse_in_frame:
            if was_mouse_in_frame:
                self.frame_mouse_leave.emit()
            return
        
        self.frame_mouse_move.emit(frame_pixel.x(), frame_pixel.y())
        if (
            (self._editMode == self.EDIT_MODE_EYEDROPPER) and
            (event.buttons() & Qt.LeftButton)
        ):
            self.frame_eyedropper_color.emit(
                QColor.fromRgb(self._frame_image_orig.pixel(
                    frame_pixel.x(), frame_pixel.y()
                ))
            )
    
    def _frameViewMousePressEvent(self, event):
        was_mouse_in_frame = self._mouse_in_frame
        frame_pixel = self._mapCursorToFramePixel(QPoint(event.x(), event.y()))
        self._mouse_in_frame = (frame_pixel is not None)
        
        if not self._mouse_in_frame:
            if was_mouse_in_frame:
                self.frame_mouse_leave.emit()
            return
        
        if self._editMode == self.EDIT_MODE_EYEDROPPER:
            self.frame_eyedropper_color.emit(
                QColor.fromRgb(self._frame_image_orig.pixel(
                    frame_pixel.x(), frame_pixel.y()
                ))
            )
    
    def _frameViewMouseReleaseEvent(self, event):
        was_mouse_in_frame = self._mouse_in_frame
        scene_coodinates = self._mapCursorToSceneCoordinates(
            QPoint(event.x(), event.y())
        )
        frame_pixel = self._mapSceneCoordinatesToFramePixel(scene_coodinates)
        self._mouse_in_frame = (frame_pixel is not None)
        
        if not self._mouse_in_frame:
            if was_mouse_in_frame:
                self.frame_mouse_leave.emit()
            return
        
        if self._editMode == self.EDIT_MODE_EYEDROPPER:
            self.frame_eyedropper_color.emit(
                QColor.fromRgb(self._frame_image_orig.pixel(
                    frame_pixel.x(), frame_pixel.y()
                ))
            )
        if self._editMode == self.EDIT_MODE_ADD_POINT:
            item = self._scene.itemAt(
                scene_coodinates, self._scene_widget.transform()
            )
            if isinstance(item, QGraphicsPixmapItem):
                # Try to use some removed point
                new_point = None
                for item in self._scene.items():
                    if not isinstance(item, _FrontQtVideoFramePoint):
                        continue
                    if item.isVisible():
                        continue
                    new_point = item
                    break
                
                if new_point is None:
                    new_point = _FrontQtVideoFramePoint()
                    new_point.setPos(0, 0)
                    new_point.setZValue(-2.0)
                    new_point.setVisible(False)
                    self._scene.addItem(new_point)
                
                # Position at the center of frame pixel
                new_point_pos = (
                    QPointF(frame_pixel) + QPointF(0.5, 0.5)
                )
                new_point.setPos(new_point_pos)
                
                new_point.setColor(self._current_color)
                new_point.setZValue(1.0)
                new_point.setVisible(True)
                
        elif self._editMode == self.EDIT_MODE_REMOVE_POINT:
            item = self._scene.itemAt(
                scene_coodinates, self._scene_widget.transform()
            )
            if isinstance(item, _FrontQtVideoFramePoint):
                item.setZValue(-2.0)
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
    
    def previousFrame(self):
        if self._vcap is None:
            return
        if self._current_frame <= 1:
            return
        
        # Save current points
        self._updatePoints(self._getCurrentPoints(), self._current_frame)
        
        # Load previous frame and its points
        new_frame_index = self._current_frame - 1
        self._updateCachedFrame(new_frame_index)
        self._updateCachedPoints(new_frame_index)
    
    def nextFrame(self):
        if self._vcap is None:
            return
        
        # Save current points
        self._updatePoints(self._getCurrentPoints(), self._current_frame)
        
        # Try to load next frame and its points
        new_frame_index = self._current_frame + 1
        try:
            self._updateCachedFrame(new_frame_index)
            self._updateCachedPoints(new_frame_index)
        except KeyError:
            _, frame = self._vcap.read()
            if frame is None:
                return
            self._updateFrame(frame.copy(), new_frame_index)
            self._updatePoints([], new_frame_index)
    
    def extrapolateNext(self):
        if self._vcap is None:
            return
        
        # Save current points
        cpoints = self._getCurrentPoints()
        self._updatePoints(cpoints, self._current_frame)
        
        # Try to load next frame and its points
        new_frame_index = self._current_frame + 1
        try:
            self._updateCachedFrame(new_frame_index)
        except KeyError:
            _, frame = self._vcap.read()
            if frame is None:
                return
            self._updateFrame(frame.copy(), new_frame_index)
        
        # Don't extrapolate if there are no points
        if len(cpoints) == 0:
            self.modelInference()
            return
        
        lk_params = dict(
            winSize = (15, 15), maxLevel = 2,
            criteria = (
                cv2.TermCriteria_EPS | cv2.TermCriteria_COUNT, 10, 0.03
            )
        )
        
        old_points = np.array([[[p['x'], p['y']]] for p in cpoints]).astype(
            np.float32
        )
        old_gray = cv2.cvtColor(
            self._frames_cache[new_frame_index - 1], cv2.COLOR_BGR2GRAY
        )
        new_gray = cv2.cvtColor(
            self._frames_cache[new_frame_index], cv2.COLOR_BGR2GRAY
        )
        
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
                'color': cpoints[i]['color']
            } for i in range(len(cpoints)) if valid_points[i]
        ]
        
        self._setCurrentPoints(new_points)
        self.modelInference()
    
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
        
        color_points = self._getCurrentPoints()
        for color_point in color_points:
            point = (
                np.array([color_point['x'], color_point['y']]) *
                self._model_context['load_size'] /
                np.array(frame_gray_cv2.shape[1::-1])
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
