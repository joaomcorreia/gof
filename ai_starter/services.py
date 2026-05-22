from copy import deepcopy

from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import SiteContent, Template


TEMPLATE_LAYOUTS = {
    'local_service': {
        'name': 'Local Service',
        'layout': [
            {'key': 'hero', 'type': 'hero_lr'},
            {'key': 'services', 'type': 'list'},
            {'key': 'contact', 'type': 'contact_form'},
            {'key': 'cta', 'type': 'cta'},
        ],
    },
    'growth_offer': {
        'name': 'Growth Offer',
        'layout': [
            {'key': 'hero', 'type': 'hero_lr'},
            {'key': 'benefits', 'type': 'benefits'},
            {'key': 'services', 'type': 'list'},
            {'key': 'cta', 'type': 'cta'},
            {'key': 'contact', 'type': 'contact_form'},
        ],
    },
    'starter_onepage': {
        'name': 'Starter Onepage',
        'layout': [
            {'key': 'hero', 'type': 'hero_simple'},
            {'key': 'contact', 'type': 'contact_form'},
            {'key': 'cta', 'type': 'cta'},
        ],
    },
}

TEMPLATE_DISPLAY_LABELS = {
    'local_service': _('Local Service'),
    'growth_offer': _('Growth Offer'),
    'starter_onepage': _('Starter Page'),
}

PALETTE_DISPLAY_LABELS = {
    'orange_black': _('Orange / Black'),
    'blue_dark': _('Blue / Dark'),
    'green_neutral': _('Green / Neutral'),
    'red_charcoal': _('Red / Charcoal'),
}


SECTION_SCHEMAS = {
    'hero_lr': {
        'label': _('Hero'),
        'template': 'ai_starter/sections/hero_lr.html',
        'fields': [
            {'key': 'kicker', 'label': _('Eyebrow')},
            {'key': 'title', 'label': _('Title')},
            {'key': 'description', 'label': _('Description')},
            {'key': 'cta_text', 'label': _('CTA text')},
            {'key': 'highlight_title', 'label': _('Highlight title')},
            {'key': 'highlight_text', 'label': _('Highlight text')},
        ],
    },
    'hero_simple': {
        'label': _('Simple hero'),
        'template': 'ai_starter/sections/hero_simple.html',
        'fields': [
            {'key': 'kicker', 'label': _('Eyebrow')},
            {'key': 'title', 'label': _('Title')},
            {'key': 'description', 'label': _('Description')},
            {'key': 'cta_text', 'label': _('CTA text')},
        ],
    },
    'list': {
        'label': _('List section'),
        'template': 'ai_starter/sections/list.html',
        'fields': [
            {'key': 'title', 'label': _('Section title')},
            {'key': 'intro', 'label': _('Intro text')},
            {'key': 'item_1', 'label': _('Item 1')},
            {'key': 'item_2', 'label': _('Item 2')},
            {'key': 'item_3', 'label': _('Item 3')},
        ],
    },
    'benefits': {
        'label': _('Benefits section'),
        'template': 'ai_starter/sections/benefits.html',
        'fields': [
            {'key': 'title', 'label': _('Section title')},
            {'key': 'intro', 'label': _('Intro text')},
            {'key': 'card_1_title', 'label': _('Card 1 title')},
            {'key': 'card_1_text', 'label': _('Card 1 text')},
            {'key': 'card_2_title', 'label': _('Card 2 title')},
            {'key': 'card_2_text', 'label': _('Card 2 text')},
            {'key': 'card_3_title', 'label': _('Card 3 title')},
            {'key': 'card_3_text', 'label': _('Card 3 text')},
        ],
    },
    'contact_form': {
        'label': _('Contact section'),
        'template': 'ai_starter/sections/contact_form.html',
        'fields': [
            {'key': 'title', 'label': _('Section title')},
            {'key': 'description', 'label': _('Description')},
            {'key': 'primary_contact', 'label': _('Primary contact')},
            {'key': 'secondary_contact', 'label': _('Secondary contact')},
            {'key': 'cta_text', 'label': _('CTA text')},
        ],
    },
    'cta': {
        'label': _('CTA section'),
        'template': 'ai_starter/sections/cta.html',
        'fields': [
            {'key': 'title', 'label': _('Title')},
            {'key': 'description', 'label': _('Description')},
            {'key': 'cta_text', 'label': _('CTA text')},
        ],
    },
}


def ensure_default_templates():
    for slug, config in TEMPLATE_LAYOUTS.items():
        Template.objects.update_or_create(
            slug=slug,
            defaults={
                'name': config['name'],
                'layout_json': deepcopy(config['layout']),
            },
        )


def available_template_options():
    return [
        {
            'slug': slug,
            'label': TEMPLATE_DISPLAY_LABELS.get(slug, config['name']),
        }
        for slug, config in TEMPLATE_LAYOUTS.items()
    ]


def available_palette_options():
    return [
        {
            'slug': slug,
            'label': label,
        }
        for slug, label in PALETTE_DISPLAY_LABELS.items()
    ]


def get_template_definition(slug):
    template = Template.objects.filter(slug=slug).first()
    if template:
        return {
            'slug': template.slug,
            'name': template.name,
            'layout': deepcopy(template.layout_json),
        }
    config = TEMPLATE_LAYOUTS.get(slug) or TEMPLATE_LAYOUTS['local_service']
    return {
        'slug': slug,
        'name': config['name'],
        'layout': deepcopy(config['layout']),
    }


