from django.urls import path

from . import views

app_name = 'content'

urlpatterns = [
    path('help/', views.help_index, name='help_index'),
    path('help/<slug:slug>/', views.help_detail, name='help_detail'),
    path('blog/', views.blog_index, name='blog_index'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
]

