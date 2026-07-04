import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import Http404
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .forms import StarterOnboardingForm, WebsiteRequestForm
from .models import Site, SiteContent, SiteHandoff, WebsiteRequest, WebsiteRequestFile
from core.template_catalog import template_lookup
from .services_ai import clean_assistant_output, draft_customer_reply, infer_recommended_website_setup
from .services import (
    available_palette_options,
    available_template_options,
    build_editor_sections,
    build_render_sections,
    build_suggestions,
    ensure_default_site_images,
    ensure_language_content,
    ensure_default_templates,
    get_onboarding_business_profile,
    get_onboarding_intro_variants,
    get_onboarding_service_suggestions,
    resolve_business_profile,
    next_suggestion_variant,
    save_site_content,
    site_slug,
)
from .image_catalog import get_alternate_image_for_business_type, get_default_image_for_business_type
from .project_assets import get_first_project_asset, normalize_project_slug
from .template_catalog import (
    available_template_cards,
    default_template_slug,
    get_template_card,
    get_template_layout_class,
    get_template_preview_class,
    is_valid_template_slug,
    normalize_template_slug,
)

MEETING_OFFER_SOURCE = 'GEMEENTE50'
MEETING_NORMAL_PRICE = 325
MEETING_OFFER_PRICE = 275
ONBOARDING_TOTAL_STEPS = 8
STARTER_WIZARD_TOTAL_STEPS = 6
STARTER_WIZARD_SESSION_KEY = 'starter_wizard_state'
logger = logging.getLogger(__name__)
ONBOARDING_FIELD_FALLBACKS = {
    'hero_title': 'Professional website preview for your business',
    'hero_description': 'A clear starting website with your services, contact details, and next steps ready to review.',
    'hero_cta': 'Request information',
    'intro_title': 'A simple introduction section',
    'intro_text': 'Use this section to explain what your business does, who you help, and why customers should contact you.',
}
ONBOARDING_INTRO_FALLBACK_TITLES = {
    'A simple introduction section',
    'A clearer introduction',
    'A stronger first explanation',
}
ONBOARDING_INTRO_FALLBACK_TEXTS = {
    'Use this section to explain what your business does, who you help, and why customers should contact you.',
    'Help visitors understand your services quickly with a short introduction that can be refined after activation.',
    'Give customers a clearer idea of what you offer, how you work, and what they should do next.',
}


def _raise_public_preview_unavailable(request):
    if request.user.is_authenticated and request.user.is_staff:
        return None
    raise Http404('Not found.')


def _is_staff_preview_user(request):
    return bool(request.user.is_authenticated and request.user.is_staff)


def _require_staff_user(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseForbidden('Staff access required.')
    return None


def _require_staff_or_debug(request):
    if settings.DEBUG:
        return None
    return _require_staff_user(request)


def _site_handoff_admin_url(handoff):
    if handoff is None:
        return ''
    return reverse('admin:ai_starter_sitehandoff_change', args=[handoff.pk])


def _handoff_content_row_count(handoff):
    payload = handoff.handoff_payload if isinstance(handoff.handoff_payload, dict) else {}
    content_rows = payload.get('content')
    return len(content_rows) if isinstance(content_rows, list) else None


def _handoff_request_summary(handoff):
    request_obj = handoff.website_request
    request_payload = {}
    if isinstance(handoff.handoff_payload, dict):
        request_payload = handoff.handoff_payload.get('website_request') or {}

    if not request_obj and not request_payload:
        return {
            'has_request': False,
            'contact_name': '',
            'contact_email': '',
            'contact_phone': '',
            'main_language': '',
            'domain_line': '',
            'status_source_line': '',
        }

    def pick(name):
        value = getattr(request_obj, name, None) if request_obj is not None else None
        if value in (None, ''):
            value = request_payload.get(name, '')
        return str(value).strip() if value not in (None, '') else ''

    contact_phone = pick('contact_phone') or pick('contact_whatsapp')
    domain_bits = []
    current_domain = pick('current_domain')
    if current_domain:
        domain_bits.append(current_domain)
    if request_obj is not None:
        needs_domain_help = getattr(request_obj, 'needs_domain_help', False)
    else:
        needs_domain_help = bool(request_payload.get('needs_domain_help'))
    if needs_domain_help:
        domain_bits.append('Needs domain help')

    status_source_bits = []
    status = pick('status')
    if status:
        status_source_bits.append(status)
    source_code = pick('source_code')
    if source_code:
        status_source_bits.append(source_code)

    return {
        'has_request': True,
        'contact_name': pick('contact_name'),
        'contact_email': pick('contact_email'),
        'contact_phone': contact_phone,
        'main_language': pick('main_language'),
        'domain_line': ' | '.join(domain_bits),
        'status_source_line': ' | '.join(status_source_bits),
    }


def _assistant_tone_options():
    return [
        {'value': 'friendly_professional', 'label': 'Friendly professional'},
        {'value': 'short_direct', 'label': 'Short and direct'},
        {'value': 'warm_sales', 'label': 'Warm sales reply'},
        {'value': 'support_helpful', 'label': 'Support/helpful'},
    ]


def _assistant_language_options():
    return ['Portuguese', 'English', 'Dutch', 'French']


def _assistant_demo_messages():
    return [
        {
            'title': 'Garage / workshop',
            'body': 'Tenho uma oficina e preciso de um website, mas não sei bem o que preciso.',
        },
        {
            'title': 'Printing / quote request',
            'body': 'Tenho uma gráfica e queria receber pedidos de orçamento pelo site.',
        },
        {
            'title': 'Shop / catalog later sales',
            'body': 'Tenho uma loja pequena e queria mostrar produtos online, talvez vender mais tarde.',
        },
        {
            'title': 'AI reply assistant',
            'body': 'Queria saber se conseguem criar um assistente AI para responder a clientes.',
        },
    ]


def _template_wireframe_layouts():
    return [
        {
            'label': 'Boxed service layout',
            'layout_family': 'boxed',
            'slug_hint': 'classic_service / layout-boxed',
            'use_cases': 'Garages, plumbers, electricians, construction, repair services',
            'sections': [
                'boxed hero',
                'services icon cards',
                'about split section',
                'boxed CTA',
                'FAQ grid',
            ],
            'preview_sections': [
                {'name': 'hero', 'class': 'is-boxed is-tall'},
                {'name': 'services', 'class': 'is-grid'},
                {'name': 'about', 'class': 'is-split'},
                {'name': 'cta', 'class': 'is-boxed'},
                {'name': 'faq', 'class': 'is-grid'},
            ],
        },
        {
            'label': 'Full-width visual layout',
            'layout_family': 'full_width',
            'slug_hint': 'visual_hero / layout-full-width',
            'use_cases': 'Restaurants, beauty, construction, transport, local brands',
            'sections': [
                'full-width hero band',
                'boxed services',
                'full-width CTA band',
                'image/text section',
                'gallery/grid',
            ],
            'preview_sections': [
                {'name': 'hero', 'class': 'is-full is-tall'},
                {'name': 'services', 'class': 'is-boxed'},
                {'name': 'cta', 'class': 'is-full'},
                {'name': 'story', 'class': 'is-split'},
                {'name': 'gallery', 'class': 'is-grid'},
            ],
        },
        {
            'label': 'Mixed layout',
            'layout_family': 'mixed',
            'slug_hint': 'card_grid / layout-mixed',
            'use_cases': 'Shops, print shops, catalogs, multi-service businesses',
            'sections': [
                'boxed hero',
                'card grid',
                'full-width CTA',
                'boxed FAQ',
                'final dark band',
            ],
            'preview_sections': [
                {'name': 'hero', 'class': 'is-boxed'},
                {'name': 'catalog', 'class': 'is-grid'},
                {'name': 'cta', 'class': 'is-full'},
                {'name': 'faq', 'class': 'is-boxed'},
                {'name': 'final', 'class': 'is-dark'},
            ],
        },
    ]


def _template_wireframe_variants():
    return [
        {'name': 'hero_split', 'purpose': 'Two-column hero for service headline plus supporting panel.', 'mini_class': 'mini-split'},
        {'name': 'hero_centered', 'purpose': 'Centered hero for simple service promise and direct CTA.', 'mini_class': 'mini-centered'},
        {'name': 'hero_visual_overlay', 'purpose': 'Visual hero band with overlay text block and CTA.', 'mini_class': 'mini-overlay'},
        {'name': 'services_icon_cards', 'purpose': 'Simple icon-led cards for clear local service explanations.', 'mini_class': 'mini-grid-three'},
        {'name': 'services_image_cards', 'purpose': 'Image-forward service cards for more visual categories.', 'mini_class': 'mini-grid-three'},
        {'name': 'services_category_grid', 'purpose': 'Dense grid for multi-service or product-style categories.', 'mini_class': 'mini-grid-four'},
        {'name': 'text_left_image_right', 'purpose': 'Story/explanation block with image or visual support.', 'mini_class': 'mini-split'},
        {'name': 'image_left_text_right', 'purpose': 'Alternating content row for proof or feature explanations.', 'mini_class': 'mini-split-reverse'},
        {'name': 'cta_full_width_band', 'purpose': 'High-emphasis full-width conversion strip between sections.', 'mini_class': 'mini-band'},
        {'name': 'cta_boxed_card', 'purpose': 'Contained CTA card for quieter conversion moments.', 'mini_class': 'mini-boxed-cta'},
        {'name': 'faq_grid', 'purpose': 'Simple question/answer grid for common objections.', 'mini_class': 'mini-grid-two'},
        {'name': 'gallery_grid', 'purpose': 'Image/card gallery for examples, categories, or portfolio blocks.', 'mini_class': 'mini-grid-four'},
    ]


def _parse_assistant_sections(text):
    cleaned = (text or '').strip()
    section_titles = [
        ('suggested_reply', 'Suggested reply'),
        ('missing_information', 'Missing information to ask'),
        ('internal_notes', 'Internal notes for staff'),
    ]
    sections = {}

    for index, (key, title) in enumerate(section_titles):
        start = cleaned.find(title)
        if start == -1:
            continue
        content_start = start + len(title)
        next_positions = [
            cleaned.find(next_title, content_start)
            for _next_key, next_title in section_titles[index + 1:]
            if cleaned.find(next_title, content_start) != -1
        ]
        end = min(next_positions) if next_positions else len(cleaned)
        body = cleaned[content_start:end].strip()
        sections[key] = body

    return sections


def staff_root_redirect(request):
    staff_guard = _require_staff_user(request)
    if staff_guard:
        return staff_guard
    return redirect('ai_starter:staff_handoffs')


def _build_staff_assistant_context(selected_handoff=None):
    handoffs = SiteHandoff.objects.select_related('site', 'website_request', 'prepared_by').order_by('-updated_at', '-created_at')
    handoff_options = []
    for handoff in handoffs:
        handoff_options.append(
            {
                'id': handoff.id,
                'label': f'{handoff.site.business_name} - {handoff.site.service_type} - {handoff.get_status_display()}',
                'request_summary': _handoff_request_summary(handoff),
            }
        )

    selected_summary = _handoff_request_summary(selected_handoff) if selected_handoff else None
    return {
        'handoff_options': handoff_options,
        'selected_handoff': selected_handoff,
        'selected_handoff_admin_url': _site_handoff_admin_url(selected_handoff),
        'selected_handoff_request_summary': selected_summary,
        'reply_language_options': _assistant_language_options(),
        'reply_tone_options': _assistant_tone_options(),
        'demo_messages': _assistant_demo_messages(),
    }


def _selected_design_context(request):
    catalog = template_lookup()
    selected_template_id = (request.GET.get('template') or '').strip()
    selected_reference_id = (request.GET.get('style_reference') or '').strip()

    if selected_template_id and selected_template_id in catalog:
        selected = catalog[selected_template_id]
        return {
            'mode': 'template',
            'template_id': selected_template_id,
            'name': selected['name'],
            'category': selected['category'],
            'best_for': selected['best_for'],
            'status': selected['status'],
        }

    if selected_reference_id and selected_reference_id in catalog:
        selected = catalog[selected_reference_id]
        return {
            'mode': 'style_reference',
            'template_id': selected_reference_id,
            'name': selected['name'],
            'category': selected['category'],
            'best_for': selected['best_for'],
            'status': selected['status'],
        }

    return None


def _selected_design_query(selected_design):
    if not selected_design:
        return ''

    key = 'template' if selected_design['mode'] == 'template' else 'style_reference'
    return f'?{key}={selected_design["template_id"]}'


def _starter_main_cta_key(profile_key):
    normalized = str(profile_key or '').strip().lower()
    if normalized in {'garage', 'construction', 'painter'}:
        return 'request_quote'
    if normalized in {'beauty', 'makeup_artist'}:
        return 'book_appointment'
    if normalized in {'taxi', 'transport'}:
        return 'call_now'
    if normalized == 'cleaning':
        return 'request_quote'
    if normalized in {'restaurant', 'bakery'}:
        return 'request_information'
    return 'request_information'


def _build_direct_template_preview_site(template_slug, language):
    valid_template_slugs = {item['slug'] for item in available_template_cards()}
    if template_slug not in valid_template_slugs:
        raise Http404('Unknown template slug.')
    normalized_slug = normalize_template_slug(template_slug)

    site = Site(
        template_slug=normalized_slug,
        color_palette=Site.ColorPalette.ORANGE_BLACK,
        business_name='GOF Template Preview',
        service_type='Small Business Website',
        city='Your Area',
    )
    content_map = build_suggestions(
        business_name=site.business_name,
        service_type=site.service_type,
        city=site.city,
        template_slug=normalized_slug,
        language=language,
    )
    content_map.setdefault('hero', {})['hero_image'] = get_default_image_for_business_type(site.service_type)['key']
    site._prefetched_content_map = content_map
    return site


def _floating_contact_context(site):
    return {
        'floating_contact_href': '#contact',
        'floating_contact_label': 'Contact',
    }


def _website_request_sections(form):
    return [
        {
            'title': _('Business details'),
            'fields': [
                form['business_name'],
                form['business_type'],
                form['existing_website_url'],
                form['current_domain'],
                form['needs_domain_help'],
                form['business_address'],
                form['service_area'],
                form['main_language'],
                form['extra_languages'],
            ],
        },
        {
            'title': _('Contact person'),
            'fields': [
                form['contact_name'],
                form['contact_email'],
                form['contact_phone'],
                form['contact_whatsapp'],
            ],
        },
        {
            'title': _('Website content'),
            'fields': [
                form['main_services'],
                form['business_description'],
                form['opening_hours'],
                form['social_links'],
                form['preferred_colors'],
                form['style_notes'],
                form['special_requests'],
            ],
        },
        {
            'title': _('Uploads'),
            'fields': [
                form['supporting_files'],
                form['request_acknowledgement'],
            ],
        },
    ]


def _meeting_offer_context(form, request_obj=None):
    return {
        'form': form,
        'form_sections': _website_request_sections(form),
        'offer_mode': True,
        'selected_design': None,
        'selected_design_query': '',
        'site_noindex': True,
        'request_submitted': request_obj,
        'meeting_offer': {
            'title': _('Website Launch Package'),
            'normal_price': MEETING_NORMAL_PRICE,
            'offer_price': MEETING_OFFER_PRICE,
            'discount': MEETING_NORMAL_PRICE - MEETING_OFFER_PRICE,
            'source_code': MEETING_OFFER_SOURCE,
        },
        'meeting_examples': [
            {
                'title': 'AutoFix',
                'description': _('Garage and vehicle service website example.'),
                'image': 'core/img/templates/garage-repair-v1.svg',
            },
            {
                'title': 'HMD',
                'description': _('Construction and handyman website example.'),
                'image': 'core/img/templates/construction-trades-v1.svg',
            },
            {
                'title': 'Taxi Top Service',
                'description': _('Taxi and transport website example.'),
                'image': 'core/img/templates/clean-professional-v1.svg',
            },
            {
                'title': 'OPC',
                'description': _('Garage, auto parts, and motorcycle parts concept.'),
                'image': 'core/img/templates/restaurant-local-v1.svg',
            },
        ],
        'template_cards': available_template_cards(),
        'selected_template_slug': default_template_slug(),
        'selected_template_card': get_template_card(default_template_slug()),
    }


def _build_request_email_body(website_request):
    uploaded_lines = [
        f'- {request_file.original_name}: {request_file.file.name}'
        for request_file in website_request.files.all()
    ] or ['- No files uploaded']

    return '\n'.join(
        [
            f'Request ID: {website_request.public_id}',
            f'Business name: {website_request.business_name}',
            f'Contact name: {website_request.contact_name}',
            f'Contact email: {website_request.contact_email}',
            f'Phone: {website_request.contact_phone or "Not provided"}',
            f'WhatsApp: {website_request.contact_whatsapp or "Not provided"}',
            f'Business type: {website_request.business_type}',
            f'Existing website: {website_request.existing_website_url or "Not provided"}',
            f'Current domain: {website_request.current_domain or "Not provided"}',
            f'Domain help needed: {"Yes" if website_request.needs_domain_help else "No"}',
            f'Main services: {website_request.main_services}',
            f'Main language: {website_request.main_language}',
            f'Extra languages: {website_request.extra_languages or "Not provided"}',
            f'Source/coupon: {website_request.source_code}',
            'Uploaded files:',
            *uploaded_lines,
            f'Timestamp: {website_request.created_at.isoformat()}',
        ]
    )


def _onboarding_step_definitions():
    return [
        {'number': 1, 'title': 'What is your website for?'},
        {'number': 2, 'title': 'Your intro section'},
        {'number': 3, 'title': 'Select the services you offer'},
        {'number': 4, 'title': 'Portfolio or gallery'},
        {'number': 5, 'title': 'Reviews and trust'},
        {'number': 6, 'title': 'Where should customers find you?'},
        {'number': 7, 'title': 'Choose how you want to start'},
        {'number': 8, 'title': 'Your private preview is ready to prepare'},
    ]


def _safe_onboarding_step(value, default=1):
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, ONBOARDING_TOTAL_STEPS))


