from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    # path('accounts/login/', views.login, name='login'),
    path('builder/', views.builder, name='builder'),
    path('admin/dashboard/', views.dashboard, name='dashboard'),
]