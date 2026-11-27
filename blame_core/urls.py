"""
URL configuration for blame_core project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("blame_app.urls")),
]