def _onboarding_gallery_choices():
    return [
        {'value': 'example_layout', 'label': 'Show example layout for now', 'description': 'Use generic preview content for the gallery section.'},
        {'value': 'add_later', 'label': 'I will add photos later', 'description': 'Keep the section light and note that final photos come later.'},
        {'value': 'template_assets', 'label': 'Use template/demo images if available', 'description': 'Show staff-prepared template assets when they exist.'},
    ]


def _onboarding_reviews_choices():
    return [
        {'value': 'add_review', 'label': 'Add a review now', 'description': 'Include one customer review or endorsement if you already have it.'},
        {'value': 'trust_section', 'label': 'Use a trust section for now', 'description': 'Show a quality/trust block instead of a direct review.'},
        {'value': 'skip', 'label': 'Skip for now', 'description': 'Keep the preview simpler and add trust content later.'},
    ]


def _choice_label(choice_value, choices):
    for choice in choices:
        if choice['value'] == choice_value:
            return choice['label']
    return choice_value


def _effective_business_type_for_suggestions(business_type, business_name=''):
    primary = str(business_type or '').strip()
    if primary:
        primary_profile = resolve_business_profile(primary)
        if primary_profile.get('exact_match') or primary_profile.get('family') != 'generic':
            return primary

    name_candidate = str(business_name or '').strip()
    if name_candidate:
        name_profile = resolve_business_profile(name_candidate)
        if name_profile.get('exact_match') or name_profile.get('family') != 'generic':
            return name_candidate

    return primary


def _current_intro_variant_index(state):
    suggestion_type = _effective_business_type_for_suggestions(
        state.get('business_type'),
        state.get('business_name'),
    )
    variants = get_onboarding_intro_variants(suggestion_type)
    current_title = str(state.get('intro_title') or '').strip()
    current_text = str(state.get('intro_text') or '').strip()
    for index, variant in enumerate(variants):
        if current_title == str(variant['title']) and current_text == str(variant['text']):
            return index
    return 0


def _next_intro_variant(state):
    suggestion_type = _effective_business_type_for_suggestions(
        state.get('business_type'),
        state.get('business_name'),
    )
    variants = get_onboarding_intro_variants(suggestion_type)
    current_index = _current_intro_variant_index(state)
    next_variant = variants[(current_index + 1) % len(variants)]
    return {
        'title': str(next_variant['title']),
        'text': str(next_variant['text']),
    }


def _hero_profile_values(business_type, business_name=''):
    suggestion_type = _effective_business_type_for_suggestions(business_type, business_name)
    profile = resolve_business_profile(suggestion_type)
    return {
        'title': str(profile['hero_title']),
        'description': str(profile['hero_description']),
        'cta': str(profile['hero_cta']),
    }


def _onboarding_direction_cards(selected_template_slug):
    cards = [
        {
            'slug': 'classic_service',
            'title': 'Basic',
            'label': 'Basic',
            'description': 'A simple website with the essentials.',
            'best_for': 'Local services, beauty, resellers, and small businesses.',
        },
        {
            'slug': 'visual_hero',
            'title': 'Growth',
            'label': 'Growth',
            'description': 'More pages and more room to grow.',
            'best_for': 'Construction, garages, transport, and multi-service businesses.',
        },
        {
            'slug': 'card_grid',
            'title': 'Shop',
            'label': 'Shop',
            'description': 'A website with products and selling options.',
            'best_for': 'Shops, product resellers, parts sellers, and niche retail businesses.',
        },
    ]
    for card in cards:
        card['selected'] = card['slug'] == selected_template_slug
    return cards


def _coerce_onboarding_state(source, selected_template_slug):
    def source_value(key, default=''):
        if hasattr(source, 'getlist'):
            values = [str(value).strip() for value in source.getlist(key) if str(value).strip()]
            if values:
                return values[-1]
        return str(source.get(key, default) or default).strip()

    business_type = source_value('business_type')
    business_name = source_value('business_name')
    effective_business_type = _effective_business_type_for_suggestions(business_type, business_name)
    previous_business_type = source_value('previous_business_type')
    profile = resolve_business_profile(effective_business_type)
    previous_profile = resolve_business_profile(previous_business_type)
    template_locked = source_value('template_locked')

    def suggested_value(raw_value, field_key):
        value = str(raw_value or '').strip()
        current_default = str(profile[field_key])
        previous_default = str(previous_profile[field_key])
        fallback_default = str(ONBOARDING_FIELD_FALLBACKS[field_key])
        if not value:
            return current_default
        if effective_business_type and value == fallback_default:
            return current_default
        if previous_business_type and effective_business_type != previous_business_type:
            if value in {previous_default, fallback_default}:
                return current_default
        return value

    gallery_choice = source_value('gallery_choice', 'example_layout') or 'example_layout'
    if gallery_choice == 'project_assets':
        gallery_choice = 'template_assets'

    state = {
        'business_type': business_type,
        'previous_business_type': business_type or previous_business_type,
        'template_locked': template_locked,
        'hero_title': suggested_value(source_value('hero_title'), 'hero_title'),
        'hero_description': suggested_value(source_value('hero_description'), 'hero_description'),
        'hero_cta': suggested_value(source_value('hero_cta'), 'hero_cta'),
        'intro_title': suggested_value(source_value('intro_title'), 'intro_title'),
        'intro_text': suggested_value(source_value('intro_text'), 'intro_text'),
        'gallery_choice': gallery_choice,
        'reviews_choice': source_value('reviews_choice', 'trust_section') or 'trust_section',
        'review_text': source_value('review_text'),
        'business_name': business_name,
        'city': source_value('city'),
        'contact_email': source_value('contact_email'),
        'contact_phone': source_value('contact_phone'),
        'contact_whatsapp': source_value('contact_whatsapp'),
        'template_slug': normalize_template_slug(source_value('template_slug', selected_template_slug) or selected_template_slug),
        'custom_service': source_value('custom_service'),
    }
    if state['template_locked'] not in {'1', 'true', 'yes'}:
        state['template_slug'] = normalize_template_slug(profile.get('recommended_template_slug') or state['template_slug'])
    return state


