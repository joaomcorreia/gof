from django.urls import path

from . import views

app_name = 'print_design'

urlpatterns = [
    path('', views.index, name='index'),
    path('<slug:service_slug>/', views.service_detail, name='service_detail'),
]
