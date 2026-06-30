from django.urls import path

from . import views

app_name = 'ai_starter'

urlpatterns = [
    path('start/', views.start_onboarding, name='start'),
    path('gemeente-offer/', views.meeting_offer_request, name='meeting_offer'),
    path('staff/', views.staff_root_redirect, name='staff_root'),
    path('staff/assistant/', views.staff_assistant, name='staff_assistant'),
    path('staff/handoffs/', views.staff_handoffs, name='staff_handoffs'),
    path('staff/template-wireframes/', views.staff_template_wireframes, name='staff_template_wireframes'),
    path('staff/template-preview/<slug:template_slug>/', views.template_preview, name='template_preview'),
    path('preview/<uuid:public_id>/', views.preview, name='preview'),
    path('preview/<uuid:public_id>/prepare-handoff/', views.prepare_wordpress_handoff, name='prepare_handoff'),
    path('preview/<uuid:public_id>/frame/', views.preview_frame, name='preview_frame'),
]
