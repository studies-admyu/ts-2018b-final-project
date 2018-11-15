import colorize_image as CI
from skimage import color
import numpy as np


class Colorization:
    def __init__(self):
        self.colorModel = CI.ColorizeImageTorch(256)
        self.colorModel.prep_net(path='./models/pytorch/model.pth')

        self.distModel = CI.ColorizeImageTorchDist(256)
        self.distModel.prep_net(path='./models/pytorch/model.pth', dist=True)

    def colorize(self, batch, masks):
        res = []
        for i in range(batch.shape[0]):
            image = batch[i]
            mask = masks[i]
            self.colorModel.set_image(image / 255.)
            # self.distModel.set_image(image)
            image = np.transpose(color.rgb2lab(image / 255.), (2, 0, 1))
            ab = image[1:3, :, :]
            mask = np.transpose((mask > 0.0), (2, 0, 1))
            res.append(self.colorModel.net_forward(ab, mask))
        return np.stack(res, 0)
