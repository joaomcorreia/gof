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
    path('', core_views.redirect_public_entry_to_language, {'url_name': 'core:home'}),
    path('start/', core_views.redirect_public_entry_to_language, {'url_name': 'ai_starter:start'}),
    path('pricing/', core_views.redirect_public_entry_to_language, {'url_name': 'core:pricing'}),
    path('contact/', core_views.redirect_public_entry_to_language, {'url_name': 'core:contact'}),
    path('staff/', core_views.unprefixed_staff_route_not_found),
    path('help/', core_views.redirect_public_entry_to_language, {'url_name': 'content:help_index'}),
    path('blog/', core_views.redirect_public_entry_to_language, {'url_name': 'blog:index'}),
    path('help/<slug:slug>/', RedirectView.as_view(pattern_name='content:help_detail', permanent=False)),
    path('blog/category/<slug:slug>/', RedirectView.as_view(pattern_name='blog:category', permanent=False)),
    path('blog/<slug:slug>/', RedirectView.as_view(pattern_name='blog:detail', permanent=False)),
]

urlpatterns += i18n_patterns(
    path('', include('ai_starter.urls')),
    path('', include('blog.urls')),
    path('', include('content.urls')),
    path('', include('core.urls')),
)