def _selected_onboarding_services(request, state):
    selected = [
        value.strip()
        for value in request.POST.getlist('selected_services')
        if value and value.strip()
    ]
    source_services = request.POST.get('selected_services_csv', '')
    if not selected and source_services:
        selected = [item.strip() for item in source_services.split('||') if item.strip()]
    if state['custom_service'] and state['custom_service'] not in selected:
        selected.append(state['custom_service'])
    if not selected:
        suggestion_type = _effective_business_type_for_suggestions(
            state.get('business_type'),
            state.get('business_name'),
        )
        selected = get_onboarding_service_suggestions(suggestion_type)[:3]
    return selected


def _serialize_onboarding_services(services):
    return '||'.join(str(service) for service in services if service)


def _onboarding_validation_errors(step_number, state):
    errors = []
    if step_number == 1 and not state['business_type']:
        errors.append('Business type or activity is required.')
    if step_number == 6:
        if not state['business_name']:
            errors.append('Business name is required.')
        if not state['city']:
            errors.append('City or service area is required.')
    return errors


def _apply_onboarding_content(site, language, wizard_state, selected_services):
    suggestions = build_suggestions(
        business_name=site.business_name,
        service_type=site.service_type,
        city=site.city,
        template_slug=site.template_slug,
        selected_services=selected_services,
        service_descriptions=selected_services[:3],
        phone=wizard_state.get('contact_phone') or wizard_state.get('contact_whatsapp'),
        email=wizard_state.get('contact_email'),
        location=wizard_state.get('city'),
        language=language,
        context_data=wizard_state,
    )
    profile = resolve_business_profile(site.service_type)

    def has_customized_value(value, defaults):
        normalized_value = str(value or '').strip()
        if not normalized_value:
            return False
        normalized_defaults = {str(default or '').strip() for default in defaults if str(default or '').strip()}
        return normalized_value not in normalized_defaults

    should_override_hero_title = has_customized_value(
        wizard_state.get('hero_title'),
        [profile.get('hero_title'), ONBOARDING_FIELD_FALLBACKS['hero_title']],
    )
    should_override_hero_description = has_customized_value(
        wizard_state.get('hero_description'),
        [profile.get('hero_description'), ONBOARDING_FIELD_FALLBACKS['hero_description']],
    )
    should_override_hero_cta = has_customized_value(
        wizard_state.get('hero_cta'),
        [profile.get('hero_cta'), ONBOARDING_FIELD_FALLBACKS['hero_cta']],
    )
    should_override_intro_title = has_customized_value(
        wizard_state.get('intro_title'),
        [
            profile.get('intro_title'),
            profile.get('intro_heading'),
            ONBOARDING_FIELD_FALLBACKS['intro_title'],
            *ONBOARDING_INTRO_FALLBACK_TITLES,
        ],
    )
    should_override_intro_text = has_customized_value(
        wizard_state.get('intro_text'),
        [
            profile.get('intro_text'),
            ONBOARDING_FIELD_FALLBACKS['intro_text'],
            *ONBOARDING_INTRO_FALLBACK_TEXTS,
        ],
    )

    active_template_slug = normalize_template_slug(site.template_slug)
    if should_override_hero_title:
        suggestions['hero']['title'] = wizard_state['hero_title']
    if should_override_hero_description:
        suggestions['hero']['description'] = wizard_state['hero_description']
    if should_override_hero_cta:
        suggestions['hero']['cta_text'] = wizard_state['hero_cta']

    primary_contact_bits = [wizard_state['contact_phone'], wizard_state['contact_email']]
    primary_contact = ' | '.join(bit for bit in primary_contact_bits if bit) or 'Contact details ready to review'
    secondary_contact = wizard_state['contact_whatsapp'] or wizard_state['city'] or 'Final details are reviewed after activation'

    if active_template_slug == 'gof-canva-layout-test-v1':
        if should_override_intro_title:
            suggestions['about']['title'] = wizard_state['intro_title'] or suggestions['about']['title']
        if should_override_intro_text:
            suggestions['about']['description'] = wizard_state['intro_text']
        for index in range(6):
            suggestions['services'][f'item_{index + 1}'] = selected_services[index] if index < len(selected_services) else ''

        suggestions['contact']['detail_1_value'] = wizard_state['contact_phone'] or suggestions['contact']['detail_1_value']
        suggestions['contact']['detail_2_value'] = wizard_state['contact_email'] or suggestions['contact']['detail_2_value']
        suggestions['contact']['detail_3_value'] = wizard_state['contact_whatsapp'] or suggestions['contact']['detail_3_value']
        suggestions['contact']['detail_4_value'] = wizard_state['city'] or suggestions['contact']['detail_4_value']
        suggestions['contact']['cta_text'] = wizard_state['hero_cta'] or suggestions['contact']['cta_text']
        suggestions['final_cta']['title'] = wizard_state['business_name'] or site.business_name

        if wizard_state['reviews_choice'] == 'add_review' and wizard_state['review_text']:
            suggestions['trust']['intro'] = wizard_state['review_text']
        elif wizard_state['reviews_choice'] == 'trust_section':
            suggestions['trust']['intro'] = (
                'Preview trust section. Final trust details, reviews, and business proof are reviewed after activation.'
            )

        if wizard_state['gallery_choice'] == 'template_assets':
            suggestions['portfolio']['intro'] = (
                'Preview gallery uses demo or template assets when available. Final images are reviewed after activation.'
            )
        elif wizard_state['gallery_choice'] == 'add_later':
            suggestions['portfolio']['intro'] = (
                'Show examples of your work, products, or previous results here. Final photos can be added later.'
            )

        suggestions['final_cta']['description'] = (
            'Preview content. Final content, gallery images, and trust details are reviewed and completed after activation.'
        )
    else:
        if should_override_intro_title:
            suggestions['services']['title'] = wizard_state['intro_title'] or suggestions['services'].get('title', 'Selected services')
        if should_override_intro_text:
            suggestions['services']['intro'] = wizard_state['intro_text']
        for index in range(3):
            suggestions['services'][f'item_{index + 1}'] = selected_services[index] if index < len(selected_services) else ''

        suggestions['contact']['title'] = wizard_state['business_name'] or site.business_name
        suggestions['contact']['description'] = (
            f"{wizard_state['business_name'] or site.business_name} serves {wizard_state['city'] or site.city}. "
            'Preview content. Final content is reviewed and completed after activation.'
        )
        suggestions['contact']['primary_contact'] = primary_contact
        suggestions['contact']['secondary_contact'] = secondary_contact
        suggestions['contact']['cta_text'] = wizard_state['hero_cta'] or suggestions['contact']['cta_text']
        suggestions['cta']['title'] = wizard_state['business_name'] or site.business_name

        if wizard_state['reviews_choice'] == 'add_review' and wizard_state['review_text']:
            suggestions['cta']['description'] = wizard_state['review_text']
        elif wizard_state['reviews_choice'] == 'trust_section':
            suggestions['cta']['description'] = (
                'Preview trust section. Final trust details, reviews, and business proof are reviewed after activation.'
            )
        elif wizard_state['gallery_choice'] == 'template_assets':
            suggestions['cta']['description'] = (
                'Preview gallery uses demo or template assets when available. Final images are reviewed after activation.'
            )
        else:
            suggestions['cta']['description'] = (
                'Preview content. Final content, gallery images, and trust details are reviewed and completed after activation.'
            )

    save_site_content(site, language, suggestions)


def _build_onboarding_preview_context(state, selected_services):
    project_slug = normalize_project_slug(state['business_name'] or state['business_type'])
    logo_asset = get_first_project_asset(project_slug, 'logo') if project_slug else None
    hero_asset = get_first_project_asset(project_slug, 'hero') if project_slug else None
    gallery_heading = {
        'example_layout': 'Example preview gallery',
        'add_later': 'Gallery can be added later',
        'template_assets': 'Template or demo image preview',
    }.get(state['gallery_choice'], 'Example preview gallery')
    trust_heading = {
        'add_review': 'Review preview',
        'trust_section': 'Trust section preview',
        'skip': 'Trust section can be added later',
    }.get(state['reviews_choice'], 'Trust section preview')
    contact_lines = [
        state['business_name'] or 'Your business name',
        state['city'] or 'Your city or service area',
    ]
    if state['contact_email']:
        contact_lines.append(state['contact_email'])
    if state['contact_phone']:
        contact_lines.append(state['contact_phone'])
    if state['contact_whatsapp']:
        contact_lines.append(f"WhatsApp: {state['contact_whatsapp']}")

    return {
        'logo_asset': logo_asset,
        'hero_asset': hero_asset,
        'preview_title': state['hero_title'],
        'preview_description': state['hero_description'],
        'preview_cta': state['hero_cta'],
        'intro_title': state['intro_title'],
        'intro_text': state['intro_text'],
        'selected_services': selected_services[:6],
        'gallery_heading': gallery_heading,
        'gallery_note': 'Preview content. Final images are reviewed and completed after activation.',
        'trust_heading': trust_heading,
        'trust_note': (
            state['review_text']
            if state['reviews_choice'] == 'add_review' and state['review_text']
            else 'Preview content. Final trust details are reviewed after activation.'
        ),
        'contact_lines': contact_lines,
        'template_label': next(
            (card['title'] for card in _onboarding_direction_cards(state['template_slug']) if card['selected']),
            'Basic',
        ),
    }


def _render_start_wizard(request, *, current_step, wizard_state, selected_design, errors=None, status=200):
    suggestion_type = _effective_business_type_for_suggestions(
        wizard_state.get('business_type'),
        wizard_state.get('business_name'),
    )
    selected_services = wizard_state.get('selected_services') or get_onboarding_service_suggestions(suggestion_type)[:3]
    preview_context = _build_onboarding_preview_context(wizard_state, selected_services)
    gallery_choices = _onboarding_gallery_choices()
    reviews_choices = _onboarding_reviews_choices()
    steps = _onboarding_step_definitions()
    for step in steps:
        step['is_active'] = step['number'] == current_step
        step['is_complete'] = step['number'] < current_step

    return render(
        request,
        'ai_starter/start.html',
        {
            'wizard_mode': True,
            'current_step': current_step,
            'wizard_steps': steps,
            'wizard_state': wizard_state,
            'wizard_errors': errors or [],
            'wizard_service_suggestions': get_onboarding_service_suggestions(suggestion_type),
            'wizard_gallery_choices': gallery_choices,
            'wizard_reviews_choices': reviews_choices,
            'wizard_direction_cards': _onboarding_direction_cards(wizard_state['template_slug']),
            'wizard_preview': preview_context,
            'wizard_summary': {
                'gallery_label': _choice_label(wizard_state['gallery_choice'], gallery_choices),
                'reviews_label': _choice_label(wizard_state['reviews_choice'], reviews_choices),
            },
            'selected_design': selected_design,
            'selected_design_query': _selected_design_query(selected_design),
        },
        status=status,
    )


