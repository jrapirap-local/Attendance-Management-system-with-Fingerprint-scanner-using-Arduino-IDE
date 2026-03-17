from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path('builder2/', views.builder2, name='builder2'),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("news/", views.news, name="news"),
    path("instructor/", views.instructor, name="instructor"),
    path("instructor-new/", views.instructornew, name="instructornew"),
    path("", views.sidebar, name="sidebar"),
    path("attendance/", views.attendance, name="attendance"),
]