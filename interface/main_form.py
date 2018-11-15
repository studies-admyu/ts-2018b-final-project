import PyQt5
from PyQt5.QtWidgets import QWidget, QScrollArea
from PyQt5.QtCore import Qt
from split_frames import read_video, write_video
from interface.video_edit import VideoEdit
import numpy as np
from make_initial_rects import make_initial_rects, MakeInitialRects
import cv2


class MainWidget(QWidget):
    def __init__(self, full_color, color, tracker):
        super(MainWidget, self).__init__()
        self.title = 'ONELN::guided video colorization'
        self.full_color = full_color
        self.color = color
        self.tracker = tracker
        self.cur_frame = -1
        self.rects = []
        self.ratio = 1.
        self.video = None
        self.initUI()

    def initUI(self):
        from PyQt5.QtWidgets import QDesktopWidget, QVBoxLayout, QFormLayout, QLayout, QGridLayout, QBoxLayout
        import qdarkstyle

        self.setWindowTitle(self.title)
        self.setGeometry(QDesktopWidget().availableGeometry())
        self.zoom_on = self.createZoomOn()
        self.zoom_out = self.createZoomOut()
        self.next_button = self.createNextButton()
        self.prev_button = self.createPrevButton()
        self.palitra = self.createPalitra()
        self.video_edit = self.createVideoEdit()
        self.menu_bar = self.createMenuBar()

        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        self.show()

    def createVideoEdit(self):
        video_edit = VideoEdit(lambda: [] if self.video is None else self.video[self.cur_frame], lambda: [] if self.video is None else self.video[self.cur_frame], self)
        video_edit.resize(self.width() * 20 // 30, self.height() * 20 // 30)
        video_edit.move(self.width() * 10 // 30, self.height() // 15)
        video_edit.setAlignment(Qt.AlignCenter)
        video_edit.setText('Video will be here')

        def show_image(image):
            from skimage.transform import resize
            import qimage2ndarray
            from PyQt5.QtGui import QPixmap
            image = resize(image, (int(image.shape[0] * self.ratio), int(image.shape[1] * self.ratio)))
            qimage = qimage2ndarray.array2qimage(image)
            pixmap = QPixmap(qimage)
            video_edit.setPixmap(pixmap)

        self.show_image = show_image

        def zoom_on_click():
            from PyQt5.QtCore import Qt
            self.ratio *= 1.1
            image = self.video[self.cur_frame]
            self.show_image(image)

        def zoom_out_click():
            from PyQt5.QtCore import Qt
            self.ratio /= 1.1
            image = self.video[self.cur_frame]
            self.show_image(image)

        self.zoom_on.clicked.connect(zoom_on_click)
        self.zoom_out.clicked.connect(zoom_out_click)
        return video_edit

    def createPalitra(self):
        from ui import gui_palette
        import numpy as np
        palitra = gui_palette.GUIPalette(self)
        palitra.setGeometry(self.width() // 30, self.height() // 15, self.width() * 8 // 30, self.height() * 20 // 30)
        palitra.set_colors(np.random.rand(500, 3))

        scroll_area = QScrollArea(self)
        scroll_area.setWidget(palitra)
        scroll_area.setWidgetResizable(True)
        scroll_area.setGeometry(self.width() // 30, self.height() // 15, self.width() * 8 // 30, self.height() * 20 // 30)
        return palitra

    def createNextButton(self):
        from PyQt5.QtWidgets import QPushButton
        btn = QPushButton(self)
        btn.resize(self.width() // 28, self.height() // 28)
        btn.move(self.width() - self.width() // 50 - self.width() // 28, self.height() // 50)
        btn.setText("Next")
        btn.setShortcut('Ctrl+D')
        btn.setEnabled(False)
        btn.clicked.connect(self.nextFrame)
        return btn

    def createPrevButton(self):
        from PyQt5.QtWidgets import QPushButton
        btn = QPushButton(self)
        btn.resize(self.width() // 28, self.height() // 28)
        btn.move(self.width() // 50, self.height() // 50)
        btn.setText("Previous")
        btn.setShortcut('Ctrl+A')
        btn.setEnabled(False)
        btn.clicked.connect(self.prevFrame)
        return btn

    def createVideoButton(self):
        from PyQt5.QtWidgets import QPushButton
        return QPushButton(self)

    def nextFrame(self):
        self.cur_frame += 1
        self.show_image(self.video[self.cur_frame])
        self.prev_button.setEnabled(True)
        if self.cur_frame == self.video_len - 1:
            self.next_button.setEnabled(False)

    def prevFrame(self):
        self.cur_frame -= 1
        self.show_image(self.video[self.cur_frame])
        self.next_button.setEnabled(True)
        if self.cur_frame == 0:
            self.prev_button.setEnabled(False)

    def setVideo(self, path):
        self.video = read_video(path, as_gray=True)[:10]
        self.video = self.full_color.colorize(self.video) * 255
        first_frame = self.video[0]

        image = first_frame
        rects = []
        window = MakeInitialRects(image, rects)
        window.exec()
        initial_rects = []
        for p1, p2 in rects:
            initial_rects.append(((int(p1[1] * image.shape[0]), int(p1[0] * image.shape[1])), (int(p2[1] * image.shape[0]), int(p2[0] * image.shape[1]))))

        self.rects = self.tracker.track(self.video, initial_rects)
        print(self.rects)
        for i in range(len(self.rects[0])):
            for j in range(len(self.rects)):
                rect = self.rects[j][i]
                cv2.rectangle(self.video[i], (rect[0][1], rect[0][0]), (rect[1][1], rect[1][0]), (255, 255, 0))
        self.video_len = self.video.shape[0]
        self.cur_frame = 0
        self.prev_button.setEnabled(False)
        self.zoom_on.setEnabled(True)
        self.zoom_out.setEnabled(True)
        self.show_image(self.video[self.cur_frame])

    def writeVideo(self, path):
        if self.video is None:
            self.makeAlert("Choose video path at first", "You did't specify video, to do it make Ctrl+O choose video, modify it and after it save it")
        write_video(self.video, path)

    def chooseOpenPath(self):
        from PyQt5.QtWidgets import QFileDialog
        path = QFileDialog.getOpenFileName(filter="*.avi")[0]
        if len(path) > 0:
            self.setVideo(path)
            self.next_button.setEnabled(True)
            return path

    def chooseSavePath(self):
        from PyQt5.QtWidgets import QFileDialog
        path = QFileDialog.getSaveFileName(filter="*.avi")[0]
        if len(path) > 0:
            self.writeVideo(path)
            return path

    def makeAlert(self, title, msg):
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(self, title, msg)

    def createMenuBar(self):
        from PyQt5.QtWidgets import QMenuBar, QAction

        menu_bar = QMenuBar(self)
        file_menu = menu_bar.addMenu("&File")

        set_data_path_action = QAction("specify data path", self)
        set_data_path_action.setShortcut('Ctrl+O')
        set_data_path_action.triggered.connect(self.chooseOpenPath)
        file_menu.addAction(set_data_path_action)

        set_export_path_action = QAction("specify export path", self)
        set_export_path_action.setShortcut('Ctrl+S')
        set_export_path_action.triggered.connect(self.chooseSavePath)
        file_menu.addAction(set_export_path_action)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        return menu_bar

    def createZoomOn(self):
        from PyQt5.QtWidgets import QPushButton
        btn = QPushButton(self)
        btn.resize(self.width() // 28, self.height() // 28)
        btn.move(2 * self.width() // 3 - self.width() // 56, self.height() // 50)
        btn.setText("Zoom on")
        btn.setEnabled(False)
        btn.setShortcut("Ctrl+=")
        return btn

    def createZoomOut(self):
        from PyQt5.QtWidgets import QPushButton
        btn = QPushButton(self)
        btn.resize(self.width() // 28, self.height() // 28)
        btn.move(self.width() // 3 - self.width() // 56, self.height() // 50)
        btn.setText("Zoom out")
        btn.setEnabled(False)
        btn.setShortcut("Ctrl+-")
        return btn