@require_http_methods(['GET', 'POST'])
def start_onboarding(request):
    selected_design = _selected_design_context(request)
    selected_design_query = _selected_design_query(selected_design)
    submitted_request_id = request.GET.get('submitted', '').strip()
    submitted_request = None
    if submitted_request_id:
        submitted_request = WebsiteRequest.objects.filter(
            public_id=submitted_request_id,
            source_code='STARTER_PUBLIC',
        ).first()

    template_options = [
        {'key': 'classic_local', 'label': 'Classic local business'},
        {'key': 'visual_showcase', 'label': 'Visual showcase'},
        {'key': 'service_focused', 'label': 'Service-focused'},
        {'key': 'simple_landing', 'label': 'Simple landing page'},
    ]
    palette_options = [
        {'key': 'warm_orange', 'label': 'Warm orange'},
        {'key': 'clean_bw', 'label': 'Clean black and white'},
        {'key': 'soft_beige', 'label': 'Soft beige'},
        {'key': 'elegant_dark', 'label': 'Elegant dark'},
        {'key': 'fresh_green', 'label': 'Fresh green'},
        {'key': 'blue_professional', 'label': 'Blue professional'},
    ]
    font_options = [
        {'key': 'clean', 'label': 'Clean'},
        {'key': 'modern', 'label': 'Modern'},
        {'key': 'elegant', 'label': 'Elegant'},
        {'key': 'bold', 'label': 'Bold'},
    ]
    image_set_base_options = [
        {'key': 'suggested', 'label': 'Suggested (auto-selected)'},
        {'key': 'generic_service', 'label': 'Generic service images'},
        {'key': 'none', 'label': 'No images for now'},
    ]
    cta_options = [
        {'key': 'request_information', 'label': 'Request information'},
        {'key': 'request_quote', 'label': 'Request quote'},
        {'key': 'book_appointment', 'label': 'Book appointment'},
        {'key': 'call_now', 'label': 'Call now'},
        {'key': 'whatsapp', 'label': 'WhatsApp'},
    ]
    launch_type_options = [
        {
            'key': 'starter_page',
            'label': 'Starter Page',
            'summary': 'One clear page to get online fast.',
            'details': [
                'Best for quick visibility',
                'Good for landing pages, small services, temporary offers, and simple businesses',
                'Includes hero, services, images, contact section, and main call to action',
            ],
            'note': '',
        },
        {
            'key': 'full_website',
            'label': 'Full Website',
            'summary': 'A complete website with separate pages.',
            'details': [
                'Best for businesses that need stronger structure and future growth',
                'Includes Home, About, Services, Contact, and optional extra pages',
                'Delivered as a full website after activation',
            ],
            'note': 'Full websites are prepared for WordPress delivery after activation.',
        },
    ]

    template_option_keys = {item['key'] for item in template_options}
    palette_option_keys = {item['key'] for item in palette_options}
    font_option_keys = {item['key'] for item in font_options}
    image_set_option_keys = {item['key'] for item in image_set_base_options}
    cta_option_keys = {item['key'] for item in cta_options}
    launch_option_keys = {item['key'] for item in launch_type_options}
    launch_type_labels = {item['key']: item['label'] for item in launch_type_options}

    page_options = [
        {'key': 'home', 'label': 'Home', 'required': True, 'recommended': False},
        {'key': 'about', 'label': 'About', 'required': False, 'recommended': True},
        {'key': 'services', 'label': 'Services', 'required': False, 'recommended': True},
        {'key': 'contact', 'label': 'Contact', 'required': True, 'recommended': False},
        {'key': 'projects', 'label': 'Projects / Portfolio', 'required': False, 'recommended': False},
        {'key': 'gallery', 'label': 'Gallery', 'required': False, 'recommended': False},
        {'key': 'reviews', 'label': 'Reviews', 'required': False, 'recommended': False},
        {'key': 'faq', 'label': 'FAQ', 'required': False, 'recommended': False},
        {'key': 'prices_menu', 'label': 'Prices / Menu', 'required': False, 'recommended': False},
        {'key': 'service_area', 'label': 'Service Area', 'required': False, 'recommended': False},
        {'key': 'blog_news', 'label': 'Blog / News', 'required': False, 'recommended': False},
    ]
    page_option_keys = [item['key'] for item in page_options]
    page_label_map = {item['key']: item['label'] for item in page_options}
    required_page_keys = {'home', 'contact'}
    default_full_website_pages = ['home', 'about', 'services', 'contact']

    contact_detail_fields = [
        'contact_name',
        'email',
        'phone',
        'whatsapp',
        'address',
        'service_area_detail',
        'opening_hours',
        'social_facebook',
        'social_instagram',
        'social_linkedin',
        'social_tiktok',
    ]

    section_visibility_keys = [
        'show_services',
        'show_gallery',
        'show_reviews',
        'show_location',
        'show_contact_cta',
    ]

    def _safe_step(value, default=1):
        try:
            parsed = int(value or default)
        except (TypeError, ValueError):
            parsed = default
        return max(1, min(parsed, STARTER_WIZARD_TOTAL_STEPS))

    def _normalize_single_line(value, *, max_length=140):
        return ' '.join(str(value or '').strip().split())[:max_length]

    def _step_url(step_number):
        base = f"{reverse('ai_starter:start')}?step={step_number}"
        if selected_design_query:
            return f"{base}&{selected_design_query.lstrip('?')}"
        return base

    def _normalize_choice(value, allowed_keys, fallback):
        candidate = str(value or '').strip()
        if candidate in allowed_keys:
            return candidate
        return fallback

    def _default_contact_details():
        return {field: '' for field in contact_detail_fields}

    def _safe_starter_draft(raw_draft):
        draft = raw_draft if isinstance(raw_draft, dict) else {}
        hero = draft.get('hero') if isinstance(draft.get('hero'), dict) else {}
        intro = draft.get('intro') if isinstance(draft.get('intro'), dict) else {}
        services = draft.get('services') if isinstance(draft.get('services'), list) else []
        service_cards = draft.get('service_cards') if isinstance(draft.get('service_cards'), list) else []
        contact_details = (
            _normalize_contact_details(draft.get('contact_details'))
            if isinstance(draft.get('contact_details'), dict)
            else _default_contact_details()
        )
        section_visibility = draft.get('section_visibility') if isinstance(draft.get('section_visibility'), dict) else {}
        selected_pages = _sanitize_selected_pages(draft.get('selected_pages', []))

        return {
            'business_name': str(draft.get('business_name') or '').strip(),
            'business_type': str(draft.get('business_type') or '').strip(),
            'service_area': str(draft.get('service_area') or '').strip(),
            'services': services,
            'resolved_profile': str(draft.get('resolved_profile') or '').strip(),
            'template_key': str(draft.get('template_key') or '').strip(),
            'palette_key': str(draft.get('palette_key') or '').strip(),
            'font_key': str(draft.get('font_key') or '').strip(),
            'image_set_key': str(draft.get('image_set_key') or '').strip(),
            'main_cta': str(draft.get('main_cta') or '').strip(),
            'section_visibility': section_visibility,
            'hero': {
                'title': str(hero.get('title') or '').strip(),
                'description': str(hero.get('description') or '').strip(),
                'cta': str(hero.get('cta') or '').strip(),
                'image_key': str(hero.get('image_key') or '').strip(),
                'image_category': str(hero.get('image_category') or '').strip(),
            },
            'intro': {
                'title': str(intro.get('title') or '').strip(),
                'text': str(intro.get('text') or '').strip(),
            },
            'service_cards': [
                {
                    'title': str(item.get('title') or '').strip(),
                    'text': str(item.get('text') or '').strip(),
                }
                for item in service_cards
                if isinstance(item, dict) and (str(item.get('title') or '').strip() or str(item.get('text') or '').strip())
            ],
            'launch_type': str(draft.get('launch_type') or '').strip(),
            'selected_pages': selected_pages,
            'contact_details': contact_details,
        }

    def _normalize_contact_details(raw_details):
        raw = raw_details if isinstance(raw_details, dict) else {}
        normalized = _default_contact_details()
        for field in contact_detail_fields:
            value = str(raw.get(field) or '').strip()
            max_length = 500 if field == 'opening_hours' else 200
            normalized[field] = value[:max_length]
        return normalized

    def _sanitize_selected_pages(raw_pages, *, default_when_empty=False):
        raw_list = raw_pages if isinstance(raw_pages, list) else []
        selected_set = {str(item).strip() for item in raw_list if str(item).strip() in page_option_keys}
        if default_when_empty and not selected_set:
            selected_set = set(default_full_website_pages)
        selected_set.update(required_page_keys)
        return [key for key in page_option_keys if key in selected_set]

    def _selected_page_labels(selected_pages):
        return [page_label_map[key] for key in selected_pages if key in page_label_map]

    def _is_true(value):
        if isinstance(value, bool):
            return value
        normalized = str(value or '').strip().lower()
        return normalized in {'1', 'true', 'yes', 'on'}

    def _cta_label(cta_key):
        for option in cta_options:
            if option['key'] == cta_key:
                return option['label']
        return 'Request information'

    def _parse_services_text(value):
        seen = set()
        parsed = []
        for raw_line in str(value or '').splitlines():
            clean = raw_line.strip().lstrip('-*•').strip()
            if not clean:
                continue
            clean = clean[:120]
            lowered = clean.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            parsed.append(clean)
            if len(parsed) >= 6:
                break
        return parsed

    def _default_state():
        return {
            'step': 1,
            'business_name': '',
            'business_type': '',
            'service_area': '',
            'services_text': '',
            'services': [],
            'template_key': 'classic_local',
            'palette_key': 'warm_orange',
            'font_key': 'clean',
            'image_set_key': 'suggested',
            'main_cta': 'request_information',
            'section_visibility': {
                'show_services': True,
                'show_gallery': True,
                'show_reviews': False,
                'show_location': True,
                'show_contact_cta': True,
            },
            'launch_type': '',
            'selected_pages': [],
            'contact_details': _default_contact_details(),
            'starter_draft': _safe_starter_draft({}),
        }

    def _has_starter_draft(state):
        draft = state.get('starter_draft')
        if not isinstance(draft, dict):
            return False
        return bool(draft.get('business_name'))

    def _resolve_style_state(state):
        draft = state.get('starter_draft') if isinstance(state.get('starter_draft'), dict) else {}

        profile_template_map = {
            'classic_service': 'classic_local',
            'visual_hero': 'visual_showcase',
            'clean_professional': 'service_focused',
            'landing_page': 'simple_landing',
        }
        draft_template = profile_template_map.get(str(draft.get('template_key') or '').strip(), 'classic_local')
        template_key = _normalize_choice(state.get('template_key') or draft.get('template_key'), template_option_keys, draft_template)
        palette_key = _normalize_choice(state.get('palette_key') or draft.get('palette_key'), palette_option_keys, 'warm_orange')
        font_key = _normalize_choice(state.get('font_key') or draft.get('font_key'), font_option_keys, 'clean')

        auto_image_set_key = str(draft.get('image_set_key') or 'generic_service').strip() or 'generic_service'
        image_set_key = str(state.get('image_set_key') or '').strip() or auto_image_set_key
        if image_set_key != auto_image_set_key:
            image_set_key = _normalize_choice(image_set_key, image_set_option_keys, auto_image_set_key)

        main_cta = _normalize_choice(state.get('main_cta') or draft.get('main_cta'), cta_option_keys, 'request_information')

        previous_visibility = state.get('section_visibility') if isinstance(state.get('section_visibility'), dict) else {}
        gallery_default = bool(image_set_key == 'suggested' or image_set_key not in {'none', ''})
        resolved_visibility = {
            'show_services': _is_true(previous_visibility.get('show_services', True)),
            'show_gallery': _is_true(previous_visibility.get('show_gallery', gallery_default)),
            'show_reviews': _is_true(previous_visibility.get('show_reviews', False)),
            'show_location': _is_true(previous_visibility.get('show_location', True)),
            'show_contact_cta': _is_true(previous_visibility.get('show_contact_cta', True)),
        }

        return {
            'template_key': template_key,
            'palette_key': palette_key,
            'font_key': font_key,
            'image_set_key': image_set_key,
            'auto_image_set_key': auto_image_set_key,
            'main_cta': main_cta,
            'section_visibility': resolved_visibility,
            'main_cta_label': _cta_label(main_cta),
        }

    def _apply_style_to_state(state, style_values):
        state['template_key'] = style_values['template_key']
        state['palette_key'] = style_values['palette_key']
        state['font_key'] = style_values['font_key']
        state['image_set_key'] = style_values['image_set_key']
        state['main_cta'] = style_values['main_cta']
        state['section_visibility'] = dict(style_values['section_visibility'])

        draft = state.get('starter_draft') if isinstance(state.get('starter_draft'), dict) else {}
        if isinstance(draft, dict):
            draft['template_key'] = style_values['template_key']
            draft['palette_key'] = style_values['palette_key']
            draft['font_key'] = style_values['font_key']
            draft['image_set_key'] = style_values['image_set_key']
            draft['main_cta'] = style_values['main_cta']
            draft['section_visibility'] = dict(style_values['section_visibility'])
            if isinstance(draft.get('hero'), dict):
                draft['hero']['cta'] = style_values['main_cta_label']
            state['starter_draft'] = draft

    def _parse_step2_style_submission(post_data, state):
        current_values = _resolve_style_state(state)
        auto_image_set_key = current_values['auto_image_set_key']

        template_key = _normalize_choice(post_data.get('template_key'), template_option_keys, current_values['template_key'])
        palette_key = _normalize_choice(post_data.get('palette_key'), palette_option_keys, current_values['palette_key'])
        font_key = _normalize_choice(post_data.get('font_key'), font_option_keys, current_values['font_key'])
        requested_image_set = str(post_data.get('image_set_key') or '').strip()
        if requested_image_set in image_set_option_keys:
            image_set_key = requested_image_set
        elif requested_image_set == auto_image_set_key:
            image_set_key = auto_image_set_key
        else:
            image_set_key = current_values['image_set_key']

        main_cta = _normalize_choice(post_data.get('main_cta'), cta_option_keys, current_values['main_cta'])

        section_visibility = {
            'show_services': 'show_services' in post_data,
            'show_gallery': 'show_gallery' in post_data,
            'show_reviews': 'show_reviews' in post_data,
            'show_location': 'show_location' in post_data,
            'show_contact_cta': 'show_contact_cta' in post_data,
        }

        return {
            'template_key': template_key,
            'palette_key': palette_key,
            'font_key': font_key,
            'image_set_key': image_set_key,
            'auto_image_set_key': auto_image_set_key,
            'main_cta': main_cta,
            'section_visibility': section_visibility,
            'main_cta_label': _cta_label(main_cta),
        }

    def _load_state():
        saved = request.session.get(STARTER_WIZARD_SESSION_KEY)
        if not isinstance(saved, dict):
            return _default_state()
        merged = _default_state()
        merged.update(saved)
        merged['starter_draft'] = _safe_starter_draft(merged.get('starter_draft'))
        if not isinstance(merged.get('services'), list):
            merged['services'] = []
        if not isinstance(merged.get('selected_pages'), list):
            merged['selected_pages'] = []
        if not isinstance(merged.get('section_visibility'), dict):
            merged['section_visibility'] = _default_state()['section_visibility']
        merged['contact_details'] = _normalize_contact_details(merged.get('contact_details'))
        merged['step'] = _safe_step(merged.get('step'), default=1)
        return merged

    def _save_state(state):
        request.session[STARTER_WIZARD_SESSION_KEY] = state
        request.session.modified = True

    def _starter_image_set_key(profile):
        profile_key = str(profile.get('key') or '').strip().lower()
        profile_family = str(profile.get('family') or '').strip().lower()
        key_source = profile_key or profile_family
        mapping = {
            'makeup_artist': 'makeup',
            'beauty': 'beauty',
            'garage': 'garage',
            'transport': 'taxi',
            'taxi': 'taxi',
            'construction': 'trades',
            'cleaning': 'generic_service',
            'restaurant': 'restaurant',
            'shop': 'generic_service',
            'printing': 'generic_service',
            'service_local': 'generic_service',
            'construction_trades': 'trades',
            'beauty_wellness': 'beauty',
            'food_restaurant': 'food',
        }
        if key_source in mapping:
            return mapping[key_source]
        if 'garage' in key_source or 'auto' in key_source:
            return 'garage'
        if 'taxi' in key_source or 'transport' in key_source:
            return 'taxi'
        if 'beauty' in key_source or 'makeup' in key_source or 'salon' in key_source:
            return 'beauty'
        if 'restaurant' in key_source or 'food' in key_source:
            return 'food'
        if 'paint' in key_source or 'handyman' in key_source or 'electric' in key_source or 'trade' in key_source:
            return 'trades'
        return 'generic_service'

    def _build_starter_draft(*, business_name, business_type, service_area, services):
        suggestion_type = _effective_business_type_for_suggestions(business_type, business_name)
        profile = resolve_business_profile(suggestion_type)

        profile_services = [
            str(item).strip()
            for item in profile.get('services', profile.get('suggested_services', []))
            if str(item).strip()
        ]
        chosen_services = list(services) if services else profile_services[:6]
        if not chosen_services:
            chosen_services = ['Main service', 'Popular option', 'Customer support']

        display_business_type = _normalize_single_line(
            business_type or profile.get('display_business_type') or profile.get('key') or 'Local business',
            max_length=120,
        )
        display_name = _normalize_single_line(business_name or display_business_type, max_length=120)
        display_area = _normalize_single_line(service_area, max_length=120)

        service_phrase = ', '.join(chosen_services[:3]).lower()
        if display_area:
            hero_title = f'{display_business_type} in {display_area}'
            if service_phrase:
                hero_title = f'{display_business_type} in {display_area} for {service_phrase}'
            hero_description = (
                f'{display_name} helps customers in {display_area} with {service_phrase}. '
                'Review this starter preview and adjust details before continuing.'
            )
        else:
            hero_title = f'{display_business_type} website preview'
            hero_description = (
                f'{display_name} helps customers with {service_phrase}. '
                'Review this starter preview and adjust details before continuing.'
            )

        hero_cta = str(profile.get('hero_cta') or 'Request information').strip() or 'Request information'
        main_cta_key = _starter_main_cta_key(profile.get('key') or profile.get('family'))
        intro_title = str(profile.get('intro_title') or profile.get('intro_heading') or 'Your business introduction').strip()
        intro_text = str(profile.get('intro_text') or '').strip()
        if not intro_text:
            intro_text = (
                f'Introduce {display_name}, highlight {display_business_type.lower()}, '
                'and explain how customers can contact you quickly.'
            )

        default_image = get_default_image_for_business_type(display_business_type)
        template_key = normalize_template_slug(profile.get('recommended_template_slug'))

        return {
            'business_name': display_name,
            'business_type': display_business_type,
            'service_area': display_area,
            'services': chosen_services,
            'resolved_profile': str(profile.get('key') or profile.get('family') or 'generic'),
            'image_set_key': _starter_image_set_key(profile),
            'template_key': template_key,
            'palette_key': 'warm_orange',
            'font_key': 'clean',
            'main_cta': main_cta_key,
            'hero': {
                'title': hero_title,
                'description': hero_description,
                'cta': hero_cta,
                'image_key': default_image.get('key', ''),
                'image_category': default_image.get('category', ''),
            },
            'intro': {
                'title': intro_title,
                'text': intro_text,
            },
            'service_cards': [{'title': item, 'text': ''} for item in chosen_services[:6]],
            'section_visibility': {
                'show_services': True,
                'show_gallery': True,
                'show_reviews': False,
                'show_location': True,
                'show_contact_cta': True,
            },
            'launch_type': '',
            'selected_pages': [],
            'contact_details': {},
        }

    def _apply_draft_to_suggestions(suggestions, draft, contact_details, style_values):
        if not isinstance(suggestions, dict):
            return suggestions

        draft_hero = draft.get('hero') if isinstance(draft.get('hero'), dict) else {}
        draft_intro = draft.get('intro') if isinstance(draft.get('intro'), dict) else {}
        service_cards = draft.get('service_cards') if isinstance(draft.get('service_cards'), list) else []
        selected_services = [str(item).strip() for item in (draft.get('services') or []) if str(item).strip()]
        main_cta_label = style_values.get('main_cta_label') or draft_hero.get('cta') or 'Request information'

        hero_section = suggestions.setdefault('hero', {})
        if draft_hero.get('title'):
            hero_section['title'] = draft_hero['title']
        if draft_hero.get('description'):
            hero_section['description'] = draft_hero['description']
        hero_section['cta_text'] = main_cta_label

        services_section = suggestions.setdefault('services', {})
        if draft_intro.get('title'):
            services_section['title'] = draft_intro['title']
        if draft_intro.get('text'):
            services_section['intro'] = draft_intro['text']

        for index, service in enumerate(selected_services[:6], start=1):
            services_section[f'item_{index}'] = service
        for index, card in enumerate(service_cards[:6], start=1):
            card_text = str(card.get('text') or '').strip()
            if card_text:
                services_section[f'item_{index}_text'] = card_text

        contact_section = suggestions.setdefault('contact', {})
        contact_section['cta_text'] = main_cta_label
        if contact_details.get('phone') or contact_details.get('whatsapp') or contact_details.get('email'):
            contact_section['primary_contact'] = (
                contact_details.get('phone')
                or contact_details.get('whatsapp')
                or contact_details.get('email')
            )
        if contact_details.get('address') or contact_details.get('service_area_detail') or draft.get('service_area'):
            contact_section['secondary_contact'] = (
                contact_details.get('address')
                or contact_details.get('service_area_detail')
                or draft.get('service_area')
            )

        cta_section = suggestions.setdefault('cta', {})
        cta_section['cta_text'] = main_cta_label
        if draft_hero.get('title'):
            cta_section['title'] = draft_hero['title']

        return suggestions

    def _template_slug_from_style_key(template_key):
        mapping = {
            'classic_local': 'classic_service',
            'visual_showcase': 'visual_hero',
            'service_focused': 'classic_service',
            'simple_landing': 'classic_service',
            'friendly_care': 'gof-canva-layout-test-v1',
            'service_pro': 'classic_service',
        }
        return normalize_template_slug(mapping.get(str(template_key or '').strip(), default_template_slug()))

    def _palette_choice_from_style_key(palette_key):
        mapping = {
            'warm_orange': Site.ColorPalette.ORANGE_BLACK,
            'clean_bw': Site.ColorPalette.BLUE_DARK,
            'soft_beige': Site.ColorPalette.GREEN_NEUTRAL,
            'elegant_dark': Site.ColorPalette.RED_CHARCOAL,
            'fresh_green': Site.ColorPalette.GREEN_NEUTRAL,
            'blue_professional': Site.ColorPalette.BLUE_DARK,
        }
        return mapping.get(str(palette_key or '').strip(), Site.ColorPalette.ORANGE_BLACK)

    def _save_starter_metadata(site, language, state, style_values):
        contact_details = _normalize_contact_details(state.get('contact_details'))
        selected_pages = _sanitize_selected_pages(
            state.get('selected_pages', []),
            default_when_empty=state.get('launch_type') == 'full_website',
        )
        metadata_values = {
            'launch_type': str(state.get('launch_type') or '').strip(),
            'selected_pages': '\n'.join(selected_pages),
            'selected_services': '\n'.join(state.get('services') or []),
            'service_area': str(state.get('service_area') or '').strip(),
            'template_key': style_values['template_key'],
            'template_slug': _template_slug_from_style_key(style_values['template_key']),
            'palette_key': style_values['palette_key'],
            'font_key': style_values['font_key'],
            'image_set_key': style_values['image_set_key'],
            'main_cta_key': style_values['main_cta'],
            'main_cta_label': style_values['main_cta_label'],
            'contact_name': contact_details.get('contact_name', ''),
            'email': contact_details.get('email', ''),
            'phone': contact_details.get('phone', ''),
            'whatsapp': contact_details.get('whatsapp', ''),
            'address': contact_details.get('address', ''),
            'service_area_detail': contact_details.get('service_area_detail', ''),
            'opening_hours': contact_details.get('opening_hours', ''),
            'social_facebook': contact_details.get('social_facebook', ''),
            'social_instagram': contact_details.get('social_instagram', ''),
            'social_linkedin': contact_details.get('social_linkedin', ''),
            'social_tiktok': contact_details.get('social_tiktok', ''),
        }
        for field_key, value in metadata_values.items():
            SiteContent.objects.update_or_create(
                site=site,
                section_key='starter_meta',
                field_key=field_key,
                language=language,
                defaults={'value': value},
            )

    def _create_preview_site_from_state(state, style_values):
        draft = _safe_starter_draft(state.get('starter_draft'))
        template_slug = _template_slug_from_style_key(style_values['template_key'])
        contact_details = _normalize_contact_details(state.get('contact_details'))
        service_area = str(draft.get('service_area') or state.get('service_area') or '').strip()
        selected_services = list(state.get('services') or draft.get('services') or [])

        site = Site.objects.create(
            user=request.user if request.user.is_authenticated else None,
            template_slug=template_slug,
            color_palette=_palette_choice_from_style_key(style_values['palette_key']),
            business_name=str(draft.get('business_name') or state.get('business_name') or '').strip(),
            service_type=str(draft.get('business_type') or state.get('business_type') or '').strip(),
            city=service_area[:120],
        )

        suggestions = build_suggestions(
            business_name=site.business_name,
            service_type=site.service_type,
            city=site.city,
            service_area=service_area,
            selected_services=selected_services,
            service_descriptions=selected_services,
            contact_name=contact_details.get('contact_name'),
            phone=contact_details.get('phone') or contact_details.get('whatsapp'),
            email=contact_details.get('email'),
            address=contact_details.get('address'),
            location=contact_details.get('service_area_detail') or service_area,
            website_goal='starter_page' if state.get('launch_type') == 'starter_page' else 'full_website',
            style_notes=' / '.join(
                bit for bit in [
                    style_values['template_key'],
                    style_values['palette_key'],
                    style_values['font_key'],
                    style_values['image_set_key'],
                ] if bit
            ),
            business_description=draft.get('intro', {}).get('text', ''),
            language=request.LANGUAGE_CODE,
            template_slug=template_slug,
            context_data={
                **state,
                'language': request.LANGUAGE_CODE,
                'template_slug': template_slug,
            },
        )
        suggestions = _apply_draft_to_suggestions(
            suggestions,
            draft,
            contact_details,
            style_values,
        )
        save_site_content(site, request.LANGUAGE_CODE, suggestions)
        ensure_default_site_images(
            site,
            request.LANGUAGE_CODE,
            business_type=site.service_type,
            only_if_missing=True,
            existing_selection=draft.get('hero', {}).get('image_key') or None,
        )
        _save_starter_metadata(site, request.LANGUAGE_CODE, state, style_values)
        return site

    def _create_public_starter_request_from_state(state, style_values):
        draft = _safe_starter_draft(state.get('starter_draft'))
        contact_details = _normalize_contact_details(state.get('contact_details'))
        selected_pages = _sanitize_selected_pages(
            state.get('selected_pages', []),
            default_when_empty=state.get('launch_type') == 'full_website',
        )
        selected_page_labels = _selected_page_labels(selected_pages)
        launch_type_label = launch_type_labels.get(state.get('launch_type'), 'Starter page')
        template_label = next(
            (item['label'] for item in template_options if item['key'] == style_values['template_key']),
            style_values['template_key'],
        )
        palette_label = next(
            (item['label'] for item in palette_options if item['key'] == style_values['palette_key']),
            style_values['palette_key'],
        )
        font_label = next(
            (item['label'] for item in font_options if item['key'] == style_values['font_key']),
            style_values['font_key'],
        )
        image_set_label = next(
            (item['label'] for item in image_set_base_options if item['key'] == style_values['image_set_key']),
            style_values['image_set_key'],
        )
        social_links = '\n'.join(
            line for line in [
                f"Facebook: {contact_details['social_facebook']}" if contact_details.get('social_facebook') else '',
                f"Instagram: {contact_details['social_instagram']}" if contact_details.get('social_instagram') else '',
                f"LinkedIn: {contact_details['social_linkedin']}" if contact_details.get('social_linkedin') else '',
                f"TikTok: {contact_details['social_tiktok']}" if contact_details.get('social_tiktok') else '',
            ]
            if line
        )
        special_requests = '\n'.join(
            line for line in [
                f"Website type: {launch_type_label}",
                f"Selected pages: {', '.join(selected_page_labels) if selected_page_labels else 'Starter page only'}",
                f"Preferred CTA: {style_values['main_cta_label']}",
                f"Starter path: {request.path}",
                'Request source: public starter wizard',
            ]
            if line
        )

        return WebsiteRequest.objects.create(
            source_code='STARTER_PUBLIC',
            normal_price=0,
            offer_price=0,
            status=WebsiteRequest.Status.NEW,
            business_name=str(draft.get('business_name') or state.get('business_name') or '').strip(),
            business_type=str(draft.get('business_type') or state.get('business_type') or '').strip(),
            existing_website_url='',
            current_domain='',
            needs_domain_help=False,
            business_address=contact_details.get('address', ''),
            service_area=contact_details.get('service_area_detail') or str(draft.get('service_area') or state.get('service_area') or '').strip(),
            main_language=request.LANGUAGE_CODE,
            extra_languages='',
            contact_name=contact_details.get('contact_name', ''),
            contact_email=contact_details.get('email', ''),
            contact_phone=contact_details.get('phone', ''),
            contact_whatsapp=contact_details.get('whatsapp', ''),
            main_services='\n'.join(state.get('services') or draft.get('services') or []),
            business_description=draft.get('intro', {}).get('text', ''),
            opening_hours=contact_details.get('opening_hours', ''),
            social_links=social_links,
            preferred_colors=style_values['palette_key'],
            style_notes='\n'.join(
                line for line in [
                    f"Template choice: {template_label}" if template_label else '',
                    f"Palette: {palette_label}" if palette_label else '',
                    f"Font: {font_label}" if font_label else '',
                    f"Image set: {image_set_label}" if image_set_label else '',
                ]
                if line
            ),
            special_requests=special_requests,
        )

    def _parse_request_notes(text):
        parsed = {}
        for raw_line in (text or '').splitlines():
            line = str(raw_line).strip()
            if not line or ':' not in line:
                continue
            key, value = line.split(':', 1)
            parsed[key.strip()] = value.strip()
        return parsed

    def _build_public_starter_request_email_body(website_request):
        request_notes = _parse_request_notes(website_request.special_requests)
        service_lines = [
            line.strip()
            for line in (website_request.main_services or '').splitlines()
            if line.strip()
        ]
        style_lines = [
            line.strip()
            for line in (website_request.style_notes or '').splitlines()
            if line.strip()
        ]
        contact_lines = [
            website_request.contact_name.strip() if website_request.contact_name else '',
            website_request.contact_email.strip() if website_request.contact_email else '',
            f"Phone: {website_request.contact_phone.strip()}" if website_request.contact_phone else '',
            f"WhatsApp: {website_request.contact_whatsapp.strip()}" if website_request.contact_whatsapp else '',
        ]
        admin_url = request.build_absolute_uri(
            reverse('admin:ai_starter_websiterequest_change', args=[website_request.pk])
        )

        return '\n'.join(
            line for line in [
                'New public starter request received.',
                '',
                f"Business name: {website_request.business_name}",
                f"Business type: {website_request.business_type}",
                f"Service area: {website_request.service_area or website_request.business_address or '-'}",
                f"Main language: {website_request.main_language}",
                f"Website type: {request_notes.get('Website type', '-')}",
                f"Selected pages: {request_notes.get('Selected pages', '-')}",
                '',
                'Selected services:',
                *([f"- {item}" for item in service_lines] if service_lines else ['- None provided']),
                '',
                'Contact details:',
                *([f"- {item}" for item in contact_lines if item] or ['- None provided']),
                '',
                'Style summary:',
                *([f"- {item}" for item in style_lines] if style_lines else ['- None provided']),
                '',
                'Special request notes:',
                *([f"- {line}" for line in (website_request.special_requests or '').splitlines() if line.strip()] or ['- None provided']),
                '',
                f'Admin link: {admin_url}',
            ]
            if line is not None
        )

    def _send_public_starter_request_notification(website_request):
        if website_request.source_code != 'STARTER_PUBLIC':
            return False
        if not settings.CONTACT_EMAIL_TO:
            logger.warning(
                'Public starter request %s was created but CONTACT_EMAIL_TO is empty.',
                website_request.public_id,
            )
            return False

        email = EmailMessage(
            subject=f"New public starter request - {website_request.business_name or 'Unnamed business'}",
            body=_build_public_starter_request_email_body(website_request),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.CONTACT_EMAIL_TO],
            reply_to=[website_request.contact_email] if website_request.contact_email else None,
        )
        try:
            sent_count = email.send(fail_silently=False)
        except Exception:
            logger.exception(
                'Could not send public starter request notification for WebsiteRequest %s.',
                website_request.public_id,
            )
            return False
        if not sent_count:
            logger.warning(
                'Email backend reported zero sends for public starter request %s.',
                website_request.public_id,
            )
            return False
        return True

    def _starter_request_summary(website_request):
        if website_request is None:
            return None

        parsed_special_requests = {
            key.strip().lower(): value
            for key, value in _parse_request_notes(website_request.special_requests).items()
        }

        services = [
            line.strip()
            for line in (website_request.main_services or '').splitlines()
            if line.strip()
        ]
        service_area = (
            str(website_request.service_area or '').strip()
            or str(website_request.business_address or '').strip()
        )

        return {
            'business_name': str(website_request.business_name or '').strip(),
            'business_type': str(website_request.business_type or '').strip(),
            'service_area': service_area,
            'services': services,
            'website_type': parsed_special_requests.get('website type', ''),
            'selected_pages': parsed_special_requests.get('selected pages', ''),
            'contact_email': str(website_request.contact_email or '').strip(),
            'contact_phone': str(website_request.contact_phone or website_request.contact_whatsapp or '').strip(),
        }

    def _wizard_steps(current_step):
        definitions = [
            {'number': 1, 'title': 'Business basics'},
            {'number': 2, 'title': 'Style and preview'},
            {'number': 3, 'title': 'Website type'},
            {'number': 4, 'title': 'Pages to include'},
            {'number': 5, 'title': 'Contact/location details'},
            {'number': 6, 'title': 'Review/prepare preview'},
        ]
        for item in definitions:
            item['is_active'] = item['number'] == current_step
            item['is_complete'] = item['number'] < current_step
        return definitions

    state = _load_state()
    wizard_errors = []

    if not _has_starter_draft(state):
        state.update(_default_state())

    style_values = _resolve_style_state(state)
    _apply_style_to_state(state, style_values)

    if request.GET.get('reset') == '1':
        state = _default_state()
        _save_state(state)
        return redirect(_step_url(1))

    if request.method == 'POST':
        wizard_action = (request.POST.get('wizard_action') or '').strip()
        current_step = _safe_step(request.POST.get('current_step') or state.get('step'), default=1)

        if wizard_action == 'create_preview':
            business_name = _normalize_single_line(request.POST.get('business_name'), max_length=120)
            business_type = _normalize_single_line(request.POST.get('business_type'), max_length=120)
            service_area = _normalize_single_line(request.POST.get('service_area'), max_length=120)
            services_text = str(request.POST.get('services_text') or '').strip()
            services = _parse_services_text(services_text)

            if not business_name:
                wizard_errors.append('Business name is required.')
            if not business_type:
                wizard_errors.append('Business type or activity is required.')
            if not service_area:
                wizard_errors.append('City or service area is required.')

            if wizard_errors:
                state.update(
                    {
                        'step': 1,
                        'business_name': business_name,
                        'business_type': business_type,
                        'service_area': service_area,
                        'services_text': services_text,
                        'services': services,
                    }
                )
            else:
                starter_draft = _build_starter_draft(
                    business_name=business_name,
                    business_type=business_type,
                    service_area=service_area,
                    services=services,
                )
                state.update(
                    {
                        'step': 2,
                        'business_name': business_name,
                        'business_type': business_type,
                        'service_area': service_area,
                        'services_text': services_text,
                        'services': services,
                        'starter_draft': starter_draft,
                    }
                )
                style_values = _resolve_style_state(state)
                _apply_style_to_state(state, style_values)
                _save_state(state)
                return redirect(_step_url(2))

        elif wizard_action == 'next':
            if current_step == 2:
                if not _has_starter_draft(state):
                    state = _default_state()
                    _save_state(state)
                    return redirect(_step_url(1))
                style_values = _parse_step2_style_submission(request.POST, state)
                _apply_style_to_state(state, style_values)
                state['step'] = 3
                _save_state(state)
                return redirect(_step_url(3))

            if current_step == 3:
                if not _has_starter_draft(state):
                    state = _default_state()
                    _save_state(state)
                    return redirect(_step_url(1))
                launch_type = str(request.POST.get('launch_type') or '').strip()
                if launch_type not in launch_option_keys:
                    wizard_errors.append('Please choose how you want to launch.')
                    state['step'] = 3
                else:
                    state['launch_type'] = launch_type
                    if isinstance(state.get('starter_draft'), dict):
                        state['starter_draft']['launch_type'] = launch_type
                    if launch_type == 'full_website' and not state.get('selected_pages'):
                        state['selected_pages'] = _sanitize_selected_pages([], default_when_empty=True)
                    state['step'] = 5 if launch_type == 'starter_page' else 4
                    _save_state(state)
                    return redirect(_step_url(state['step']))

            if current_step == 4:
                if not _has_starter_draft(state):
                    state = _default_state()
                    _save_state(state)
                    return redirect(_step_url(1))
                if state.get('launch_type') == 'starter_page':
                    state['step'] = 5
                    _save_state(state)
                    return redirect(_step_url(5))
                if not state.get('launch_type'):
                    state['step'] = 3
                    _save_state(state)
                    return redirect(_step_url(3))

                selected_pages = _sanitize_selected_pages(request.POST.getlist('selected_pages'))
                state['selected_pages'] = selected_pages
                if isinstance(state.get('starter_draft'), dict):
                    state['starter_draft']['selected_pages'] = selected_pages
                state['step'] = 5
                _save_state(state)
                return redirect(_step_url(5))

            if current_step == 5:
                if not _has_starter_draft(state):
                    state = _default_state()
                    _save_state(state)
                    return redirect(_step_url(1))
                if not state.get('launch_type'):
                    state['step'] = 3
                    _save_state(state)
                    return redirect(_step_url(3))

                contact_details = _normalize_contact_details({field: request.POST.get(field, '') for field in contact_detail_fields})
                has_contact_method = bool(contact_details['email'] or contact_details['phone'] or contact_details['whatsapp'])
                if not has_contact_method:
                    wizard_errors.append('Please add at least one contact method: email, phone, or WhatsApp.')
                    state['contact_details'] = contact_details
                    state['step'] = 5
                else:
                    state['contact_details'] = contact_details
                    if isinstance(state.get('starter_draft'), dict):
                        state['starter_draft']['contact_details'] = contact_details
                    state['step'] = 6
                    _save_state(state)
                    return redirect(_step_url(6))

            state['step'] = _safe_step(current_step + 1, default=2)
            _save_state(state)
            return redirect(_step_url(state['step']))
        elif wizard_action == 'previous':
            if current_step == 2:
                state['step'] = 1
                _save_state(state)
                return redirect(_step_url(1))
            if current_step == 3:
                state['step'] = 2
                _save_state(state)
                return redirect(_step_url(2))
            if current_step == 4:
                state['step'] = 3
                _save_state(state)
                return redirect(_step_url(3))
            if current_step == 5:
                state['step'] = 3 if state.get('launch_type') == 'starter_page' else 4
                _save_state(state)
                return redirect(_step_url(state['step']))
            if current_step == 6:
                state['step'] = 5
                _save_state(state)
                return redirect(_step_url(5))
            state['step'] = _safe_step(current_step - 1, default=1)
            _save_state(state)
            return redirect(_step_url(state['step']))
        elif wizard_action == 'prepare_preview':
            if not _has_starter_draft(state):
                state = _default_state()
                _save_state(state)
                return redirect(_step_url(1))
            if not state.get('launch_type'):
                state['step'] = 3
                _save_state(state)
                return redirect(_step_url(3))

            contact_details = _normalize_contact_details(state.get('contact_details'))
            has_contact_method = bool(contact_details['email'] or contact_details['phone'] or contact_details['whatsapp'])
            if not has_contact_method:
                state['step'] = 5
                state['contact_details'] = contact_details
                wizard_errors.append('Please add at least one contact method: email, phone, or WhatsApp.')
                _save_state(state)
                return redirect(_step_url(5))

            if _is_staff_preview_user(request):
                site = _create_preview_site_from_state(state, style_values)
                request.session.pop(STARTER_WIZARD_SESSION_KEY, None)
                request.session.modified = True
                messages.success(
                    request,
                    _('Private preview prepared. Review the generated page and choose the next step from the preview screen.'),
                )
                return redirect('ai_starter:preview', public_id=site.public_id)

            website_request = _create_public_starter_request_from_state(state, style_values)
            _send_public_starter_request_notification(website_request)
            request.session.pop(STARTER_WIZARD_SESSION_KEY, None)
            request.session.modified = True
            success_url = f"{reverse('ai_starter:start')}?submitted={website_request.public_id}"
            return redirect(success_url)
        else:
            state['step'] = _safe_step(current_step, default=1)

    requested_step = _safe_step(request.GET.get('step') or state.get('step'), default=1)
    if requested_step > 1 and not _has_starter_draft(state):
        state = _default_state()
        _save_state(state)
        return redirect(_step_url(1))

    if requested_step == 4 and state.get('launch_type') == 'starter_page':
        state['step'] = 5
        _save_state(state)
        return redirect(_step_url(5))

    if requested_step > 3 and not state.get('launch_type'):
        state['step'] = 3
        _save_state(state)
        return redirect(_step_url(3))

    if requested_step == 4 and state.get('launch_type') == 'full_website' and not state.get('selected_pages'):
        state['selected_pages'] = _sanitize_selected_pages([], default_when_empty=True)
        if isinstance(state.get('starter_draft'), dict):
            state['starter_draft']['selected_pages'] = state['selected_pages']

    state['step'] = requested_step
    style_values = _resolve_style_state(state)
    _apply_style_to_state(state, style_values)
    _save_state(state)

    selected_pages_for_display = []
    if state.get('launch_type') == 'full_website':
        selected_pages_for_display = _sanitize_selected_pages(
            state.get('selected_pages', []),
            default_when_empty=True,
        )
    selected_page_labels = _selected_page_labels(selected_pages_for_display)

    launch_type_label = launch_type_labels.get(state.get('launch_type'), '')
    style_summary = {
        'template': next((item['label'] for item in template_options if item['key'] == style_values['template_key']), style_values['template_key']),
        'palette': next((item['label'] for item in palette_options if item['key'] == style_values['palette_key']), style_values['palette_key']),
        'font': next((item['label'] for item in font_options if item['key'] == style_values['font_key']), style_values['font_key']),
    }

    contact_details = _normalize_contact_details(state.get('contact_details'))
    state['contact_details'] = contact_details

    contact_method_summary = []
    if contact_details.get('email'):
        contact_method_summary.append('Email')
    if contact_details.get('phone'):
        contact_method_summary.append('Phone')
    if contact_details.get('whatsapp'):
        contact_method_summary.append('WhatsApp')

    step4_page_options = []
    selected_page_keys = set(selected_pages_for_display)
    for item in page_options:
        option = dict(item)
        option['selected'] = item['key'] in selected_page_keys
        step4_page_options.append(option)

    image_set_options = [
        {'key': style_values['auto_image_set_key'], 'label': f'Auto selected ({style_values["auto_image_set_key"]})'}
    ]
    image_set_options.extend(image_set_base_options)

    preview_classes = ' '.join(
        [
            f"template-{style_values['template_key']}",
            f"palette-{style_values['palette_key']}",
            f"font-{style_values['font_key']}",
        ]
    )

    return render(
        request,
        'ai_starter/start.html',
        {
            'starter_wizard_v2': True,
            'current_step': requested_step,
            'wizard_steps': _wizard_steps(requested_step),
            'wizard_state': state,
            'starter_draft': _safe_starter_draft(state.get('starter_draft', {})),
            'style_values': style_values,
            'template_options': template_options,
            'palette_options': palette_options,
            'font_options': font_options,
            'image_set_options': image_set_options,
            'cta_options': cta_options,
            'section_visibility': style_values.get('section_visibility', {}),
            'step4_page_options': step4_page_options,
            'selected_page_labels': selected_page_labels,
            'contact_details': contact_details,
            'launch_type_label': launch_type_label,
            'style_summary': style_summary,
            'contact_method_summary': contact_method_summary,
            'section_visibility_keys': section_visibility_keys,
            'launch_type_options': launch_type_options,
            'preview_classes': preview_classes,
            'wizard_errors': wizard_errors,
            'selected_design': selected_design,
            'selected_design_query': selected_design_query,
            'starter_request_submitted': submitted_request,
            'starter_request_summary': _starter_request_summary(submitted_request),
            'is_public_start_flow': not _is_staff_preview_user(request),
            'force_indexable': True,
            'site_noindex': False,
        },
    )


