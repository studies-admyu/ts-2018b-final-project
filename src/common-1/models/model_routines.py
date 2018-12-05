# -*- coding: utf-8 -*-

import os
import base64

import numpy as np
import cv2

from skimage import color as skcl

from common.data import colorize_image as CI

PRETRAINED_DEFAULT_PATH = (
    'common/pretrained_models/checkpoints/siggraph_pretrained/latest_net_G.pth'
)

def init_model(
    gpu_id = None, load_size = 256, pretrained_path = PRETRAINED_DEFAULT_PATH
):
    if not os.path.exists(pretrained_path):
        raise FileNotFoundError('Pretrained model file not found')
    
    # Init model first
    colorization_model = CI.ColorizeImageTorch(Xd = load_size)
    colorization_model.prep_net(gpu_id, pretrained_path)
    return colorization_model

def encode_image(image):
    return base64.b64encode(
        cv2.imencode('.png', image)[1].tostring()
    ).decode('ascii')

def decode_image(bstr):
    return cv2.imdecode(
        np.frombuffer(base64.b64decode(bstr), dtype = np.uint8), 1
    )

def makeGrayscale(frame_image_cv2):
    frame_image_gray3_cv2 = cv2.cvtColor(
        cv2.cvtColor(frame_image_cv2, cv2.COLOR_BGR2GRAY),
        cv2.COLOR_GRAY2RGB
    )
    return frame_image_gray3_cv2

def extrapolatePoints(
    frame_from_image_cv2, frame_from_color_points, frame_to_image_cv2
):
        # Don't extrapolate if there are no points
        if len(frame_from_color_points) == 0:
            return []
        
        old_gray = cv2.cvtColor(
            frame_from_image_cv2, cv2.COLOR_BGR2GRAY
        )
        new_gray = cv2.cvtColor(
            frame_to_image_cv2, cv2.COLOR_BGR2GRAY
        )
        
        lk_params = dict(
            winSize = (15, 15), maxLevel = 2,
            criteria = (
                cv2.TermCriteria_EPS | cv2.TermCriteria_COUNT, 10, 0.03
            )
        )
        
        old_points = np.array(
            [[[p['x'], p['y']]] for p in frame_from_color_points]
        ).astype(np.float32)
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
                'x': int(new_pixels[i, 0]), 'y': int(new_pixels[i, 1]),
                'color': frame_from_color_points[i]['color']
            } for i in range(len(frame_from_color_points)) if valid_points[i]
        ]
        
        return new_points

def preprocessColorization(frame_image_cv2, frame_color_points, load_size):
    w = int(max(frame_image_cv2.shape[:2]) / load_size)
    frame_image_gray3_cv2 = makeGrayscale(frame_image_cv2)
    
    incoming_frame_gray_cv2 = cv2.resize(
        frame_image_gray3_cv2, (load_size, load_size),
        interpolation = cv2.INTER_CUBIC
    )
    
    im = np.zeros(incoming_frame_gray_cv2.shape, dtype = np.uint8)
    mask = np.zeros(
        tuple(list(incoming_frame_gray_cv2.shape[:-1]) + [1]),
        dtype = np.uint8
    )
    
    for color_point in frame_color_points:
        point = (
            np.array([color_point['x'], color_point['y']]) *
            load_size /
            np.array(frame_image_cv2.shape[1::-1])
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
    frame_image_l = skcl.rgb2lab(frame_image_cv2)[:, :, 0]
    
    return (incoming_frame_gray_cv2, frame_image_l, im_mask0, im_ab0)

def postprocessColorization(frame_image_l, output_ab):
    out_ab = output_ab.transpose((1, 2, 0))
    out_ab = cv2.resize(
        out_ab, frame_image_l.shape[::-1],
        interpolation = cv2.INTER_CUBIC
    )
    out_lab = np.concatenate(
        (frame_image_l[..., np.newaxis], out_ab),
        axis = 2
    )
    out_img = (np.clip(skcl.lab2rgb(out_lab), 0, 1) * 255).astype(
        np.uint8
    )
    
    return out_img
