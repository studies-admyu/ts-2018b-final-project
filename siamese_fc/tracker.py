# Suofei ZHANG, 2017.

import os
import tensorflow as tf
import numpy as np
import glob
# import matplotlib.image as mpimg
# from PIL import Image
# from skimage import transform
import cv2
import scipy.io as sio
import time

from siamese_fc import utils
from siamese_fc.siamese_net import SiameseNet
from siamese_fc.parameters import configParams


def getOpts(opts):
    opts['numScale'] = 3
    opts['scaleStep'] = 1.0375
    opts['scalePenalty'] = 0.9745
    # opts['scalePenalty'] = 1/0.9745
    opts['scaleLr'] = 0.59
    opts['responseUp'] = 16
    opts['windowing'] = 'cosine'
    opts['wInfluence'] = 0.176
    opts['exemplarSize'] = 127
    opts['instanceSize'] = 255
    opts['scoreSize'] = 17
    opts['totalStride'] = 8
    opts['contextAmount'] = 0.5
    opts['trainWeightDecay'] = 5e-04
    opts['stddev'] = 0.03
    opts['subMean'] = False

    opts['video'] = 'forest_bag'
    opts['modelPath'] = './siamese_fc/models/'
    opts['modelName'] = opts['modelPath'] + "model_tf.ckpt"
    opts['summaryFile'] = './data_track/' + opts['video'] + '_20170518'

    return opts


def getAxisAlignedBB(region):
    region = np.array(region)
    nv = region.size
    assert (nv == 8 or nv == 4)

    if nv == 8:
        xs = region[0::2]
        ys = region[1::2]
        cx = np.mean(xs)
        cy = np.mean(ys)
        x1 = min(xs)
        x2 = max(xs)
        y1 = min(ys)
        y2 = max(ys)
        A1 = np.linalg.norm(np.array(region[0:2]) - np.array(region[2:4])) * np.linalg.norm(np.array(region[2:4]) - np.array(region[4:6]))
        A2 = (x2 - x1) * (y2 - y1)
        s = np.sqrt(A1 / A2)
        w = s * (x2 - x1) + 1
        h = s * (y2 - y1) + 1
    else:
        x = region[0]
        y = region[1]
        w = region[2]
        h = region[3]
        cx = x + w / 2
        cy = y + h / 2

    return cx - 1, cy - 1, w, h


def frameGenerator(vpath):
    imgs = []
    imgFiles = [imgFile for imgFile in glob.glob(os.path.join(vpath, "*.png"))]
    for imgFile in imgFiles:
        if imgFile.find('00000001.png') >= 0:
            imgFiles.remove(imgFile)

    imgFiles.sort()

    for imgFile in imgFiles:
        # imgs.append(mpimg.imread(imgFile).astype(np.float32))
        # imgs.append(np.array(Image.open(imgFile)).astype(np.float32))
        img = cv2.imread(imgFile).astype(np.float32)
        imgs.append(img)

    return imgs


def loadVideoInfo(basePath, video):
    videoPath = os.path.join(basePath, video, 'imgs')
    groundTruthFile = os.path.join(basePath, video, 'groundtruth.txt')

    groundTruth = open(groundTruthFile, 'r')
    reader = groundTruth.readline()
    region = [float(i) for i in reader.strip().split(",")]
    cx, cy, w, h = getAxisAlignedBB(region)
    pos = [cy, cx]
    targetSz = [h, w]

    imgs = frameGenerator(videoPath)

    return imgs, np.array(pos), np.array(targetSz)


def getSubWinTracking(img, pos, modelSz, originalSz, avgChans):
    if originalSz is None:
        originalSz = modelSz

    sz = originalSz
    im_sz = img.shape
    # make sure the size is not too small
    assert min(im_sz[:2]) > 2, "the size is too small"
    c = (np.array(sz) + 1) / 2

    # check out-of-bounds coordinates, and set them to black
    context_xmin = round(pos[1] - c[1])
    context_xmax = context_xmin + sz[1] - 1
    context_ymin = round(pos[0] - c[0])
    context_ymax = context_ymin + sz[0] - 1
    left_pad = max(0, int(-context_xmin))
    top_pad = max(0, int(-context_ymin))
    right_pad = max(0, int(context_xmax - im_sz[1] + 1))
    bottom_pad = max(0, int(context_ymax - im_sz[0] + 1))

    context_xmin = int(context_xmin + left_pad)
    context_xmax = int(context_xmax + left_pad)
    context_ymin = int(context_ymin + top_pad)
    context_ymax = int(context_ymax + top_pad)

    if top_pad or left_pad or bottom_pad or right_pad:
        r = np.pad(img[:, :, 0], ((top_pad, bottom_pad), (left_pad, right_pad)), mode='constant',
                   constant_values=avgChans[0])
        g = np.pad(img[:, :, 1], ((top_pad, bottom_pad), (left_pad, right_pad)), mode='constant',
                   constant_values=avgChans[1])
        b = np.pad(img[:, :, 2], ((top_pad, bottom_pad), (left_pad, right_pad)), mode='constant',
                   constant_values=avgChans[2])
        r = np.expand_dims(r, 2)
        g = np.expand_dims(g, 2)
        b = np.expand_dims(b, 2)
        img = np.concatenate((r, g, b), axis=2)

    im_patch_original = img[context_ymin:context_ymax + 1, context_xmin:context_xmax + 1, :]
    if not np.array_equal(modelSz, originalSz):
        im_patch = cv2.resize(im_patch_original, modelSz)
    else:
        im_patch = im_patch_original

    return im_patch, im_patch_original


