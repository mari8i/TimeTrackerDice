import logging

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from mapper import views


urlpatterns = [
    path('<int:face>', views.face_changed),
]

urlpatterns = format_suffix_patterns(urlpatterns)
