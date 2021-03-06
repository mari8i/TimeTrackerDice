import logging

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from mapper import views


urlpatterns = [
    path('faces/<int:face>', views.face_changed),
    path('', views.HomePageView.as_view(), name='home'),
    path('settings/', views.SettingsPageView.as_view(), name='settings'),    
    path('toggl/projects', views.get_toggl_projects, name='toggl-projects'),
    path('toggl/actions', views.get_existing_actions, name='toggl-actions'),
    path('toggl/tags', views.get_toggl_tags, name='toggl-tags'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
