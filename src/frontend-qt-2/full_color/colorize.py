import tensorflow as tf
from .models import Places365Model
import cv2
import numpy as np


class FullColor:
    def __init__(self, options):
        self.graph = tf.Graph()
        with self.graph.as_default():
            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True
            self.sess = tf.Session(config=config)
            options.mode = 1
            self.model = Places365Model(self.sess, options)
            self.model.build()
            self.sess.run(tf.global_variables_initializer())
            self.model.load()

    def colorize(self, gray_batch):
        with self.graph.as_default():
            res = []
            for i in range(0, gray_batch.shape[0], 3):
                res.append(self.model.transform(gray_batch[i: min(i + 3, gray_batch.shape[0])]))
            return np.concatenate(res, axis=0)
