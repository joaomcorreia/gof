from collections.abc import Mapping


SUPPORTED_PLATFORM_MODES = {
    'starter_preview',
    'ai_polish',
    'staff_reply',
    'handoff_brief',
    'social_posts_future',
    'public_assistant_future',
}


def _clean_string(value):
    if value is None:
        return ''
    return str(value).strip()


def _clean_list(values):
    cleaned = []
    for value in values or []:
        text = _clean_string(value)
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _first_value(*values):
    for value in values:
        text = _clean_string(value)
        if text:
            return text
    return ''


def _as_mapping(value):
    if isinstance(value, Mapping):
        return value
    if hasattr(value, 'items'):
        try:
            return dict(value.items())
        except Exception:
            return {}
    return {}


def _extract_content_map(content_source):
    if isinstance(content_source, Mapping):
        return {str(key): _clean_string(value) for key, value in content_source.items()}

    content_map = {}
    for row in content_source or []:
        if isinstance(row, Mapping):
            section_key = _clean_string(row.get('section_key'))
            field_key = _clean_string(row.get('field_key'))
            value = _clean_string(row.get('value'))
        else:
            section_key = _clean_string(getattr(row, 'section_key', ''))
            field_key = _clean_string(getattr(row, 'field_key', ''))
            value = _clean_string(getattr(row, 'value', ''))

        if not section_key or not field_key:
            continue

        content_map[f'{section_key}.{field_key}'] = value

    return content_map


def _content_value(content_map, *keys):
    for key in keys:
        value = _clean_string(content_map.get(key, ''))
        if value:
            return value
    return ''


def _split_services(value):
    if isinstance(value, (list, tuple, set)):
        return _clean_list(value)
    text = _clean_string(value)
    if not text:
        return []

    parts = [
        item.strip(' -\u2022\t')
        for raw_line in text.replace('\r', '\n').split('\n')
        for item in raw_line.split(',')
    ]
    return _clean_list(parts)


def _extract_site_mapping(site):
    if not site:
        return {}
    return {
        'business_name': getattr(site, 'business_name', ''),
        'business_type': getattr(site, 'service_type', ''),
        'city': getattr(site, 'city', ''),
        'template_slug': getattr(site, 'template_slug', ''),
        'color_palette': getattr(site, 'color_palette', ''),
    }


def _extract_request_mapping(request_obj):
    if not request_obj:
        return {}
    return {
        'business_name': getattr(request_obj, 'business_name', ''),
        'business_type': getattr(request_obj, 'business_type', ''),
        'service_area': getattr(request_obj, 'service_area', ''),
        'contact_name': getattr(request_obj, 'contact_name', ''),
        'email': getattr(request_obj, 'contact_email', ''),
        'phone': getattr(request_obj, 'contact_phone', '') or getattr(request_obj, 'contact_whatsapp', ''),
        'address': getattr(request_obj, 'business_address', ''),
        'language': getattr(request_obj, 'main_language', ''),
        'selected_services': _split_services(getattr(request_obj, 'main_services', '')),
        'business_description': getattr(request_obj, 'business_description', ''),
        'style_notes': getattr(request_obj, 'style_notes', ''),
    }


def _extract_handoff_mapping(handoff):
    if not handoff:
        return {}, {}, {}

    payload = _as_mapping(getattr(handoff, 'handoff_payload', None))
    website_request = _as_mapping(payload.get('website_request'))
    business = _as_mapping(payload.get('business'))
    design = _as_mapping(payload.get('design'))

    handoff_mapping = {
        'business_name': business.get('business_name'),
        'business_type': business.get('service_type') or business.get('business_type'),
        'city': business.get('city'),
        'template_slug': design.get('template_slug'),
        'color_palette': design.get('color_palette'),
        'email': website_request.get('contact_email'),
        'contact_name': website_request.get('contact_name'),
        'phone': website_request.get('contact_phone') or website_request.get('contact_whatsapp'),
        'address': website_request.get('business_address'),
        'service_area': website_request.get('service_area'),
        'language': website_request.get('main_language'),
        'selected_services': _split_services(website_request.get('main_services')),
        'business_description': website_request.get('business_description'),
        'style_notes': website_request.get('style_notes'),
    }
    return handoff_mapping, payload, website_request


