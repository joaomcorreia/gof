from django.contrib import admin
from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path
from django.views.generic import RedirectView
from core import views as core_views

urlpatterns = [
    path('admin/print-design/', include('print_design.urls')),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('robots.txt', core_views.robots_txt, name='robots_txt'),
    path('sitemap.xml', core_views.sitemap_xml, name='sitemap_xml'),
    path('help/', RedirectView.as_view(pattern_name='content:help_index', permanent=False)),
    path('help/<slug:slug>/', RedirectView.as_view(pattern_name='content:help_detail', permanent=False)),
    path('blog/', RedirectView.as_view(pattern_name='blog:index', permanent=False)),
    path('blog/category/<slug:slug>/', RedirectView.as_view(pattern_name='blog:category', permanent=False)),
    path('blog/<slug:slug>/', RedirectView.as_view(pattern_name='blog:detail', permanent=False)),
    path('', RedirectView.as_view(pattern_name='core:home', permanent=False)),
]

urlpatterns += i18n_patterns(
    path('', include('ai_starter.urls')),
    path('', include('blog.urls')),
    path('', include('content.urls')),
    path('', include('core.urls')),
)
