from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    path('blog/', views.index, name='index'),
    path('blog/category/<slug:slug>/', views.category_detail, name='category'),
    path('blog/<slug:slug>/', views.detail, name='detail'),
    path('dashboard/guides/', views.guides_index, name='guides_index'),
    path('dashboard/guides/<slug:slug>/', views.guides_detail, name='guides_detail'),
]

