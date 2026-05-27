from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


PRINT_SERVICES = [
    {
        'slug': 'business-cards',
        'title': _('Business Cards'),
    },
    {
        'slug': 'flyers',
        'title': _('Flyers'),
    },
    {
        'slug': 'banners',
        'title': _('Banners'),
    },
    {
        'slug': 'stickers',
        'title': _('Stickers'),
    },
    {
        'slug': 'menus',
        'title': _('Menus'),
    },
    {
        'slug': 'vehicle-graphics',
        'title': _('Vehicle Graphics'),
    },
    {
        'slug': 'custom-print-request',
        'title': _('Custom Print Request'),
    },
]


def _service_by_slug(service_slug):
    for service in PRINT_SERVICES:
        if service['slug'] == service_slug:
            return service
    raise Http404


@staff_member_required(login_url='/admin/login/')
def index(request):
    return render(
        request,
        'print_design/index.html',
        {
            'page_title': _('Print & Design'),
            'page_intro': _(
                'Private preparation area for future print and signage services.'
            ),
            'services': PRINT_SERVICES,
            'placeholder_message': _(
                'This service is being prepared and is not available yet.'
            ),
        },
    )


@staff_member_required(login_url='/admin/login/')
def service_detail(request, service_slug):
    service = _service_by_slug(service_slug)
    return render(
        request,
        'print_design/detail.html',
        {
            'page_title': service['title'],
            'section_title': _('Print & Design'),
            'service': service,
            'services': PRINT_SERVICES,
            'placeholder_message': _(
                'This service is being prepared and is not available yet.'
            ),
        },
    )
