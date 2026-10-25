"""URL configuration for the parceldesk project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Django's built-in login and logout views.
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("packages.urls")),
]