@require_http_methods(['GET', 'POST'])
def meeting_offer_request(request):
    _raise_public_preview_unavailable(request)
    submitted_request_id = request.GET.get('submitted', '').strip()
    submitted_request = None
    if submitted_request_id:
        submitted_request = WebsiteRequest.objects.filter(public_id=submitted_request_id).first()

    if request.method == 'POST':
        form = WebsiteRequestForm(request.POST, request.FILES)
        if form.is_valid():
            website_request = WebsiteRequest.objects.create(
                source_code=MEETING_OFFER_SOURCE,
                normal_price=MEETING_NORMAL_PRICE,
                offer_price=MEETING_OFFER_PRICE,
                status=WebsiteRequest.Status.NEW,
                business_name=form.cleaned_data['business_name'],
                business_type=form.cleaned_data['business_type'],
                existing_website_url=form.cleaned_data['existing_website_url'],
                current_domain=form.cleaned_data['current_domain'],
                needs_domain_help=form.cleaned_data['needs_domain_help'],
                business_address=form.cleaned_data['business_address'],
                service_area=form.cleaned_data['service_area'],
                main_language=form.cleaned_data['main_language'],
                extra_languages=form.cleaned_data['extra_languages'],
                contact_name=form.cleaned_data['contact_name'],
                contact_email=form.cleaned_data['contact_email'],
                contact_phone=form.cleaned_data['contact_phone'],
                contact_whatsapp=form.cleaned_data['contact_whatsapp'],
                main_services=form.cleaned_data['main_services'],
                business_description=form.cleaned_data['business_description'],
                opening_hours=form.cleaned_data['opening_hours'],
                social_links=form.cleaned_data['social_links'],
                preferred_colors=form.cleaned_data['preferred_colors'],
                style_notes=form.cleaned_data['style_notes'],
                special_requests=form.cleaned_data['special_requests'],
            )

            for upload in form.cleaned_data['supporting_files']:
                WebsiteRequestFile.objects.create(
                    website_request=website_request,
                    file=upload,
                    original_name=upload.name,
                )

            email = EmailMessage(
                subject='New website request - GEMEENTE50',
                body=_build_request_email_body(website_request),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.CONTACT_EMAIL_TO],
                reply_to=[website_request.contact_email],
            )
            email.send(fail_silently=False)

            success_url = f'{reverse("ai_starter:meeting_offer")}?submitted={website_request.public_id}'
            return redirect(success_url)

        return render(
            request,
            'ai_starter/start.html',
            _meeting_offer_context(form),
            status=400,
        )

    return render(
        request,
        'ai_starter/start.html',
        _meeting_offer_context(WebsiteRequestForm(), submitted_request),
    )


