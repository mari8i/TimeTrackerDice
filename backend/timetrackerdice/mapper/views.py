import logging
from dataclasses import asdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic.base import TemplateView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import TogglAction, TogglMapping, TogglCredentials
from .toggl import TogglService, TogglInvalidCredentialsError, TogglConnectionError

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def face_changed(request, face: int):
    logger.info(f"User {request.user} switched to face {face}")

    if face < 0 or face > 8:
        raise ValidationError({"error": f"Invalid face {face}"})

    toggl = TogglService(request.user)

    if face == 0:
        toggl.stop_current_time_entry()
    else:
        mapping = request.user.togglmapping_set.select_related('action').get(face=face)

        tags = mapping.action.tags.split(",") if mapping.action.tags else None
        toggl.start_time_entry(mapping.action.name, mapping.action.project, tags=tags)

    response = {
        "status": "success",
        "face": face,
        "action": "stopped" if face == 0 else "started",
    }

    return Response(response, status=status.HTTP_200_OK)


class HomePageView(LoginRequiredMixin, TemplateView):
    template_name = "mapper/home.html"

    def post(self, request):
        toggl = TogglService(request.user)

        for face in range(1, 9):
            action = request.POST['action[' + str(face) + ']']
            project = request.POST['project[' + str(face) + ']']
            tags = request.POST['tags[' + str(face) + ']']

            toggl_project_id = toggl.find_project_id_by_name(project)

            toggl_action, _ = TogglAction.objects.get_or_create(user=request.user, name=action, project=toggl_project_id)

            toggl_action.tags = tags
            toggl_action.save()

            toggl_mapping = TogglMapping.objects.get(user=request.user, face=face)
            toggl_mapping.action = toggl_action
            toggl_mapping.save()

        #messages.info(self.request, "Actions saved!")

        return redirect('home')

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        has_toggl_credentials = bool(self.request.user.togglcredentials.api_key)
        context['has_toggl_credentials'] = has_toggl_credentials

        toggl = TogglService(self.request.user)

        if has_toggl_credentials:
            try:
                context['mappings'] = [add_project_name_to_mapping(toggl, mapping)
                                       for mapping in TogglMapping.objects.filter(user=self.request.user).order_by('face')]
            except TogglInvalidCredentialsError:
                context['has_toggl_credentials'] = False
                messages.error(self.request, "Toggl Credentials not valid")
            except TogglConnectionError:
                messages.error(self.request, "Error connecting to Toggl")

        return context


class SettingsPageView(LoginRequiredMixin, TemplateView):
    template_name = "mapper/settings.html"

    def post(self, request):
        TogglCredentials.objects \
                        .filter(user=request.user) \
                        .update(api_key=request.POST['toggl_api_key'])

        return redirect('settings')

    def get_context_data(self, **kwargs):
        context = super(SettingsPageView, self).get_context_data(**kwargs)
        context['toggl_api_key'] = self.request.user.togglcredentials.api_key

        if self.request.user.togglcredentials.api_key:
            try:
                toggl = TogglService(self.request.user)
                toggl.test_api_key()
            except TogglInvalidCredentialsError:
                messages.error(self.request, "Toggl Credentials not valid")
            except TogglConnectionError:
                messages.error(self.request, "Error connecting to Toggl")

        return context


@login_required
def get_toggl_tags(request):
    toggl = TogglService(request.user)
    toggl_tags = [t.name for t in toggl.fetch_toggl_tags()]
    actions_tags = TogglAction.objects.filter(user=request.user).values_list('tags', flat=True)

    for t in actions_tags:
        if t:
            toggl_tags.extend(t.split(","))

    return JsonResponse(toggl_tags, safe=False)


@login_required
def get_toggl_projects(request):
    toggl = TogglService(request.user)
    projects = toggl.fetch_toggl_projects()
    return JsonResponse([asdict(p) for p in projects], safe=False)


@login_required
def get_existing_actions(request):
    toggl = TogglService(request.user)

    data = [
        {
            "id": a.id,
            "name": a.name,
            "project": toggl.find_project_name_by_id(a.project)
        }
        for a in TogglAction.objects.filter(user=request.user)]

    return JsonResponse(data, safe=False)


def add_project_name_to_mapping(toggl, mapping):
    if mapping.action:
        mapping.action.project_name = toggl.find_project_name_by_id(mapping.action.project) or ""

    return mapping
