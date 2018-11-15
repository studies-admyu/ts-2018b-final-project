import PyQt5
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QStyle, QDesktopWidget, QMessageBox, QDialog
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush
from PyQt5.QtCore import Qt, QRect, QPoint
import numpy as np
import sys


class RectLabel(QLabel):
    def __init__(self, data_fn, *args, **kwargs):
        super(RectLabel, self).__init__(*args, **kwargs)
        self.data_fn = data_fn
        self.begin = (-1, -1)
        self.end = (-1, -1)

    def paintEvent(self, event):
        super(RectLabel, self).paintEvent(event)

        if self.pixmap() is None or self.data_fn() is None:
            return
        painter = QPainter(self)
        painter.setBrush(QBrush(QColor(255, 255, 255), Qt.NoBrush))

        rect = self.pixmap().rect()
        for rectangle in self.data_fn().get('rects', []):
            painter.drawRect(QRect(self.make_coordinate(rectangle[0], rect), self.make_coordinate(rectangle[1], rect)))
        rectangle = (self.begin, self.end)
        painter.drawRect(QRect(self.make_coordinate(rectangle[0], rect), self.make_coordinate(rectangle[1], rect)))

    def mousePressEvent(self, event):
        super(RectLabel, self).mousePressEvent(event)
        rect = self.pixmap().rect()
        pos = event.pos()
        self.begin = self.make_parameter(pos, rect)
        self.update()

    def mouseMoveEvent(self, event):
        super(RectLabel, self).mouseMoveEvent(event)
        rect = self.pixmap().rect()
        pos = event.pos()
        self.end = self.make_parameter(pos, rect)
        self.update()

    def mouseReleaseEvent(self, event):
        super(RectLabel, self).mouseReleaseEvent(event)
        rect = self.pixmap().rect()
        pos = event.pos()
        self.end = self.make_parameter(pos, rect)

        self.data_fn().setdefault('rects', []).append((self.begin, self.end))
        self.begin = (-1, -1)
        self.end = (-1, -1)

        self.update()

    def make_parameter(self, pos, rect):
        base_point = self.get_pixmap_base_point()
        return ((pos.x() - base_point.x()) / rect.width(), (pos.y() - base_point.y()) / rect.height())

    def make_coordinate(self, point, rect):
        base_point = self.get_pixmap_base_point()
        return QPoint(point[0] * rect.width() + base_point.x(), point[1] * rect.height() + base_point.y())

    def get_pixmap_base_point(self):
        return QStyle.alignedRect(QApplication.layoutDirection(), self.alignment(), self.pixmap().size(), self.rect()).topLeft()


class MakeInitialRects(QDialog, QLabel):
    def __init__(self, image, rects, parent=None):
        super(MakeInitialRects, self).__init__(parent)
        self.image = image
        self.data = {'rects': rects}
        self.mask = np.zeros_like(image)
        self.height = image.shape[0]
        self.width = image.shape[1]
        self.initUI()

    def initUI(self):
        self.setGeometry(QDesktopWidget().availableGeometry())
        self.setWindowTitle('Draw few points')
        show_image = self.get_image_placer(self)
        show_image(self.image)
        self.show()

    def get_image_placer(self, widget):
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QScrollArea, QVBoxLayout

        area = QScrollArea()
        label = RectLabel(lambda: self.data)
        label.setGeometry(widget.geometry())
        label.setAlignment(Qt.AlignCenter)

        area.setWidget(label)
        area.setWidgetResizable(True)

        layout = QVBoxLayout()
        layout.addWidget(area)
        widget.setLayout(layout)

        def show_image(image):
            import qimage2ndarray
            from PyQt5.QtGui import QPixmap
            qimage = qimage2ndarray.array2qimage(image)
            pixmap = QPixmap(qimage)
            label.setPixmap(pixmap)

        return show_image


def make_initial_rects(image):
    rects = []
    app = QApplication(sys.argv)
    window = MakeInitialRects(image, rects)
    app.exec_()
    res_rects = []
    for p1, p2 in rects:
        print(p1, p2)
        res_rects.append(((int(p1[1] * image.shape[0]), int(p1[0] * image.shape[1])), (int(p2[1] * image.shape[0]), int(p2[0] * image.shape[1]))))
    return res_rects