@require_http_methods(['GET', 'POST'])
def preview(request, public_id):
    _raise_public_preview_unavailable(request)
    ensure_default_templates()
    site = get_object_or_404(Site, public_id=public_id)
    language = request.LANGUAGE_CODE
    ensure_language_content(site, language)
    handoff = SiteHandoff.objects.filter(site=site, target_system='wordpress_jcw').first()
    active_template_slug = normalize_template_slug(site.template_slug)
    starter_launch_type_content = site.contents.filter(
        section_key='starter_meta',
        field_key='launch_type',
        language=language,
    ).first() or site.contents.filter(
        section_key='starter_meta',
        field_key='launch_type',
    ).first()
    starter_selected_pages_content = site.contents.filter(
        section_key='starter_meta',
        field_key='selected_pages',
        language=language,
    ).first() or site.contents.filter(
        section_key='starter_meta',
        field_key='selected_pages',
    ).first()
    starter_launch_type = str(starter_launch_type_content.value).strip() if starter_launch_type_content else ''
    starter_selected_pages = [
        item.strip()
        for item in str(starter_selected_pages_content.value or '').splitlines()
        if item.strip()
    ] if starter_selected_pages_content else []
    selected_hero_image = site.contents.filter(
        section_key='hero',
        field_key='hero_image',
        language=language,
    ).first() or site.contents.filter(
        section_key='hero',
        field_key='hero_image',
    ).first()
    preserved_hero_image_key = selected_hero_image.value if selected_hero_image else ''

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'apply_template':
            selected_template = normalize_template_slug(request.POST.get('template_slug', '').strip())
            if selected_template:
                site.template_slug = selected_template
                site.save(update_fields=['template_slug', 'updated_at'])
                site.contents.all().delete()
                save_site_content(
                    site,
                    language,
                    build_suggestions(
                        business_name=site.business_name,
                        service_type=site.service_type,
                        city=site.city,
                        template_slug=site.template_slug,
                        language=language,
                    ),
                )
                ensure_default_site_images(
                    site,
                    language,
                    business_type=site.service_type,
                    only_if_missing=False,
                    existing_selection=(
                        preserved_hero_image_key
                        if preserved_hero_image_key and preserved_hero_image_key != 'generic_service_01'
                        else None
                    ),
                    refresh_generic_existing=True,
                )
        elif action == 'apply_palette':
            selected_palette = request.POST.get('color_palette', '').strip()
            valid_palettes = {choice for choice, _label in Site.ColorPalette.choices}
            if selected_palette in valid_palettes:
                site.color_palette = selected_palette
                site.save(update_fields=['color_palette', 'updated_at'])
        elif action == 'regenerate':
            save_site_content(
                site,
                language,
                build_suggestions(
                    business_name=site.business_name,
                    service_type=site.service_type,
                    city=site.city,
                    template_slug=site.template_slug,
                    variant_index=next_suggestion_variant(site, language),
                    language=language,
                ),
            )
            ensure_default_site_images(
                site,
                language,
                business_type=site.service_type,
                only_if_missing=True,
                refresh_generic_existing=True,
            )
        elif action == 'regenerate_hero_image':
            staff_guard = _require_staff_user(request)
            if staff_guard:
                return staff_guard

            alternate_image = get_alternate_image_for_business_type(
                site.service_type,
                current_key=preserved_hero_image_key,
            )
            ensure_default_site_images(
                site,
                language,
                business_type=site.service_type,
                only_if_missing=False,
                existing_selection=alternate_image['key'],
            )
            if alternate_image['key'] == preserved_hero_image_key:
                messages.warning(
                    request,
                    _('No distinct alternate hero photo is currently available for this category.'),
                )
            else:
                messages.success(
                    request,
                    _('Hero image suggestion updated from the built-in photo library.'),
                )
        else:
            for content in site.contents.filter(language=language):
                posted_value = request.POST.get(f'content__{content.id}')
                if posted_value is not None:
                    content.value = posted_value
                    content.save(update_fields=['value', 'updated_at'])
        return redirect('ai_starter:preview', public_id=site.public_id)

    return render(
        request,
        'ai_starter/preview.html',
        {
            'site': site,
            'site_slug': site_slug(site),
            'editor_sections': build_editor_sections(site, language),
            'template_options': available_template_options(),
            'active_template_slug': active_template_slug,
            'active_template_card': get_template_card(active_template_slug),
            'active_layout_class': get_template_layout_class(active_template_slug),
            'palette_options': available_palette_options(),
            'wordpress_handoff': handoff,
            'wordpress_handoff_admin_url': _site_handoff_admin_url(handoff),
            'wordpress_handoff_ai_brief_ready': bool(handoff and handoff.staff_ai_brief),
            'starter_launch_type': starter_launch_type,
            'starter_selected_pages': starter_selected_pages,
        },
    )


