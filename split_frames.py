import os
import pylab
import imageio
import skvideo.io
import numpy as np


def read_video(path, as_gray=False):
    videodata = skvideo.io.vread(path)
    if as_gray:
        videodata = np.mean(videodata, axis=-1, keepdims=True)
        videodata = np.concatenate([videodata, videodata, videodata], axis=-1)
    return videodata


def write_video(video, path):
    pass
