import logging

from django.shortcuts import render, redirect
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
from .models import TogglAction, TogglMapping
from django.http import JsonResponse

from functools import lru_cache

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
    
    def post(self, request):
        action = request.POST['action']
        project = request.POST['project']
        face = request.POST['face']
        
        projects = fetch_toggl_projects(request.user.togglcredentials.api_key)

        try:
            project_id = next(p['id']
                              for p in projects
                              if p['name'] == project)
        except:
            project_id = None

        try:
            toggl_action = TogglAction.objects.get(user=request.user, name=action)            
            toggl_action.project = project_id
        except TogglAction.DoesNotExist:
            toggl_action = TogglAction(user=request.user, name=action, project=project_id)
            
        toggl_action.save()

        toggl_mapping = TogglMapping.objects.get(user=request.user, face=face)
        toggl_mapping.action = toggl_action
        toggl_mapping.save()
        
        
        messages.info(self.request, "Action for face " + str(face) + " saved!")
        
        return redirect('home')
    
    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        #messages.info(self.request, "hello http://example.com")
        projects = fetch_toggl_projects(self.request.user.togglcredentials.api_key)
        
        context['mappings'] = [add_project_name_to_mapping(projects, mapping)
                               for mapping in TogglMapping.objects.filter(user=self.request.user).order_by('face')]
        
        return context

@lru_cache(maxsize=None)
def fetch_toggl_projects(api_key):
    logger.info("Fetching toggl projects for api_key: " + api_key)
    toggl = Toggl()
    toggl.setAPIKey(api_key)

    default_workspace = toggl.getWorkspaces()[0]
    return toggl.request("https://www.toggl.com/api/v8/workspaces/" + str(default_workspace['id']) + "/projects")
    
@login_required
def get_toggl_projects(request):
    projects = fetch_toggl_projects(request.user.togglcredentials.api_key)

    data = [
        {
            "id": p['id'],
            "name": p['name']
        }
        for p in projects]

    return JsonResponse(data, safe=False)

@login_required
def get_existing_actions(request):
    projects = fetch_toggl_projects(request.user.togglcredentials.api_key)
    
    data = [
        {
            "id": a.id,
            "name": a.name,
            "project": find_project_name_by_id(projects, a.project)
        }
        for a in TogglAction.objects.filter(user=request.user)]

    return JsonResponse(data, safe=False)


def find_project_name_by_id(projects, project_id):
    if project_id is None:
        return None
    
    try:
        return next(project['name']
                    for project in projects
                    if project['id'] == project_id)
    except:
        return None

def add_project_name_to_mapping(projects, mapping):
    if mapping.action:
        mapping.action.project_name = find_project_name_by_id(projects, mapping.action.project) or ""
        
    return mapping
