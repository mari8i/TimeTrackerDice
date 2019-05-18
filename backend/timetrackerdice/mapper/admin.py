from django.contrib import admin

from .models import TogglCredentials, TogglAction, TogglMapping

admin.site.register(TogglCredentials)
admin.site.register(TogglAction)
admin.site.register(TogglMapping)
