import logging

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated

from toggl.TogglPy import Toggl

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def face_changed(request, face):
    logger.info("User %s changed device %s to face: %d", request.user, 'LOL', face)

    toggl = Toggl()
    toggl.setAPIKey(request.user.togglcredentials.api_key)

    if face == 0:
        currentTimer = toggl.currentRunningTimeEntry()
        toggl.stopTimeEntry(currentTimer['data']['id'])
    else:
        mapping = request.user.togglmapping_set.get(face=face)
                
        # You can get your project pid in toggl.com->Projects->(select your project)
        # and copying the last number of the url
        toggl.startTimeEntry(mapping.action.name, mapping.action.project)
    
    return Response("Hello World")