@require_http_methods(['POST'])
def prepare_wordpress_handoff(request, public_id):
    staff_guard = _require_staff_user(request)
    if staff_guard:
        return staff_guard

    site = get_object_or_404(Site, public_id=public_id)
    handoff, _created = SiteHandoff.objects.get_or_create(
        site=site,
        target_system='wordpress_jcw',
    )
    handoff.status = SiteHandoff.Status.PREPARED
    handoff.prepared_by = request.user
    handoff.save(update_fields=['status', 'prepared_by', 'updated_at'])
    handoff.refresh_payload()

    messages.success(
        request,
        _('WordPress handoff payload prepared. This updates Django only and does not change WordPress.'),
    )
    return redirect('ai_starter:preview', public_id=site.public_id)


@require_http_methods(['GET', 'POST'])
def staff_handoffs(request):
    staff_guard = _require_staff_user(request)
    if staff_guard:
        return staff_guard

    allowed_status_filters = {
        'prepared': SiteHandoff.Status.PREPARED,
        'completed': SiteHandoff.Status.COMPLETED,
        'failed': SiteHandoff.Status.FAILED,
    }
    selected_status = (request.GET.get('status') or '').strip().lower()

    if request.method == 'POST':
        handoff_id = request.POST.get('handoff_id', '').strip()
        action = request.POST.get('action', '').strip()

        handoff = get_object_or_404(
            SiteHandoff.objects.select_related('site', 'website_request', 'prepared_by'),
            pk=handoff_id,
        )

        try:
            if action == 'prepare_refresh_handoff':
                handoff.status = SiteHandoff.Status.PREPARED
                handoff.save(update_fields=['status', 'updated_at'])
                handoff.refresh_payload()
                messages.success(
                    request,
                    _('Handoff payload refreshed for %(business)s. Django only; WordPress unchanged.') % {
                        'business': handoff.site.business_name,
                    },
                )
            elif action == 'generate_ai_brief':
                handoff.generate_staff_ai_brief()
                messages.success(
                    request,
                    _('Staff AI handoff brief generated for %(business)s.') % {
                        'business': handoff.site.business_name,
                    },
                )
            elif action == 'mark_completed':
                handoff.mark_completed()
                messages.success(
                    request,
                    _('Marked handoff as completed for %(business)s.') % {
                        'business': handoff.site.business_name,
                    },
                )
            else:
                messages.error(request, _('Unknown handoff action.'))
        except Exception as exc:
            messages.error(
                request,
                _('Could not process handoff for %(business)s: %(error)s') % {
                    'business': handoff.site.business_name,
                    'error': str(exc),
                },
            )

        redirect_url = reverse('ai_starter:staff_handoffs')
        if selected_status in allowed_status_filters:
            redirect_url = f'{redirect_url}?status={selected_status}'
        return redirect(redirect_url)

    handoffs = SiteHandoff.objects.select_related('site', 'website_request', 'prepared_by').order_by('-updated_at', '-created_at')
    if selected_status in allowed_status_filters:
        handoffs = handoffs.filter(status=allowed_status_filters[selected_status])

    handoff_rows = []
    for handoff in handoffs:
        handoff_rows.append(
            {
                'handoff': handoff,
                'content_row_count': _handoff_content_row_count(handoff),
                'request_summary': _handoff_request_summary(handoff),
                'admin_url': _site_handoff_admin_url(handoff),
            }
        )

    filter_tabs = [
        {'label': _('All'), 'value': '', 'active': selected_status == '', 'url': reverse('ai_starter:staff_handoffs')},
        {'label': _('Prepared'), 'value': 'prepared', 'active': selected_status == 'prepared', 'url': f"{reverse('ai_starter:staff_handoffs')}?status=prepared"},
        {'label': _('Completed'), 'value': 'completed', 'active': selected_status == 'completed', 'url': f"{reverse('ai_starter:staff_handoffs')}?status=completed"},
        {'label': _('Failed'), 'value': 'failed', 'active': selected_status == 'failed', 'url': f"{reverse('ai_starter:staff_handoffs')}?status=failed"},
    ]

    return render(
        request,
        'ai_starter/staff_handoffs.html',
        {
            'handoff_rows': handoff_rows,
            'selected_status': selected_status,
            'filter_tabs': filter_tabs,
        },
    )


