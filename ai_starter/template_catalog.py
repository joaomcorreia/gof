from copy import deepcopy

from django.utils.translation import gettext_lazy as _


STARTER_TEMPLATE_REGISTRY = [
    {
        'key': 'service_pro',
        'label': _('Service Pro'),
        'template_slug': 'classic_service',
        'note': _('Older one-page local service template for practical and professional businesses.'),
        'business_keywords': [
            'auto repair', 'garage', 'mechanic', 'car repair', 'vehicle repair', 'workshop',
            'taxi', 'transport', 'airport transfer', 'handyman', 'cleaning', 'construction',
            'builder', 'contractor', 'electrician', 'plumber', 'painter',
        ],
        'preferred_image_category': 'garage',
    },
    {
        'key': 'friendly_care',
        'label': _('Friendly Care'),
        'template_slug': 'gof-canva-layout-test-v1',
        'note': _('Current Codex starter preview template kept for kids, family, care, tutoring, and softer service businesses.'),
        'business_keywords': [
            'babysitter', 'baby sitter', 'child care', 'childcare', 'kids', 'children',
            'daycare', 'day care', 'family support', 'tutoring', 'tutor', 'lessons',
            'caregiver', 'care', 'nanny',
        ],
        'preferred_image_category': 'generic_service',
    },
    {
        'key': 'visual_showcase',
        'label': _('Visual Showcase'),
        'template_slug': 'visual_hero',
        'note': _('Image-led starter template for visual local businesses.'),
        'business_keywords': [
            'beauty', 'wellness', 'salon', 'spa', 'hair', 'lashes', 'makeup', 'barber',
            'massage', 'skincare',
        ],
        'preferred_image_category': 'beauty',
    },
    {
        'key': 'simple_landing',
        'label': _('Simple Landing'),
        'template_slug': 'classic_service',
        'note': _('Placeholder registry key using the older one-page template until a dedicated landing template is added.'),
        'business_keywords': [],
        'preferred_image_category': 'generic_service',
    },
]


TEMPLATE_REGISTRY = [
    {
        'slug': 'classic_service',
        'label': _('Classic Service Website'),
        'category': _('Professional & Practical'),
        'style': _('Clean / Familiar'),
        'layout_label': _('Boxed sections'),
        'description': _(
            'Simple local service website with clear hero, services, contact buttons, and quote/contact flow.'
        ),
        'best_for': _('Garages, plumbers, electricians, construction, repair services.'),
        'layout_note': _('Boxed layout'),
        'thumbnail_type': 'classic_service',
        'preview_css_class': 'template-classic-service',
        'layout_family': 'boxed',
        'layout_class': 'layout-boxed',
        'section_layout': {
            'hero': 'boxed',
            'services': 'boxed',
            'contact': 'boxed',
            'cta': 'boxed',
        },
        'layout': [
            {'key': 'hero', 'type': 'hero_lr'},
            {'key': 'services', 'type': 'list'},
            {'key': 'contact', 'type': 'contact_form'},
            {'key': 'cta', 'type': 'cta'},
        ],
        'legacy_aliases': ['local_service', 'starter_onepage'],
    },
    {
        'slug': 'visual_hero',
        'label': _('Visual Hero Website'),
        'category': _('Visual & Local'),
        'style': _('Bold / Image-led'),
        'layout_label': _('Full-width visual sections'),
        'description': _(
            'Large image-led homepage with strong first impression, call-to-action, and stacked content sections.'
        ),
        'best_for': _('Restaurants, beauty, construction, transport, local brands.'),
        'layout_note': _('Full-width visual layout'),
        'thumbnail_type': 'visual_hero',
        'preview_css_class': 'template-visual-hero',
        'layout_family': 'full_width',
        'layout_class': 'layout-full-width',
        'section_layout': {
            'hero': 'full_width',
            'benefits': 'boxed',
            'services': 'boxed',
            'cta': 'full_width',
            'contact': 'boxed',
        },
        'layout': [
            {'key': 'hero', 'type': 'hero_lr'},
            {'key': 'benefits', 'type': 'benefits'},
            {'key': 'services', 'type': 'list'},
            {'key': 'cta', 'type': 'cta'},
            {'key': 'contact', 'type': 'contact_form'},
        ],
        'legacy_aliases': ['growth_offer'],
    },
    {
        'slug': 'card_grid',
        'label': _('Catalog / Multi-Service Website'),
        'category': _('Catalog & Multi-Service'),
        'style': _('Structured / Card-based'),
        'layout_label': _('Mixed sections'),
        'description': _(
            'Card-based layout for businesses with multiple services, products, or categories.'
        ),
        'best_for': _('Shops, drogists, print shops, catalogs, mixed-service businesses.'),
        'layout_note': _('Mixed layout'),
        'thumbnail_type': 'card_grid',
        'preview_css_class': 'template-card-grid',
        'layout_family': 'mixed',
        'layout_class': 'layout-mixed',
        'section_layout': {
            'hero': 'boxed',
            'services': 'boxed',
            'benefits': 'boxed',
            'cta': 'full_width',
            'contact': 'boxed',
            'faq': 'boxed',
        },
        'layout': [
            {'key': 'hero', 'type': 'hero_simple'},
            {'key': 'services', 'type': 'list'},
            {'key': 'benefits', 'type': 'benefits'},
            {'key': 'cta', 'type': 'cta'},
            {'key': 'contact', 'type': 'contact_form'},
        ],
        'legacy_aliases': [],
    },
    {
        'slug': 'gof-canva-layout-test-v1',
        'label': _('Warm Modern Starter'),
        'category': _('Professional & Practical'),
        'style': _('Editorial / Sharp'),
        'layout_label': _('Full-width rows'),
        'description': _(
            'A sharper full-width layout for businesses that want a serious, structured website with strong service sections, portfolio examples, trust points, and clear contact paths.'
        ),
        'best_for': _(
            'Consultants, B2B services, local professional services, trades that want a more serious look, security, technical services, agencies, repair/services with portfolio.'
        ),
        'layout_note': _('Full-width rows'),
        'thumbnail_type': 'gof_canva_layout_test_v1',
        'preview_css_class': 'template-gof-canva-layout-test-v1',
        'layout_family': 'full_width',
        'layout_class': 'layout-full-width',
        'section_layout': {
            'hero': 'boxed',
            'about': 'boxed',
            'services': 'boxed',
            'portfolio': 'boxed',
            'process': 'boxed',
            'trust': 'boxed',
            'contact': 'boxed',
            'final_cta': 'boxed',
            'footer': 'boxed',
        },
        'layout': [
            {'key': 'hero', 'type': 'hero_lr'},
            {'key': 'about', 'type': 'story_split'},
            {'key': 'services', 'type': 'offer_grid'},
            {'key': 'portfolio', 'type': 'showcase_grid'},
            {'key': 'process', 'type': 'steps'},
            {'key': 'trust', 'type': 'benefits'},
            {'key': 'contact', 'type': 'contact_details'},
            {'key': 'final_cta', 'type': 'cta'},
            {'key': 'footer', 'type': 'footer_columns'},
        ],
        'legacy_aliases': [],
    },
]


