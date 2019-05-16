import logging

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def face_changed(request, face):
    logger.info("User %s changed device %s to face: %d", request.user, 'LOL', face)
    
    return Response("Hello World")
