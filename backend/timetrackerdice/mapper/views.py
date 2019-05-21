import logging

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated

from django.views.generic.base import TemplateView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from toggl.TogglPy import Toggl
from dal import autocomplete
from .models import TogglAction
from django.http import JsonResponse

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

class HomePageView(LoginRequiredMixin, TemplateView):
    template_name = "mapper/home.html"

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        #messages.info(self.request, "hello http://example.com")
        return context


@login_required
def get_toggl_projects(request):
    toggl = Toggl()
    toggl.setAPIKey(request.user.togglcredentials.api_key)

    default_workspace = toggl.getWorkspaces()[0]
    projects = toggl.request("https://www.toggl.com/api/v8/workspaces/" + str(default_workspace['id']) + "/projects")

    data = [
        {
            "id": p['id'],
            "name": p['name']
        }
        for p in projects]

    return JsonResponse(data, safe=False)

@login_required
def get_existing_actions(request):
    data = [
        {
            "id": a.id,
            "name": a.name
        }
        for a in TogglAction.objects.filter(user=request.user)]

    return JsonResponse(data, safe=False)
