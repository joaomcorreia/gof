from django.conf import settings


def site_flags(request):
    return {
        'site_noindex': settings.SITE_NOINDEX,
    }