def build_suggestions(*, business_name, service_type, city, template_slug='local_service'):
    business_name = business_name.strip()
    service_type = service_type.strip()
    city = city.strip()
    service_type_lower = service_type.lower()
    template_slug = template_slug or 'local_service'

    hero = {
        'kicker': city,
        'title': f'{business_name} for {service_type_lower} in {city}',
        'description': (
            f'Clear website content for {service_type_lower} customers in {city}, '
            f'with an easy way to contact {business_name}.'
        ),
        'cta_text': _('Request a quote'),
        'highlight_title': _('Built for your business'),
        'highlight_text': (
            f'{business_name} uses a practical layout for {service_type_lower} services, '
            f'local visibility, and customer enquiries.'
        ),
    }

    services = {
        'title': _('What customers can see right away'),
        'intro': (
            f'This template explains {service_type_lower} services clearly for visitors in {city}.'
        ),
        'item_1': _('Clear services and pricing direction'),
        'item_2': _('Local visibility structure'),
        'item_3': _('Simple contact path for new enquiries'),
    }

    contact = {
        'title': _('Ready to hear from customers'),
        'description': (
            f'Use a contact form, direct contact details, or a clear CTA so {business_name} stays easy to reach.'
        ),
        'primary_contact': _('Contact form ready'),
        'secondary_contact': _('Email or phone can be added anytime'),
        'cta_text': _('Contact us'),
    }

    cta = {
        'title': f'{business_name} in {city}',
        'description': _('A simple website foundation that can be edited, expanded, and improved over time.'),
        'cta_text': _('Start with this setup'),
    }

    benefits = {
        'title': _('Built to support growth'),
        'intro': _('A stronger page structure for businesses that want a clearer offer and more response from visitors.'),
        'card_1_title': _('Clear offer'),
        'card_1_text': _('Explain what you do quickly so visitors know why they should contact you.'),
        'card_2_title': _('More visibility'),
        'card_2_text': _('Use a layout that supports search, promotion, and stronger first impressions.'),
        'card_3_title': _('Easy contact'),
        'card_3_text': _('Keep calls, messages, and quote requests simple for new visitors.'),
    }

    suggestions = {
        'hero': hero,
        'services': services,
        'contact': contact,
        'cta': cta,
        'benefits': benefits,
    }

    if template_slug == 'growth_offer':
        suggestions['hero']['title'] = f'{business_name} helps {city} customers choose {service_type_lower} with confidence'
        suggestions['hero']['description'] = _(
            'Use a stronger sales-focused layout to explain your offer, show value, and guide visitors toward action.'
        )
        suggestions['hero']['highlight_title'] = _('Built to attract more enquiries')
        suggestions['hero']['highlight_text'] = _(
            'A stronger offer layout for businesses that want clearer visibility and promotion.'
        )
    elif template_slug == 'starter_onepage':
        suggestions['hero']['title'] = f'{business_name} in {city}'
        suggestions['hero']['description'] = _(
            'A simple one-page website start for businesses that want to launch quickly with clear contact details.'
        )

    return suggestions


def save_site_content(site, language, content_map):
    for section_key, fields in content_map.items():
        for field_key, value in fields.items():
            SiteContent.objects.update_or_create(
                site=site,
                section_key=section_key,
                field_key=field_key,
                language=language,
                defaults={'value': value},
            )


def get_site_content_map(site, language):
    requested = list(site.contents.filter(language=language))
    if not requested:
        requested = list(site.contents.all())

    content_map = {}
    for item in requested:
        content_map.setdefault(item.section_key, {})[item.field_key] = item.value
    return content_map


def ensure_language_content(site, language):
    if site.contents.filter(language=language).exists():
        return

    fallback_map = get_site_content_map(site, language)
    if fallback_map:
        save_site_content(site, language, fallback_map)


def build_editor_sections(site, language):
    template_definition = get_template_definition(site.template_slug)
    content_map = get_site_content_map(site, language)
    sections = []

    for section in template_definition['layout']:
        schema = SECTION_SCHEMAS[section['type']]
        section_values = content_map.get(section['key'], {})
        fields = []
        for field in schema['fields']:
            content = SiteContent.objects.filter(
                site=site,
                section_key=section['key'],
                field_key=field['key'],
                language=language,
            ).first() or SiteContent.objects.filter(
                site=site,
                section_key=section['key'],
                field_key=field['key'],
            ).first()
            fields.append(
                {
                    'id': content.id if content else None,
                    'key': field['key'],
                    'label': field['label'],
                    'value': section_values.get(field['key'], ''),
                }
            )
        sections.append(
            {
                'key': section['key'],
                'type': section['type'],
                'label': schema['label'],
                'fields': fields,
            }
        )

    return sections


def build_render_sections(site, language):
    template_definition = get_template_definition(site.template_slug)
    content_map = get_site_content_map(site, language)
    render_sections = []

    for section in template_definition['layout']:
        schema = SECTION_SCHEMAS[section['type']]
        render_sections.append(
            {
                'key': section['key'],
                'type': section['type'],
                'template_name': schema['template'],
                'values': content_map.get(section['key'], {}),
            }
        )

    return render_sections


def site_slug(site):
    return slugify(site.business_name) or 'your-business'
