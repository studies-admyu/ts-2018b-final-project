import tensorflow as tf
import tensorlayer as tl
from skimage.draw import rectangle
import numpy as np
from adnet.runner import ADNetRunner
from adnet.runner import BoundingBox, Coordinate
from siamese_fc import tracker


'''
##  FIX: DOESNOTWORK
class Tracker:
    def __init__(self):
        self.adnet = ADNetRunner()

    def rects2mask(self, shape, rects):
        mask = np.zeros(shape, dtype=np.int32)
        for p1, p2 in rects:
            rr, cc = rectangle(p1, p2)
            mask[rr, cc, :] = 255
        return mask

    def track(self, batch, initial_rects):
        self.adnet.imgwh = Coordinate.get_imgwh(batch[0])
        batch_rects = [[None] * len(initial_rects)] * batch.shape[0]
        for j, initial_rect in enumerate(initial_rects):
            p1, p2 = initial_rect
            curr_bbox = BoundingBox(p1[1], p1[0], p2[1] - p1[1], p2[0] - p1[0])
            rects = []
            self.adnet.initial_finetune(batch[0], curr_bbox)
            for i in range(batch.shape[0]):
                curr_bbox = self.adnet.tracking(batch[i], curr_bbox)
                batch_rects[i][j] = ((curr_bbox.xy.y, curr_bbox.xy.x), (curr_bbox.xy.y + curr_bbox.wh.y, curr_bbox.xy.x + curr_bbox.wh.x))

        return batch_rects

    def get_masks(self, batch, initial_rects):
        batch_rects = self.track(batch, initial_rects)
        for i in range(len(batch_rects)):
            yield self.rects2mask(batch[i].shape, batch_rects[i])
'''


class Tracker:
    def __init__(self):
        self.graph = tf.Graph()
        with self.graph.as_default():
            self.sess, self.exemplarOp, self.instanceOp, self.exemplarOpBak, self.instanceOpBak, self.isTrainingOp, self.sn, self.scoreOpBak, self.zFeatOp = tracker.build()

    def rects2mask(self, shape, rects):
        mask1 = np.zeros(shape, dtype=np.int32)
        mask2 = np.zeros(shape, dtype=np.int32)
        mask = np.zeros(shape, dtype=np.int32)
        for p1, p2 in rects:
            p1 = np.array(p1)
            p2 = np.array(p2)
            rr, cc = rectangle(p1, p2)
            rr = np.clip(rr, 0, shape[0] - 1)
            cc = np.clip(cc, 0, shape[1] - 1)
            mask1[rr, cc, :] = 255
            rr, cc = rectangle(p1 + 10, p2 - 10)
            rr = np.clip(rr, 0, shape[0] - 1)
            cc = np.clip(cc, 0, shape[1] - 1)
            mask[rr, cc, :] = 255
            # mask = mask2 - mask1
        return mask

    def track(self, batch, initial_rects):
        with self.graph.as_default():
            batch = list(map(lambda x: x[0].astype(np.float32), np.split(batch, batch.shape[0], axis=0)))
            batch_rects = []
            for j, initial_rect in enumerate(initial_rects):
                rects = []
                p1, p2 = initial_rect
                targetPosition = np.array([(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2])
                targetSize = np.array([p2[0] - p1[0], p2[1] - p1[1]])
                k = 10
                base_rects = tracker.track(batch[::k], targetPosition, targetSize, self.sess, self.exemplarOp, self.instanceOp, self.exemplarOpBak, self.instanceOpBak, self.isTrainingOp, self.sn, self.scoreOpBak, self.zFeatOp)
                for i in range(0, len(batch), k):
                    p1, p2 = base_rects[i // k]
                    targetPosition = np.array([(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2])
                    targetSize = np.array([p2[0] - p1[0], p2[1] - p1[1]])
                    cur_rects = tracker.track(batch[i: min(i + k, len(batch))], targetPosition, targetSize, self.sess, self.exemplarOp, self.instanceOp, self.exemplarOpBak, self.instanceOpBak, self.isTrainingOp, self.sn, self.scoreOpBak, self.zFeatOp)
                    rects.extend(cur_rects)
                batch_rects.append(rects)
            return batch_rects

    def get_masks(self, batch, initial_rects):
        batch_rects = self.track(batch, initial_rects)
        return [self.rects2mask(batch[i].shape, batch_rects[i]) for i in range(len(batch_rects))]
