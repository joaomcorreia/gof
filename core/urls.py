from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('how-it-works/', views.how_it_works, name='how_it_works'),
    path('examples/', views.examples, name='examples'),
    path('plans/', views.plans, name='plans'),
    path('faq/', views.faq, name='faq'),
    path('contact/', views.contact, name='contact'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms, name='terms'),
    path('plans/one-time-website/', views.one_time_website_plan, name='one_time_website_plan'),
    path('plans/monthly-website/', views.monthly_plan, name='monthly_plan'),
    path('plans/monthly-plan/', views.monthly_plan, name='monthly_plan_legacy'),
    path('plans/ecommerce-plan/', views.ecommerce_plan, name='ecommerce_plan'),
    path('ai-website/', views.ai_website, name='ai_website'),
    path('business-website/', views.business_website, name='business_website'),
    path('managed/', views.managed, name='managed'),
]
