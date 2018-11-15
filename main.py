import tensorflow as tf
import sys
# import tensorlayer as tl
import argparse
from split_frames import read_video
import sys
import matplotlib.pyplot as plt
from make_initial_rects import make_initial_rects
from tracker import Tracker
import numpy as np
import cv2
from full_color import colorize
from full_color.options import ModelOptions
from colorize_batch import Colorization
from interface import main_form
from PyQt5.QtWidgets import QApplication


def main(argv=None):
    options = ModelOptions().parse()
    tracker = Tracker()
    full_color = colorize.FullColor(options)
    color = None  # Colorization()

    app = QApplication(argv)
    main_widget = main_form.MainWidget(full_color, color, tracker)
    sys.exit(app.exec_())

    '''
    path = options.path
    video = read_video(path, as_gray=False)
    image = color.colorize(video[:1], np.zeros_like(video[:1])[:, :, :, 0:1])
    plt.imshow(image[0])
    plt.show()


    video = np.uint8(full_color.colorize(video) * 255)
    plt.imshow(video[0])
    plt.show()

    for i in range(video.shape[0]):
        plt.imshow(video[i])
        plt.show()
    exit()
    '''
    '''
    first_frame = video[0]
    initial_rects = make_initial_rects(first_frame)
    mask = tracker.rects2mask(video[0].shape, initial_rects)
    # video[0][mask > 0] = 1.
    # plt.imshow(video[0])
    # plt.show()
    print(initial_rects)
    batch_rects = tracker.track(video, initial_rects)
    print(batch_rects)
    for i in range(len(batch_rects[0])):
        for j in range(len(batch_rects)):
            rect = batch_rects[j][i]
            cv2.rectangle(video[i], (rect[0][1], rect[0][0]), (rect[1][1], rect[1][0]), (255, 255, 0))
        cv2.imshow("tracking", cv2.cvtColor(video[i], cv2.COLOR_RGB2BGR))
        cv2.imwrite('./results/%d.jpg' % i, cv2.cvtColor(video[i], cv2.COLOR_RGB2BGR))
        cv2.waitKey(50)
    '''

if __name__ == '__main__':
    main(sys.argv)