def makeScalePyramid(im, targetPosition, in_side_scaled, out_side, avgChans, stats, p):
    """
    computes a pyramid of re-scaled copies of the target (centered on TARGETPOSITION)
    and resizes them to OUT_SIDE. If crops exceed image boundaries they are padded with AVGCHANS.

    """
    in_side_scaled = np.round(in_side_scaled)
    max_target_side = int(round(in_side_scaled[-1]))
    min_target_side = int(round(in_side_scaled[0]))
    beta = out_side / float(min_target_side)
    search_side = int(round(beta * max_target_side))
    search_region, _ = getSubWinTracking(im, targetPosition, (search_side, search_side), (max_target_side, max_target_side), avgChans)
    if p['subMean']:
        pass
    assert round(beta * min_target_side) == int(out_side)

    tmp_list = []
    tmp_pos = ((search_side - 1) / 2., (search_side - 1) / 2.)
    for s in range(p['numScale']):
        target_side = round(beta * in_side_scaled[s])
        tmp_region, _ = getSubWinTracking(search_region, tmp_pos, (out_side, out_side), (target_side, target_side), avgChans)
        tmp_list.append(tmp_region)

    pyramid = np.stack(tmp_list)

    return pyramid


def trackerEval(score, sx, targetPosition, window, opts):
    # responseMaps = np.transpose(score[:, :, :, 0], [1, 2, 0])
    responseMaps = score[:, :, :, 0]
    upsz = opts['scoreSize'] * opts['responseUp']
    # responseMapsUp = np.zeros([opts['scoreSize']*opts['responseUp'], opts['scoreSize']*opts['responseUp'], opts['numScale']])
    responseMapsUP = []

    if opts['numScale'] > 1:
        currentScaleID = int(opts['numScale'] / 2)
        bestScale = currentScaleID
        bestPeak = -float('Inf')

        for s in range(opts['numScale']):
            if opts['responseUp'] > 1:
                responseMapsUP.append(cv2.resize(responseMaps[s, :, :], (upsz, upsz), interpolation=cv2.INTER_CUBIC))
            else:
                responseMapsUP.append(responseMaps[s, :, :])

            thisResponse = responseMapsUP[-1]

            if s != currentScaleID:
                thisResponse = thisResponse * opts['scalePenalty']

            thisPeak = np.max(thisResponse)
            if thisPeak > bestPeak:
                bestPeak = thisPeak
                bestScale = s

        responseMap = responseMapsUP[bestScale]
    else:
        responseMap = cv2.resize(responseMaps[0, :, :], (upsz, upsz), interpolation=cv2.INTER_CUBIC)
        bestScale = 0

    responseMap = responseMap - np.min(responseMap)
    responseMap = responseMap / np.sum(responseMap)

    responseMap = (1 - opts['wInfluence']) * responseMap + opts['wInfluence'] * window
    rMax, cMax = np.unravel_index(responseMap.argmax(), responseMap.shape)
    pCorr = np.array((rMax, cMax))
    dispInstanceFinal = pCorr - int(upsz / 2)
    dispInstanceInput = dispInstanceFinal * opts['totalStride'] / opts['responseUp']
    dispInstanceFrame = dispInstanceInput * sx / opts['instanceSize']
    newTargetPosition = targetPosition + dispInstanceFrame

    return newTargetPosition, bestScale


def build():
    opts = configParams()
    opts = getOpts(opts)

    exemplarOp = tf.placeholder(tf.float32, [1, opts['exemplarSize'], opts['exemplarSize'], 3])
    instanceOp = tf.placeholder(tf.float32, [opts['numScale'], opts['instanceSize'], opts['instanceSize'], 3])
    exemplarOpBak = tf.placeholder(tf.float32, [opts['trainBatchSize'], opts['exemplarSize'], opts['exemplarSize'], 3])
    instanceOpBak = tf.placeholder(tf.float32, [opts['trainBatchSize'], opts['instanceSize'], opts['instanceSize'], 3])
    isTrainingOp = tf.convert_to_tensor(False, dtype='bool', name='is_training')

    sn = SiameseNet()
    scoreOpBak = sn.buildTrainNetwork(exemplarOpBak, instanceOpBak, opts, isTraining=False)
    saver = tf.train.Saver()
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    sess = tf.Session(config=config)
    saver.restore(sess, opts['modelName'])
    zFeatOp = sn.buildExemplarSubNetwork(exemplarOp, opts, isTrainingOp)
    return sess, exemplarOp, instanceOp, exemplarOpBak, instanceOpBak, isTrainingOp, sn, scoreOpBak, zFeatOp


