"""
URL configuration for zit_core project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("zit_app.urls")),
]
