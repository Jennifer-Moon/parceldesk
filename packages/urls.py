from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.staff_dashboard, name="staff_dashboard"),
    path("my-packages/", views.resident_packages, name="resident_packages"),
]