def track(imgs, targetPosition, targetSize, sess, exemplarOp, instanceOp, exemplarOpBak, instanceOpBak, isTrainingOp, sn, scoreOpBak, zFeatOp):
    imgs = list(map(lambda x: cv2.cvtColor(x, cv2.COLOR_RGB2BGR), imgs))
    opts = configParams()
    opts = getOpts(opts)

    # imgs, targetPosition, targetSize = loadVideoInfo(opts['seq_base_path'], opts['video'])
    nImgs = len(imgs)
    startFrame = 0
    im = imgs[startFrame]
    if(im.shape[-1] == 1):
        tmp = np.zeros([im.shape[0], im.shape[1], 3], dtype=np.float32)
        tmp[:, :, 0] = tmp[:, :, 1] = tmp[:, :, 2] = np.squeeze(im)
        im = tmp

    avgChans = np.mean(im, axis=(0, 1))  # [np.mean(np.mean(img[:, :, 0])), np.mean(np.mean(img[:, :, 1])), np.mean(np.mean(img[:, :, 2]))]
    wcz = targetSize[1] + opts['contextAmount'] * np.sum(targetSize)
    hcz = targetSize[0] + opts['contextAmount'] * np.sum(targetSize)
    sz = np.sqrt(wcz * hcz)
    scalez = opts['exemplarSize'] / sz

    zCrop, _ = getSubWinTracking(im, targetPosition, (opts['exemplarSize'], opts['exemplarSize']), (np.around(sz), np.around(sz)), avgChans)

    if opts['subMean']:
        pass

    dSearch = (opts['instanceSize'] - opts['exemplarSize']) / 2
    pad = dSearch / scalez
    sx = sz + 2 * pad

    minSx = 0.2 * sx
    maxSx = 5.0 * sx

    winSz = opts['scoreSize'] * opts['responseUp']
    if opts['windowing'] == 'cosine':
        hann = np.hanning(winSz).reshape(winSz, 1)
        window = hann.dot(hann.T)
    elif opts['windowing'] == 'uniform':
        window = np.ones((winSz, winSz), dtype=np.float32)

    window = window / np.sum(window)
    scales = np.array([opts['scaleStep'] ** i for i in range(int(np.ceil(opts['numScale'] / 2.0) - opts['numScale']), int(np.floor(opts['numScale'] / 2.0) + 1))])

    zCrop = np.expand_dims(zCrop, axis=0)
    zFeat = sess.run(zFeatOp, feed_dict={exemplarOp: zCrop})
    zFeat = np.transpose(zFeat, [1, 2, 3, 0])
    zFeatConstantOp = tf.constant(zFeat, dtype=tf.float32)
    scoreOp = sn.buildInferenceNetwork(instanceOp, zFeatConstantOp, opts, isTrainingOp)

    resPath = os.path.join(opts['seq_base_path'], opts['video'], 'res')
    bBoxes = np.zeros([nImgs, 4])

    tic = time.time()
    res = []
    for i in range(startFrame, nImgs):
        if i > startFrame:
            im = imgs[i]

            if(im.shape[-1] == 1):
                tmp = np.zeros([im.shape[0], im.shape[1], 3], dtype=np.float32)
                tmp[:, :, 0] = tmp[:, :, 1] = tmp[:, :, 2] = np.squeeze(im)
                im = tmp

            scaledInstance = sx * scales
            scaledTarget = np.array([targetSize * scale for scale in scales])

            xCrops = makeScalePyramid(im, targetPosition, scaledInstance, opts['instanceSize'], avgChans, None, opts)
            # sio.savemat('pyra.mat', {'xCrops': xCrops})

            score = sess.run(scoreOp, feed_dict={instanceOp: xCrops})

            newTargetPosition, newScale = trackerEval(score, round(sx), targetPosition, window, opts)
            targetPosition = newTargetPosition
            sx = max(minSx, min(maxSx, (1 - opts['scaleLr']) * sx + opts['scaleLr'] * scaledInstance[newScale]))
            targetSize = (1 - opts['scaleLr']) * targetSize + opts['scaleLr'] * scaledTarget[newScale]
        else:
            pass

        rectPosition = targetPosition - targetSize / 2.
        tl = tuple(np.round(rectPosition).astype(int))
        br = tuple(np.round(rectPosition + targetSize).astype(int))
        res.append((tl, br))
    return res
