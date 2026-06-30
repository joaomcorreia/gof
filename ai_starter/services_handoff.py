from decimal import Decimal

from django.utils import timezone


def _serialize_site_content(site):
    return [
        {
            'section_key': content.section_key,
            'field_key': content.field_key,
            'value': content.value,
            'language': content.language,
        }
        for content in site.contents.order_by('language', 'section_key', 'field_key')
    ]


def _serialize_website_request_files(website_request):
    files = []

    file_manager = getattr(website_request, 'files', None)
    if file_manager is None:
        return files

    for request_file in file_manager.all():
        files.append(
            {
                'original_name': getattr(request_file, 'original_name', ''),
                'file_name': getattr(getattr(request_file, 'file', None), 'name', ''),
                'created_at': (
                    request_file.created_at.isoformat()
                    if getattr(request_file, 'created_at', None) is not None
                    else None
                ),
            }
        )

    return files


def _website_request_value(website_request, field_name):
    value = getattr(website_request, field_name, None)
    if isinstance(value, Decimal):
        return str(value)
    return value


def _serialize_website_request(website_request):
    if website_request is None:
        return None

    payload = {
        'public_id': str(getattr(website_request, 'public_id', '')) or None,
        'business_name': _website_request_value(website_request, 'business_name'),
        'business_type': _website_request_value(website_request, 'business_type'),
        'contact_name': _website_request_value(website_request, 'contact_name'),
        'contact_email': _website_request_value(website_request, 'contact_email'),
        'contact_phone': _website_request_value(website_request, 'contact_phone'),
        'contact_whatsapp': _website_request_value(website_request, 'contact_whatsapp'),
        'existing_website_url': _website_request_value(website_request, 'existing_website_url'),
        'current_domain': _website_request_value(website_request, 'current_domain'),
        'needs_domain_help': _website_request_value(website_request, 'needs_domain_help'),
        'business_address': _website_request_value(website_request, 'business_address'),
        'service_area': _website_request_value(website_request, 'service_area'),
        'main_language': _website_request_value(website_request, 'main_language'),
        'extra_languages': _website_request_value(website_request, 'extra_languages'),
        'main_services': _website_request_value(website_request, 'main_services'),
        'business_description': _website_request_value(website_request, 'business_description'),
        'preferred_colors': _website_request_value(website_request, 'preferred_colors'),
        'style_notes': _website_request_value(website_request, 'style_notes'),
        'social_links': _website_request_value(website_request, 'social_links'),
        'opening_hours': _website_request_value(website_request, 'opening_hours'),
        'special_requests': _website_request_value(website_request, 'special_requests'),
        'source_code': _website_request_value(website_request, 'source_code'),
        'normal_price': _website_request_value(website_request, 'normal_price'),
        'offer_price': _website_request_value(website_request, 'offer_price'),
        'status': _website_request_value(website_request, 'status'),
        'files': _serialize_website_request_files(website_request),
    }

    return payload


def build_site_handoff_payload(site, website_request=None):
    payload = {
        'schema_version': 1,
        'generated_at': timezone.now().isoformat(),
        'source': {
            'system': 'django_getonlinefast',
            'site_id': site.id,
            'public_id': str(site.public_id),
        },
        'business': {
            'business_name': site.business_name,
            'service_type': site.service_type,
            'city': site.city,
        },
        'design': {
            'template_slug': site.template_slug,
            'color_palette': site.color_palette,
        },
        'content': _serialize_site_content(site),
        'wordpress_target': {
            'site_url': '',
            'admin_url': '',
            'user_reference': '',
        },
        'notes': (
            'Staff/manual handoff payload only. This payload is a structured export '
            'reference and does not mutate WordPress.'
        ),
    }

    website_request_payload = _serialize_website_request(website_request)
    if website_request_payload is not None:
        payload['website_request'] = website_request_payload

    return payload
