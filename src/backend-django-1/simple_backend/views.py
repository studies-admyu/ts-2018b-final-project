# -*- coding: utf-8 -*-

from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import JSONParser

from rest_framework.permissions import IsAuthenticated

import common.models.model_routines as mr

BACKEND_MODEL = mr.init_model()

@api_view(['POST'])
@permission_classes((IsAuthenticated, ))
def authenticate(request):
    return HttpResponse('', status = 200)

@api_view(['POST'])
@permission_classes((IsAuthenticated, ))
def extrapolateColorPoints(request):
    frame = JSONParser().parse(request)
    frame_from_image_cv2 = mr.decode_image(frame['image_from'])
    frame_to_image_cv2 = mr.decode_image(frame['image_to'])
    frame_from_color_points = frame['color_points']
    
    new_points = mr.extrapolatePoints(
        frame_from_image_cv2, frame_from_color_points, frame_to_image_cv2
    )
    
    incoming_frame_gray_cv2, frame_image_l, im_mask0, im_ab0 = \
        mr.preprocessColorization(
            frame_to_image_cv2, new_points, BACKEND_MODEL.Xd
        )
    
    BACKEND_MODEL.set_image(incoming_frame_gray_cv2)
    BACKEND_MODEL.net_forward(im_ab0, im_mask0)
    
    out_img = mr.postprocessColorization(
        frame_image_l, BACKEND_MODEL.output_ab
    )
    
    out_dict = {
        'image': mr.encode_image(out_img),
        'color_points': new_points
    }
    
    return JsonResponse(out_dict, status = 200)

@api_view(['POST'])
@permission_classes((IsAuthenticated, ))
def colorizeByPoints(request):
    frame = JSONParser().parse(request)
    frame_image_cv2 = mr.decode_image(frame['image'])
    frame_color_points = frame['color_points']
    
    incoming_frame_gray_cv2, frame_image_l, im_mask0, im_ab0 = \
        mr.preprocessColorization(
            frame_image_cv2, frame_color_points, BACKEND_MODEL.Xd
        )
    
    BACKEND_MODEL.set_image(incoming_frame_gray_cv2)
    BACKEND_MODEL.net_forward(im_ab0, im_mask0)
    
    out_img = mr.postprocessColorization(
        frame_image_l, BACKEND_MODEL.output_ab
    )
    
    image_out_str = mr.encode_image(out_img)
    return HttpResponse(
        image_out_str, status = 200,
        content_type = 'image/png;base64'
    )