def _template_lookup():
    lookup = {}
    for template in TEMPLATE_REGISTRY:
        lookup[template['slug']] = template
        for alias in template.get('legacy_aliases', []):
            lookup[alias] = template
    return lookup


def _starter_template_lookup():
    return {entry['key']: entry for entry in STARTER_TEMPLATE_REGISTRY}


def default_template_slug():
    return TEMPLATE_REGISTRY[0]['slug']


def available_template_cards():
    return [deepcopy(template) for template in TEMPLATE_REGISTRY]


def available_starter_template_registry():
    return [deepcopy(entry) for entry in STARTER_TEMPLATE_REGISTRY]


def default_starter_template_key():
    return STARTER_TEMPLATE_REGISTRY[0]['key']


def normalize_starter_template_key(key):
    normalized = str(key or '').strip()
    if normalized in _starter_template_lookup():
        return normalized
    return default_starter_template_key()


def get_starter_template_entry(key):
    normalized = normalize_starter_template_key(key)
    return deepcopy(_starter_template_lookup()[normalized])


def template_slug_for_starter_template_key(key):
    entry = get_starter_template_entry(key)
    return normalize_template_slug(entry['template_slug'])


def infer_starter_template_key(business_type, *, fallback=None):
    normalized_business_type = str(business_type or '').strip().lower()
    for entry in STARTER_TEMPLATE_REGISTRY:
        if any(keyword in normalized_business_type for keyword in entry.get('business_keywords', [])):
            return entry['key']
    return normalize_starter_template_key(fallback or default_starter_template_key())


def infer_starter_template_slug(business_type, *, fallback=None):
    return template_slug_for_starter_template_key(
        infer_starter_template_key(business_type, fallback=fallback)
    )


def normalize_template_slug(slug):
    slug = (slug or '').strip()
    if not slug:
        return default_template_slug()
    template = _template_lookup().get(slug)
    if template:
        return template['slug']
    return default_template_slug()


def is_valid_template_slug(slug):
    return normalize_template_slug(slug) in {item['slug'] for item in TEMPLATE_REGISTRY}


def get_template_card(slug):
    normalized_slug = normalize_template_slug(slug)
    return deepcopy(_template_lookup()[normalized_slug])


def get_template_layout(slug):
    return deepcopy(get_template_card(slug)['layout'])


def get_template_preview_class(slug):
    return get_template_card(slug)['preview_css_class']


def get_template_layout_class(slug):
    return get_template_card(slug)['layout_class']


def get_template_layout_family(slug):
    return get_template_card(slug)['layout_family']


def get_template_section_layout(slug):
    return deepcopy(get_template_card(slug)['section_layout'])