def build_business_context(
    source=None,
    *,
    site=None,
    site_content=None,
    handoff=None,
    website_request=None,
    content_dict=None,
    language='',
    platform_mode='starter_preview',
    **overrides,
):
    source_mapping = _as_mapping(source)
    source_business = _as_mapping(source_mapping.get('business'))
    source_services = _as_mapping(source_mapping.get('services'))
    source_contact = _as_mapping(source_mapping.get('contact'))
    source_content = _as_mapping(source_mapping.get('content'))
    source_meta = _as_mapping(source_mapping.get('meta'))
    site_mapping = _extract_site_mapping(site)
    request_mapping = _extract_request_mapping(website_request)
    handoff_mapping, handoff_payload, handoff_request_mapping = _extract_handoff_mapping(handoff)

    content_map = _extract_content_map(site_content)
    content_map.update(_extract_content_map(content_dict))

    direct_selected_services = (
        overrides.get('selected_services')
        or source_services.get('selected_services')
        or source_mapping.get('selected_services')
        or request_mapping.get('selected_services')
        or handoff_mapping.get('selected_services')
        or handoff_request_mapping.get('main_services')
    )
    direct_service_descriptions = (
        overrides.get('service_descriptions')
        or source_services.get('service_descriptions')
        or source_mapping.get('service_descriptions')
        or []
    )

    normalized_platform_mode = platform_mode if platform_mode in SUPPORTED_PLATFORM_MODES else 'starter_preview'
    resolved_language = _first_value(
        language,
        overrides.get('language'),
        source_meta.get('language'),
        source_mapping.get('language'),
        request_mapping.get('language'),
        handoff_mapping.get('language'),
    )

    business = {
        'business_name': _first_value(
            overrides.get('business_name'),
            source_business.get('business_name'),
            source_mapping.get('business_name'),
            site_mapping.get('business_name'),
            request_mapping.get('business_name'),
            handoff_mapping.get('business_name'),
        ),
        'business_type': _first_value(
            overrides.get('business_type'),
            source_business.get('business_type'),
            source_business.get('service_type'),
            source_mapping.get('business_type'),
            source_mapping.get('service_type'),
            site_mapping.get('business_type'),
            request_mapping.get('business_type'),
            handoff_mapping.get('business_type'),
        ),
        'city': _first_value(
            overrides.get('city'),
            source_business.get('city'),
            source_mapping.get('city'),
            site_mapping.get('city'),
            handoff_mapping.get('city'),
        ),
        'service_area': _first_value(
            overrides.get('service_area'),
            source_business.get('service_area'),
            source_mapping.get('service_area'),
            request_mapping.get('service_area'),
            handoff_mapping.get('service_area'),
        ),
        'business_description': _first_value(
            overrides.get('business_description'),
            source_business.get('business_description'),
            source_mapping.get('business_description'),
            request_mapping.get('business_description'),
            handoff_mapping.get('business_description'),
        ),
        'website_goal': _first_value(
            overrides.get('website_goal'),
            source_business.get('website_goal'),
            source_mapping.get('website_goal'),
            source_mapping.get('goal'),
        ),
        'style_notes': _first_value(
            overrides.get('style_notes'),
            source_business.get('style_notes'),
            source_mapping.get('style_notes'),
            request_mapping.get('style_notes'),
            handoff_mapping.get('style_notes'),
        ),
    }

    contact = {
        'contact_name': _first_value(
            overrides.get('contact_name'),
            source_contact.get('contact_name'),
            source_mapping.get('contact_name'),
            request_mapping.get('contact_name'),
            handoff_mapping.get('contact_name'),
        ),
        'phone': _first_value(
            overrides.get('phone'),
            source_contact.get('phone'),
            source_mapping.get('phone'),
            source_mapping.get('contact_phone'),
            request_mapping.get('phone'),
            handoff_mapping.get('phone'),
        ),
        'email': _first_value(
            overrides.get('email'),
            source_contact.get('email'),
            source_mapping.get('email'),
            source_mapping.get('contact_email'),
            request_mapping.get('email'),
            handoff_mapping.get('email'),
        ),
        'address': _first_value(
            overrides.get('address'),
            overrides.get('location'),
            source_contact.get('address'),
            source_contact.get('location'),
            source_mapping.get('address'),
            source_mapping.get('location'),
            request_mapping.get('address'),
            handoff_mapping.get('address'),
        ),
        'location': _first_value(
            overrides.get('location'),
            source_contact.get('location'),
            source_contact.get('address'),
            source_mapping.get('location'),
            source_mapping.get('address'),
            request_mapping.get('address'),
            handoff_mapping.get('address'),
        ),
    }

    services = {
        'selected_services': _clean_list(_split_services(direct_selected_services)),
        'service_descriptions': _clean_list(direct_service_descriptions),
    }

    content = {
        'hero_title': _first_value(
            overrides.get('hero_title'),
            source_content.get('hero_title'),
            source_mapping.get('hero_title'),
            _content_value(content_map, 'hero.title'),
        ),
        'hero_text': _first_value(
            overrides.get('hero_text'),
            source_content.get('hero_text'),
            source_mapping.get('hero_text'),
            _content_value(content_map, 'hero.description'),
        ),
        'intro_heading': _first_value(
            overrides.get('intro_heading'),
            source_content.get('intro_heading'),
            source_mapping.get('intro_heading'),
            _content_value(content_map, 'about.title', 'services.title'),
        ),
        'intro_paragraph': _first_value(
            overrides.get('intro_paragraph'),
            source_content.get('intro_paragraph'),
            source_mapping.get('intro_paragraph'),
            _content_value(content_map, 'about.description', 'services.intro'),
        ),
    }

    meta = {
        'language': resolved_language,
        'platform_mode': normalized_platform_mode,
        'template_slug': _first_value(
            overrides.get('template_slug'),
            source_meta.get('template_slug'),
            source_mapping.get('template_slug'),
            site_mapping.get('template_slug'),
            handoff_mapping.get('template_slug'),
        ),
        'color_palette': _first_value(
            overrides.get('color_palette'),
            source_meta.get('color_palette'),
            source_mapping.get('color_palette'),
            site_mapping.get('color_palette'),
            handoff_mapping.get('color_palette'),
        ),
        'source': _first_value(
            overrides.get('source'),
            source_meta.get('source'),
            source_mapping.get('source'),
            handoff_payload.get('source', {}).get('system') if isinstance(handoff_payload.get('source'), Mapping) else '',
        ),
    }

    return {
        'business': business,
        'services': services,
        'contact': contact,
        'content': content,
        'meta': meta,
    }


def format_business_context_for_prompt(context):
    normalized = context if isinstance(context, Mapping) else {}
    business = _as_mapping(normalized.get('business'))
    services = _as_mapping(normalized.get('services'))
    contact = _as_mapping(normalized.get('contact'))
    meta = _as_mapping(normalized.get('meta'))

    lines = []

    field_map = (
        ('Business name', business.get('business_name')),
        ('Business type', business.get('business_type')),
        ('City', business.get('city')),
        ('Service area', business.get('service_area')),
        ('Selected services', ', '.join(_clean_list(services.get('selected_services') or []))),
        ('Service descriptions', ' | '.join(_clean_list(services.get('service_descriptions') or []))),
        ('Business description', business.get('business_description')),
        ('Website goal', business.get('website_goal')),
        ('Style notes', business.get('style_notes')),
        ('Contact name', contact.get('contact_name')),
        ('Phone', contact.get('phone')),
        ('Email', contact.get('email')),
        ('Address', contact.get('address')),
        ('Language', meta.get('language')),
        ('Platform mode', meta.get('platform_mode')),
    )

    for label, value in field_map:
        text = _clean_string(value)
        if text:
            lines.append(f'{label}: {text}')

    return '\n'.join(lines) or 'No business context provided.'
