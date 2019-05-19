import logging

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from mapper import views


urlpatterns = [
    path('faces/<int:face>', views.face_changed),
    path('home', views.HomePageView.as_view(), name='home'),
    path('projects', views.ProjectsAutocomplete.as_view(),
         name='projects-autocomplete'),    
]

urlpatterns = format_suffix_patterns(urlpatterns)