@require_http_methods(['GET', 'POST'])
def staff_assistant(request):
    staff_guard = _require_staff_user(request)
    if staff_guard:
        return staff_guard

    selected_handoff = None
    drafted_reply = ''
    customer_message = ''
    reply_language = 'Portuguese'
    reply_tone = 'friendly_professional'

    if request.method == 'POST':
        handoff_id = (request.POST.get('handoff_id') or '').strip()
        customer_message = clean_assistant_output((request.POST.get('customer_message') or '').strip())
        reply_language = (request.POST.get('reply_language') or 'Portuguese').strip() or 'Portuguese'
        reply_tone = (request.POST.get('reply_tone') or 'friendly_professional').strip() or 'friendly_professional'

        if handoff_id:
            selected_handoff = SiteHandoff.objects.select_related('site', 'website_request', 'prepared_by').filter(pk=handoff_id).first()

        if not customer_message:
            messages.error(request, _('Customer message is required.'))
        else:
            try:
                drafted_reply = draft_customer_reply(
                    customer_message,
                    handoff=selected_handoff,
                    reply_language=reply_language,
                    reply_tone=reply_tone,
                )
                messages.success(request, _('Customer reply draft generated. Nothing was sent automatically.'))
            except Exception as exc:
                messages.error(
                    request,
                    _('Could not draft a customer reply: %(error)s') % {'error': str(exc)},
                )
    else:
        handoff_id = (request.GET.get('handoff_id') or '').strip()
        if handoff_id:
            selected_handoff = SiteHandoff.objects.select_related('site', 'website_request', 'prepared_by').filter(pk=handoff_id).first()

    context = _build_staff_assistant_context(selected_handoff)
    context.update(
        {
            'customer_message': customer_message,
            'reply_language': reply_language,
            'reply_tone': reply_tone,
            'drafted_reply': drafted_reply,
            'drafted_reply_sections': _parse_assistant_sections(drafted_reply) if drafted_reply else {},
            'recommended_setup': infer_recommended_website_setup(customer_message, selected_handoff) if customer_message else None,
        }
    )
    return render(request, 'ai_starter/staff_assistant.html', context)


@require_http_methods(['GET'])
def staff_template_wireframes(request):
    staff_guard = _require_staff_user(request)
    if staff_guard:
        return staff_guard

    return render(
        request,
        'ai_starter/staff_template_wireframes.html',
        {
            'wireframe_layouts': _template_wireframe_layouts(),
            'wireframe_variants': _template_wireframe_variants(),
        },
    )


@xframe_options_sameorigin
def preview_frame(request, public_id):
    _raise_public_preview_unavailable(request)
    ensure_default_templates()
    site = get_object_or_404(Site, public_id=public_id)
    language = request.LANGUAGE_CODE
    ensure_language_content(site, language)
    return render(
        request,
        'ai_starter/frame.html',
        {
            'site': site,
            'site_slug': site_slug(site),
            'render_sections': build_render_sections(site, language),
            'preview_template_class': get_template_preview_class(site.template_slug),
            'preview_layout_class': get_template_layout_class(site.template_slug),
            'preview_template_slug': normalize_template_slug(site.template_slug),
            **_floating_contact_context(site),
        },
    )


@require_http_methods(['GET'])
def template_preview(request, template_slug):
    access_guard = _require_staff_or_debug(request)
    if access_guard:
        return access_guard

    ensure_default_templates()
    language = request.LANGUAGE_CODE
    site = _build_direct_template_preview_site(template_slug, language)
    return render(
        request,
        'ai_starter/frame.html',
        {
            'site': site,
            'site_slug': site_slug(site),
            'render_sections': build_render_sections(site, language),
            'preview_template_class': get_template_preview_class(site.template_slug),
            'preview_layout_class': get_template_layout_class(site.template_slug),
            'preview_template_slug': normalize_template_slug(site.template_slug),
            'template_preview_mode': True,
            **_floating_contact_context(site),
        },
    )
