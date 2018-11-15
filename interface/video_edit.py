from PyQt5.QtWidgets import QLabel, QLayout, QWidget, QMainWindow, QApplication, QStyle
from PyQt5.QtCore import Qt, QRect, QPoint, QLine, QSize
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor


class VideoEdit(QLabel):
    def __init__(self, rect_fn, image_fn, *args, **kwargs):
        super(VideoEdit, self).__init__(*args, **kwargs)
        self.rect_fn = rect_fn
        self.image_fn = image_fn

    def mousePressEvent(self, event):
        frame_rects = self.rect_fn()
        frame = self.image_fn()
        self.update()

    def mouseReleaseEvent(self, event):
        frame_rects = self.rect_fn()
        frame = self.image_fn()
        self.update()

    def mouseMoveEvent(self, event):
        frame_rects = self.rect_fn()
        frame = self.image_fn()
        self.update()

    def make_parameter(self, pos, rect):
        base_point = self.get_pixmap_base_point()
        return ((pos.x() - base_point.x()) / rect.width(), (pos.y() - base_point.y()) / rect.height())

    def make_coordinate(self, point, rect):
        from PyQt5.QtCore import QPoint
        base_point = self.get_pixmap_base_point()
        return QPoint(point[0] * rect.width() + base_point.x(), point[1] * rect.height() + base_point.y())

    def get_pixmap_base_point(self):
        from PyQt5.QtWidgets import QApplication, QStyle
        return QStyle.alignedRect(QApplication.layoutDirection(), self.alignment(), self.pixmap().size(), self.rect()).topLeft()
