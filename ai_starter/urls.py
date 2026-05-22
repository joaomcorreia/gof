from django.urls import path

from . import views

app_name = 'ai_starter'

urlpatterns = [
    path('start/', views.start_onboarding, name='start'),
    path('preview/<uuid:public_id>/', views.preview, name='preview'),
    path('preview/<uuid:public_id>/frame/', views.preview_frame, name='preview_frame'),
]
