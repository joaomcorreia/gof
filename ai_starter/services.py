import logging

from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static

from .models import SiteContent, Template
from .image_catalog import (
    get_default_image_for_business_type,
    get_image_by_key,
    get_image_choices,
    get_image_choices_for_business_type,
    is_generic_placeholder_image_key,
    resolve_business_images,
)
from .services_context import build_business_context
from .template_catalog import (
    available_template_cards,
    infer_starter_template_slug,
    get_template_card,
    get_template_layout,
    get_template_section_layout,
    normalize_template_slug,
)


logger = logging.getLogger(__name__)

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
            {'key': 'secondary_cta_text', 'label': _('Secondary CTA text')},
            {'key': 'hero_image', 'label': _('Hero image'), 'input_type': 'select', 'choices': 'hero_image_choices'},
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
            {'key': 'secondary_cta_text', 'label': _('Secondary CTA text')},
            {'key': 'hero_image', 'label': _('Hero image'), 'input_type': 'select', 'choices': 'hero_image_choices'},
        ],
    },
    'story_split': {
        'label': _('About section'),
        'template': 'ai_starter/sections/story_split.html',
        'fields': [
            {'key': 'kicker', 'label': _('Eyebrow')},
            {'key': 'title', 'label': _('Title')},
            {'key': 'description', 'label': _('Description')},
            {'key': 'support_title', 'label': _('Support title')},
            {'key': 'support_text', 'label': _('Support text')},
            {'key': 'point_1', 'label': _('Point 1')},
            {'key': 'point_2', 'label': _('Point 2')},
        ],
    },
    'offer_grid': {
        'label': _('Services section'),
        'template': 'ai_starter/sections/offer_grid.html',
        'fields': [
            {'key': 'kicker', 'label': _('Eyebrow')},
            {'key': 'title', 'label': _('Section title')},
            {'key': 'intro', 'label': _('Intro text')},
            {'key': 'item_1', 'label': _('Item 1')},
            {'key': 'item_1_text', 'label': _('Item 1 text')},
            {'key': 'item_2', 'label': _('Item 2')},
            {'key': 'item_2_text', 'label': _('Item 2 text')},
            {'key': 'item_3', 'label': _('Item 3')},
            {'key': 'item_3_text', 'label': _('Item 3 text')},
            {'key': 'item_4', 'label': _('Item 4')},
            {'key': 'item_4_text', 'label': _('Item 4 text')},
            {'key': 'item_5', 'label': _('Item 5')},
            {'key': 'item_5_text', 'label': _('Item 5 text')},
            {'key': 'item_6', 'label': _('Item 6')},
            {'key': 'item_6_text', 'label': _('Item 6 text')},
        ],
    },
    'showcase_grid': {
        'label': _('Portfolio section'),
        'template': 'ai_starter/sections/showcase_grid.html',
        'fields': [
            {'key': 'kicker', 'label': _('Eyebrow')},
            {'key': 'title', 'label': _('Section title')},
            {'key': 'intro', 'label': _('Intro text')},
            {'key': 'card_1_title', 'label': _('Card 1 title')},
            {'key': 'card_1_text', 'label': _('Card 1 text')},
            {'key': 'card_2_title', 'label': _('Card 2 title')},
            {'key': 'card_2_text', 'label': _('Card 2 text')},
            {'key': 'card_3_title', 'label': _('Card 3 title')},
            {'key': 'card_3_text', 'label': _('Card 3 text')},
            {'key': 'card_4_title', 'label': _('Card 4 title')},
            {'key': 'card_4_text', 'label': _('Card 4 text')},
        ],
    },
    'steps': {
        'label': _('Process section'),
        'template': 'ai_starter/sections/steps.html',
        'fields': [
            {'key': 'kicker', 'label': _('Eyebrow')},
            {'key': 'title', 'label': _('Section title')},
            {'key': 'intro', 'label': _('Intro text')},
            {'key': 'step_1_title', 'label': _('Step 1 title')},
            {'key': 'step_1_text', 'label': _('Step 1 text')},
            {'key': 'step_2_title', 'label': _('Step 2 title')},
            {'key': 'step_2_text', 'label': _('Step 2 text')},
            {'key': 'step_3_title', 'label': _('Step 3 title')},
            {'key': 'step_3_text', 'label': _('Step 3 text')},
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
            {'key': 'kicker', 'label': _('Eyebrow')},
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
    'contact_details': {
        'label': _('Contact section'),
        'template': 'ai_starter/sections/contact_details.html',
        'fields': [
            {'key': 'kicker', 'label': _('Eyebrow')},
            {'key': 'title', 'label': _('Section title')},
            {'key': 'description', 'label': _('Description')},
            {'key': 'detail_1_label', 'label': _('Detail 1 label')},
            {'key': 'detail_1_value', 'label': _('Detail 1 value')},
            {'key': 'detail_2_label', 'label': _('Detail 2 label')},
            {'key': 'detail_2_value', 'label': _('Detail 2 value')},
            {'key': 'detail_3_label', 'label': _('Detail 3 label')},
            {'key': 'detail_3_value', 'label': _('Detail 3 value')},
            {'key': 'detail_4_label', 'label': _('Detail 4 label')},
            {'key': 'detail_4_value', 'label': _('Detail 4 value')},
            {'key': 'cta_text', 'label': _('CTA text')},
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
    'footer_columns': {
        'label': _('Footer section'),
        'template': 'ai_starter/sections/footer_columns.html',
        'fields': [
            {'key': 'business_name', 'label': _('Business name')},
            {'key': 'description', 'label': _('Description')},
            {'key': 'contact_line', 'label': _('Contact line')},
            {'key': 'nav_title', 'label': _('Navigation title')},
            {'key': 'nav_item_1', 'label': _('Navigation item 1')},
            {'key': 'nav_item_2', 'label': _('Navigation item 2')},
            {'key': 'nav_item_3', 'label': _('Navigation item 3')},
            {'key': 'services_title', 'label': _('Services title')},
            {'key': 'services_item_1', 'label': _('Services item 1')},
            {'key': 'services_item_2', 'label': _('Services item 2')},
            {'key': 'services_item_3', 'label': _('Services item 3')},
            {'key': 'contact_title', 'label': _('Contact title')},
            {'key': 'contact_item_1', 'label': _('Contact item 1')},
            {'key': 'contact_item_2', 'label': _('Contact item 2')},
            {'key': 'contact_item_3', 'label': _('Contact item 3')},
            {'key': 'legal_title', 'label': _('Legal title')},
            {'key': 'legal_item_1', 'label': _('Legal item 1')},
            {'key': 'legal_item_2', 'label': _('Legal item 2')},
            {'key': 'legal_item_3', 'label': _('Legal item 3')},
            {'key': 'copyright_line', 'label': _('Copyright line')},
            {'key': 'platform_note', 'label': _('Platform note')},
        ],
    },
}

EDITOR_FIELD_CHOICE_SETS = {
    'hero_image_choices': get_image_choices(),
}

SUGGESTION_VARIANTS = 3

ONBOARDING_PROFILE_FALLBACK = {
    'hero_title': _('Professional website preview for your business'),
    'hero_description': _(
        'A clear starting website with your services, contact details, and next steps ready to review.'
    ),
    'hero_cta': _('Request information'),
    'intro_title': _('A simple introduction section'),
    'intro_text': _(
        'Use this section to explain what your business does, who you help, and why customers should contact you.'
    ),
    'intro_variants': [
        {
            'title': _('A simple introduction section'),
            'text': _(
                'Use this section to explain what your business does, who you help, and why customers should contact you.'
            ),
        },
        {
            'title': _('A clearer introduction'),
            'text': _(
                'Help visitors understand your services quickly with a short introduction that can be refined after activation.'
            ),
        },
        {
            'title': _('A stronger first explanation'),
            'text': _(
                'Give customers a clearer idea of what you offer, how you work, and what they should do next.'
            ),
        },
    ],
    'services': [
        _('Main service'),
        _('Popular option'),
        _('Customer support'),
    ],
}

ONBOARDING_SERVICE_PROFILES = [
    {
        'key': 'makeup_artist',
        'match_terms': ['makeup artist', 'makeup', 'make-up', 'mua', 'bridal makeup'],
        'hero_title': _('Makeup for special moments'),
        'hero_description': _(
            'Professional makeup services for weddings, events, photoshoots, and personal appointments.'
        ),
        'hero_cta': _('Request appointment'),
        'intro_title': _('A polished first impression'),
        'intro_text': _(
            'Create a confident look for weddings, events, photoshoots, or personal appointments with makeup tailored to your style and occasion.'
        ),
        'intro_variants': [
            {
                'title': _('A polished first impression'),
                'text': _(
                    'Create a confident look for weddings, events, photoshoots, or personal appointments with makeup tailored to your style and occasion.'
                ),
            },
            {
                'title': _('Makeup tailored to your occasion'),
                'text': _(
                    'From bridal makeup to photoshoots and events, your preview can show customers how your services help them feel prepared and confident.'
                ),
            },
            {
                'title': _('Feel ready for every moment'),
                'text': _(
                    'Show visitors your makeup services, style, and appointment options with a clear intro section that can be completed after activation.'
                ),
            },
        ],
        'services': [
            _('Bridal makeup'),
            _('Event makeup'),
            _('Photoshoot makeup'),
            _('Evening makeup'),
            _('Natural makeup'),
            _('Makeup trial'),
        ],
    },
    {
        'key': 'garage',
        'match_terms': ['garage', 'mechanic', 'car repair', 'auto repair', 'workshop', 'automotive'],
        'hero_title': _('Auto repair website preview'),
        'hero_description': _(
            'Present repairs, diagnostics, maintenance and APK/MOT support in one clear starter page for local drivers.'
        ),
        'hero_cta': _('Request a repair quote'),
        'intro_title': _('Explain your workshop clearly'),
        'intro_text': _(
            'Show the services you handle, the vehicles you work on, and how customers can contact you quickly.'
        ),
        'intro_variants': [
            {
                'title': _('Explain your workshop clearly'),
                'text': _(
                    'Show the services you handle, the vehicles you work on, and how customers can contact you quickly.'
                ),
            },
            {
                'title': _('Help drivers understand your services'),
                'text': _(
                    'Use the intro to explain repairs, diagnostics, and maintenance in a way that makes it easy to ask for help.'
                ),
            },
            {
                'title': _('A stronger garage introduction'),
                'text': _(
                    'Give visitors a clearer overview of your repair services, vehicle support, and the best way to contact your workshop.'
                ),
            },
        ],
        'services': [
            _('Diagnostics'),
            _('Maintenance'),
            _('Brake service'),
            _('MOT preparation'),
            _('Engine repair'),
            _('Tyre service'),
        ],
    },
    {
        'key': 'taxi',
        'match_terms': ['taxi', 'cab', 'airport transfer', 'airport transfers'],
        'hero_title': _('Taxi website preview'),
        'hero_description': _(
            'Show local rides, airport transfers and booking details in one simple starter page.'
        ),
        'hero_cta': _('Request a ride'),
        'intro_title': _('Show your ride options clearly'),
        'intro_text': _(
            'Use this section to present local rides, airport transfers, and how passengers can book quickly.'
        ),
        'services': [
            _('Local taxi rides'),
            _('Airport transfers'),
            _('Business and appointment transport'),
            _('Scheduled pickups'),
            _('Station and hotel transfers'),
            _('Ride booking requests'),
        ],
    },
    {
        'key': 'painter',
        'match_terms': ['painter', 'painting', 'paint', 'decorating'],
        'hero_title': _('Painting business website preview'),
        'hero_description': _(
            'Present interior painting, exterior painting, wall repairs and quote requests in one clear starter page.'
        ),
        'hero_cta': _('Request a painting quote'),
        'intro_title': _('Present painting jobs with confidence'),
        'intro_text': _(
            'Use this section to explain interior and exterior jobs, surface preparation, and how customers can request a quote.'
        ),
        'services': [
            _('Interior painting'),
            _('Exterior painting'),
            _('Walls, ceilings and repairs'),
            _('Surface preparation'),
            _('Trim and detail painting'),
            _('Painting quote requests'),
        ],
    },
    {
        'key': 'bakery',
        'match_terms': ['bakery', 'bread', 'pastry', 'pastries', 'patisserie'],
        'hero_title': _('Bakery website preview'),
        'hero_description': _(
            'Show fresh bread, pastries, cakes, opening hours and order/contact options in one simple starter page.'
        ),
        'hero_cta': _('View bakery options'),
        'intro_title': _('Show your bakery offer clearly'),
        'intro_text': _(
            'Use this section to present daily products, custom cake orders, and how customers can contact or order.'
        ),
        'services': [
            _('Fresh bread and pastries'),
            _('Cakes and custom orders'),
            _('Local pickup or daily specials'),
            _('Seasonal products'),
            _('Coffee and bakery combos'),
            _('Order and contact options'),
        ],
    },
    {
        'key': 'construction',
        'match_terms': ['construction', 'builder', 'renovation', 'contractor', 'handyman'],
        'hero_title': _('Construction and renovation work you can trust'),
        'hero_description': _(
            'Present your building services clearly, from smaller repairs to full renovation projects.'
        ),
        'hero_cta': _('Request a project quote'),
        'intro_title': _('Show your work with confidence'),
        'intro_text': _(
            'Use the intro section to explain what you build, the types of customers you help, and how enquiries should reach you.'
        ),
        'services': [
            _('Renovation work'),
            _('Interior finishing'),
            _('Extensions'),
            _('Repairs'),
            _('Maintenance'),
            _('Project estimates'),
        ],
    },
    {
        'key': 'cleaning',
        'match_terms': ['cleaning', 'cleaner', 'housekeeping', 'office cleaning'],
        'hero_title': _('Cleaning services for homes and businesses'),
        'hero_description': _(
            'A practical website draft for regular cleaning, deep cleaning, and quote requests.'
        ),
        'hero_cta': _('Request cleaning help'),
        'intro_title': _('Make your services easy to scan'),
        'intro_text': _(
            'Explain the spaces you clean, the packages you offer, and the areas where customers can book you.'
        ),
        'services': [
            _('Home cleaning'),
            _('Office cleaning'),
            _('Deep cleaning'),
            _('Move-in cleaning'),
            _('Weekly service'),
            _('Quote request'),
        ],
    },
    {
        'key': 'restaurant',
        'match_terms': ['restaurant', 'cafe', 'food', 'takeaway', 'pizza', 'bar'],
        'hero_title': _('A clear website for your menu and bookings'),
        'hero_description': _(
            'Help visitors discover your food, location, opening hours, and the best way to order or reserve.'
        ),
        'hero_cta': _('View menu and contact'),
        'intro_title': _('Show the experience clearly'),
        'intro_text': _(
            'Use this block to describe your food, your atmosphere, and how customers should visit, book, or order.'
        ),
        'services': [
            _('Dine-in service'),
            _('Takeaway orders'),
            _('Reservations'),
            _('Menu highlights'),
            _('Private events'),
            _('Opening hours'),
        ],
    },
    {
        'key': 'beauty',
        'match_terms': ['beauty', 'salon', 'nails', 'lashes', 'facial', 'spa'],
        'hero_title': _('Beauty salon website preview'),
        'hero_description': _(
            'Present treatments, appointments, salon details and booking options in one clear starter page.'
        ),
        'hero_cta': _('Book an appointment'),
        'intro_title': _('Help visitors trust your service'),
        'intro_text': _(
            'Use the intro to explain your treatments, your style, and how new clients can ask about availability.'
        ),
        'services': [
            _('Facial treatments'),
            _('Nail care'),
            _('Lash styling'),
            _('Waxing'),
            _('Skin consultation'),
            _('Beauty packages'),
        ],
    },
    {
        'key': 'shop',
        'match_terms': ['shop', 'store', 'retail', 'boutique', 'catalog', 'product'],
        'hero_title': _('Show your products clearly online'),
        'hero_description': _(
            'Start with a practical website structure for products, categories, and customer enquiries or sales.'
        ),
        'hero_cta': _('Explore products'),
        'intro_title': _('A better product starting point'),
        'intro_text': _(
            'Use the intro to explain what you sell, highlight key product categories, and guide visitors to the right next step.'
        ),
        'services': [
            _('Featured products'),
            _('Product categories'),
            _('New arrivals'),
            _('Special orders'),
            _('Customer enquiries'),
            _('Online sales later'),
        ],
    },
    {
        'key': 'printing',
        'match_terms': ['printing', 'signage', 'print shop', 'graphic print', 'banners'],
        'hero_title': _('Printing and signage made easier to request'),
        'hero_description': _(
            'Help customers understand your print services, order options, and quote process.'
        ),
        'hero_cta': _('Request a print quote'),
        'intro_title': _('Guide visitors to the right print service'),
        'intro_text': _(
            'Use this section to explain the print work you handle and what customers should send before requesting a quote.'
        ),
        'services': [
            _('Business cards'),
            _('Flyers and leaflets'),
            _('Posters and banners'),
            _('Signs and stickers'),
            _('Vehicle graphics'),
            _('Print quotes'),
        ],
    },
    {
        'key': 'transport',
        'match_terms': ['transport', 'taxi', 'delivery', 'courier', 'logistics'],
        'hero_title': _('Transport services with clear booking paths'),
        'hero_description': _(
            'Present your transport, delivery, or passenger services so customers know what you do and how to book.'
        ),
        'hero_cta': _('Request transport'),
        'intro_title': _('Make your routes and service clear'),
        'intro_text': _(
            'Use the intro to explain where you operate, what you transport, and how people should contact you.'
        ),
        'services': [
            _('Local transport'),
            _('Airport transfers'),
            _('Courier service'),
            _('Scheduled rides'),
            _('Business transport'),
            _('Booking requests'),
        ],
    },
]

BUSINESS_FAMILY_RULES = [
    {
        'family': 'shop_catalog',
        'keywords': [
            'shop', 'store', 'products', 'product', 'catalog', 'catalogue', 'ecommerce',
            'e-commerce', 'parts', 'accessories', 'electronics', 'technology', 'computer',
            'laptop', 'phone', 'gadgets', 'supplies',
        ],
        'recommended_template_slug': 'card_grid',
        'hero_title': _('Technology products and computer parts'),
        'hero_description': _(
            'Browse computer parts, accessories, electronics, and tech products with a clear way to request information or order.'
        ),
        'hero_cta': _('View products'),
        'intro_title': _('Products organised clearly'),
        'intro_text': _(
            'Help visitors browse categories, compare products, and ask for information with a clearer catalog-style introduction.'
        ),
        'services': [
            _('Computer parts'),
            _('Laptop accessories'),
            _('Phone accessories'),
            _('Cables and chargers'),
            _('Components'),
            _('Repairs and support'),
            _('Gaming accessories'),
            _('Tech products'),
        ],
        'intro_variants': [
            {
                'title': _('Products organised clearly'),
                'text': _(
                    'Help visitors browse categories, compare products, and ask for information with a clearer catalog-style introduction.'
                ),
            },
            {
                'title': _('A better technology catalog start'),
                'text': _(
                    'Show computer parts, accessories, and related products in a way that makes it easier to browse and ask questions.'
                ),
            },
            {
                'title': _('Clear product sections for visitors'),
                'text': _(
                    'Use a practical website structure so visitors can discover products, categories, and next steps without confusion.'
                ),
            },
        ],
    },
    {
        'family': 'construction_trades',
        'keywords': [
            'construction', 'renovation', 'building', 'roofing', 'contractor', 'handyman',
            'carpenter', 'electrician', 'plumber',
        ],
        'recommended_template_slug': 'classic_service',
    },
    {
        'family': 'food_restaurant',
        'keywords': ['restaurant', 'cafe', 'bakery', 'takeaway', 'pizza', 'food', 'catering', 'bar'],
        'recommended_template_slug': 'visual_hero',
    },
    {
        'family': 'beauty_wellness',
        'keywords': ['beauty', 'makeup', 'hair', 'nails', 'spa', 'massage', 'wellness', 'salon', 'barber'],
        'recommended_template_slug': 'visual_hero',
    },
    {
        'family': 'friendly_care',
        'keywords': ['babysitter', 'baby sitter', 'child care', 'childcare', 'kids', 'children', 'daycare', 'day care', 'tutor', 'tutoring', 'nanny', 'family support', 'caregiver'],
        'recommended_template_slug': 'gof-canva-layout-test-v1',
    },
    {
        'family': 'creative_printing',
        'keywords': ['printing', 'signage', 'design', 'flyers', 'business cards', 'stickers', 'banners', 'vehicle graphics', 'vinyl', 'signs'],
        'recommended_template_slug': 'card_grid',
    },
    {
        'family': 'professional',
        'keywords': ['consultant', 'accountant', 'lawyer', 'coach', 'agency', 'advisor', 'finance', 'insurance'],
        'recommended_template_slug': 'classic_service',
    },
    {
        'family': 'transport',
        'keywords': ['taxi', 'transport', 'delivery', 'courier', 'moving', 'logistics', 'van'],
        'recommended_template_slug': 'classic_service',
    },
    {
        'family': 'service_local',
        'keywords': ['service', 'cleaning', 'handyman', 'plumber', 'electrician', 'painter'],
        'recommended_template_slug': 'classic_service',
    },
]


def normalize_business_type(value):
    normalized = slugify(str(value or '').strip().lower()).replace('-', ' ')
    return normalized.strip()


def _contains_business_phrase(text, phrase):
    normalized_text = f" {normalize_business_type(text)} "
    normalized_phrase = normalize_business_type(phrase)
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in normalized_text


def _profile_payload(profile, *, display_business_type=None, family=None, key=None, exact_match=False):
    display_value = str(display_business_type or '').strip() or str(key or '').replace('_', ' ').strip() or _('Business')
    profile_key = key or profile.get('key') or 'generic'
    profile_family = family or profile.get('family') or profile_key
    return {
        'key': profile_key,
        'display_business_type': display_value,
        'family': profile_family,
        'hero_title': str(profile['hero_title']),
        'hero_description': str(profile['hero_description']),
        'hero_cta': str(profile['hero_cta']),
        'intro_heading': str(profile['intro_title']),
        'intro_title': str(profile['intro_title']),
        'intro_text': str(profile['intro_text']),
        'intro_variants': [
            {'title': str(variant['title']), 'text': str(variant['text'])}
            for variant in profile.get('intro_variants', [])
        ],
        'suggested_services': [str(item) for item in profile.get('services', [])],
        'services': [str(item) for item in profile.get('services', [])],
        'recommended_template_slug': normalize_template_slug(
            profile.get('recommended_template_slug')
            or infer_starter_template_slug(display_value or profile_family, fallback='service_pro')
        ),
        'exact_match': exact_match,
    }


def infer_business_family(value):
    normalized = normalize_business_type(value)
    for rule in BUSINESS_FAMILY_RULES:
        if any(keyword in normalized for keyword in rule['keywords']):
            return rule
    return None


def build_generic_profile(value, family=None):
    business_type = str(value or '').strip()
    display_value = business_type or str(_('Your business type'))
    family_name = family['family'] if isinstance(family, dict) else (family or 'generic')
    recommended_template_slug = (
        family.get('recommended_template_slug')
        if isinstance(family, dict)
        else infer_starter_template_slug(display_value, fallback='service_pro')
    ) or infer_starter_template_slug(display_value, fallback='service_pro')
    if isinstance(family, dict) and family.get('hero_title'):
        return _profile_payload(
            {
                'hero_title': family['hero_title'],
                'hero_description': family['hero_description'],
                'hero_cta': family['hero_cta'],
                'intro_title': family['intro_title'],
                'intro_text': family['intro_text'],
                'intro_variants': family.get('intro_variants', []),
                'services': family['services'],
                'recommended_template_slug': recommended_template_slug,
            },
            display_business_type=display_value,
            family=family_name,
            key=family_name,
            exact_match=False,
        )
    return {
        'key': 'generic',
        'display_business_type': display_value,
        'family': family_name,
        'hero_title': f'Website preview for {display_value}',
        'hero_description': 'A clear starting website to explain your services, contact details, and next steps.',
        'hero_cta': 'Request information',
        'intro_heading': 'A simple introduction section',
        'intro_title': 'A simple introduction section',
        'intro_text': (
            f'Use this section to explain what {display_value.lower()} offers, how customers can contact you, '
            'and what they should do next.'
        ),
        'intro_variants': [
            {
                'title': 'A simple introduction section',
                'text': (
                    f'Use this section to explain what {display_value.lower()} offers, how customers can contact you, '
                    'and what they should do next.'
                ),
            },
            {
                'title': 'A clearer business introduction',
                'text': (
                    f'Help visitors understand {display_value.lower()} quickly with a simple introduction that can be refined after activation.'
                ),
            },
            {
                'title': 'A stronger starting introduction',
                'text': (
                    f'Give visitors a clearer overview of {display_value.lower()} with practical content that can be completed after activation.'
                ),
            },
        ],
        'suggested_services': ['Main service', 'Popular option', 'Customer support'],
        'services': ['Main service', 'Popular option', 'Customer support'],
        'recommended_template_slug': recommended_template_slug,
        'exact_match': False,
    }


def get_onboarding_business_profile(business_type):
    normalized = normalize_business_type(business_type)
    for profile in ONBOARDING_SERVICE_PROFILES:
        normalized_terms = [normalize_business_type(term) for term in profile['match_terms']]
        is_exact = normalized in normalized_terms
        is_phrase_match = any(_contains_business_phrase(normalized, term) for term in normalized_terms)
        if is_exact or is_phrase_match:
            return _profile_payload(
                profile,
                display_business_type=str(business_type or '').strip() or profile['key'].replace('_', ' '),
                family=profile['key'],
                key=profile['key'],
                exact_match=is_exact,
            )
    family_match = infer_business_family(business_type)
    if family_match:
        return build_generic_profile(business_type, family=family_match)
    return build_generic_profile(business_type)


def resolve_business_profile(value):
    return get_onboarding_business_profile(value)


def get_onboarding_service_suggestions(business_type):
    profile = resolve_business_profile(business_type)
    return list(profile.get('suggested_services', profile.get('services', [])))


def get_onboarding_intro_variants(business_type):
    profile = resolve_business_profile(business_type)
    return list(profile.get('intro_variants', build_generic_profile(business_type)['intro_variants']))


def ensure_default_templates():
    for template in available_template_cards():
        Template.objects.update_or_create(
            slug=template['slug'],
            defaults={
                'name': str(template['label']),
                'layout_json': get_template_layout(template['slug']),
            },
        )


def available_template_options():
    return available_template_cards()


def available_palette_options():
    return [
        {
            'slug': slug,
            'label': label,
        }
        for slug, label in PALETTE_DISPLAY_LABELS.items()
    ]


def get_template_definition(slug):
    normalized_slug = normalize_template_slug(slug)
    template = Template.objects.filter(slug=normalized_slug).first()
    if template:
        card = get_template_card(normalized_slug)
        return {
            'slug': normalized_slug,
            'name': template.name,
            'label': card['label'],
            'category': card.get('category', ''),
            'style': card.get('style', ''),
            'layout_label': card.get('layout_label', ''),
            'description': card['description'],
            'best_for': card['best_for'],
            'layout_note': card['layout_note'],
            'layout_family': card['layout_family'],
            'layout_class': card['layout_class'],
            'section_layout': get_template_section_layout(normalized_slug),
            'preview_css_class': card['preview_css_class'],
            'layout': get_template_layout(normalized_slug),
        }
    card = get_template_card(normalized_slug)
    return {
        'slug': normalized_slug,
        'name': str(card['label']),
        'label': card['label'],
        'category': card.get('category', ''),
        'style': card.get('style', ''),
        'layout_label': card.get('layout_label', ''),
        'description': card['description'],
        'best_for': card['best_for'],
        'layout_note': card['layout_note'],
        'layout_family': card['layout_family'],
        'layout_class': card['layout_class'],
        'section_layout': get_template_section_layout(normalized_slug),
        'preview_css_class': card['preview_css_class'],
        'layout': get_template_layout(normalized_slug),
    }


GENERIC_SERVICE_LINES = {
    'clear services and pricing direction',
    'local visibility structure',
    'simple contact path for new enquiries',
    'main service',
    'popular option',
    'customer support',
}


BUSINESS_SERVICE_HINTS = [
    {
        'keywords': ('garage', 'mechanic', 'car repair', 'auto repair', 'mot', 'apk'),
        'services': ['APK / MOT preparation', 'Diagnostics and repairs', 'Maintenance and servicing'],
    },
    {
        'keywords': ('bakery', 'bread', 'pastry', 'patisserie'),
        'services': ['Fresh bread and pastries', 'Cakes and custom orders', 'Local pickup or daily specials'],
    },
    {
        'keywords': ('taxi', 'transport', 'cab', 'ride', 'airport transfer'),
        'services': ['Local taxi rides', 'Airport transfers', 'Business and appointment transport'],
    },
    {
        'keywords': ('painter', 'painting', 'paint', 'decorating'),
        'services': ['Interior painting', 'Exterior painting', 'Walls, ceilings and repairs'],
    },
    {
        'keywords': ('beauty', 'salon', 'spa', 'facial', 'nails', 'lashes', 'skincare'),
        'services': ['Treatments and appointments', 'Skincare or beauty services', 'Local salon bookings'],
    },
]


def _is_generic_service_line(value):
    normalized = str(value or '').strip().lower()
    if not normalized:
        return True
    if normalized in GENERIC_SERVICE_LINES:
        return True
    generic_fragments = (
        'professional services',
        'clear services',
        'quality solutions',
        'local visibility',
        'simple contact path',
    )
    return any(fragment in normalized for fragment in generic_fragments)


def _business_specific_service_candidates(service_type):
    candidates = []

    profile = resolve_business_profile(service_type)
    for item in profile.get('suggested_services', profile.get('services', [])):
        value = str(item or '').strip()
        if value and not _is_generic_service_line(value):
            candidates.append(value)

    normalized = normalize_business_type(service_type)
    for rule in BUSINESS_SERVICE_HINTS:
        if any(keyword in normalized for keyword in rule['keywords']):
            candidates.extend(rule['services'])
            break

    deduplicated = []
    seen = set()
    for item in candidates:
        key = item.strip().lower()
        if key and key not in seen:
            deduplicated.append(item)
            seen.add(key)

    return deduplicated


def _first_non_empty(*values):
    for value in values:
        text = str(value or '').strip()
        if text:
            return text
    return ''


def _profile_key(profile):
    return str(profile.get('key') or profile.get('family') or 'generic').strip().lower()


def _area_label(city='', service_area='', location=''):
    return _first_non_empty(city, service_area, location)


def _area_phrase(city='', service_area='', location=''):
    area = _area_label(city, service_area, location)
    return f'in {area}' if area else 'in your area'


def _display_business_name(business_name, service_type, profile):
    return _first_non_empty(
        business_name,
        service_type,
        profile.get('display_business_type'),
        'Your business',
    )


def _display_service_type(service_type, profile):
    return _first_non_empty(service_type, profile.get('display_business_type'), 'local business')


def _preferred_cta(profile_key, selected_services):
    key = str(profile_key or '').strip().lower()
    joined_services = ' '.join(str(item).lower() for item in (selected_services or []))

    if key in {'taxi', 'transport'}:
        return _('Book a ride')
    if key == 'garage':
        return _('Request a repair quote')
    if key in {'construction', 'painter'}:
        return _('Request a quote')
    if key in {'beauty', 'makeup_artist'}:
        return _('Book an appointment')
    if key == 'cleaning':
        return _('Request cleaning help')
    if key in {'restaurant', 'bakery'}:
        return _('Order or book now')
    if key in {'shop', 'shop_catalog'}:
        if 'repair' in joined_services or 'support' in joined_services:
            return _('Ask about products')
        return _('See products')
    return _('Request information')


def _business_specific_hero_title(profile_key, business_name, service_type, city, service_area, location, selected_services):
    area = _area_label(city, service_area, location)
    area_tail = f' in {area}' if area else ''
    name = _display_business_name(business_name, service_type, {'display_business_type': service_type})
    primary_service = _first_non_empty(*(selected_services or []))

    if profile_key in {'taxi', 'transport'}:
        return f'{name}{area_tail} for local rides and transfers'
    if profile_key == 'garage':
        return f'{name}{area_tail} for repairs, servicing, and diagnostics'
    if profile_key in {'construction', 'painter'}:
        return f'{name}{area_tail} for repair and project work'
    if profile_key in {'beauty', 'makeup_artist'}:
        return f'{name}{area_tail} for treatments and appointments'
    if profile_key == 'cleaning':
        return f'{name}{area_tail} for home and business cleaning'
    if profile_key in {'restaurant', 'bakery'}:
        return f'{name}{area_tail} for food, orders, and bookings'
    if profile_key in {'shop', 'shop_catalog'}:
        return f'{name}{area_tail} for products and enquiries'
    if primary_service and area:
        return f'{name} in {area} for {primary_service.lower()}'
    if primary_service:
        return f'{name} for {primary_service.lower()}'
    if area:
        return f'{name} in {area}'
    return name


def _business_specific_hero_description(profile_key, business_name, service_type, city, service_area, location, selected_services):
    area_phrase = _area_phrase(city, service_area, location)
    name = _display_business_name(business_name, service_type, {'display_business_type': service_type})
    service_bits = [str(item).strip() for item in (selected_services or []) if str(item).strip()]
    service_summary = ', '.join(service_bits[:2]).lower()

    if profile_key in {'taxi', 'transport'}:
        return f'Show local rides, airport transfers, and booking details {area_phrase} so passengers know how to contact {name}.'
    if profile_key == 'garage':
        return f'Explain repairs, diagnostics, and servicing {area_phrase} with a clear path for drivers to request help from {name}.'
    if profile_key in {'construction', 'painter'}:
        return f'Present your repair, renovation, or project work {area_phrase} with a clear quote path for new enquiries.'
    if profile_key in {'beauty', 'makeup_artist'}:
        return f'Present treatments, availability, and booking details {area_phrase} so new clients can contact {name} quickly.'
    if profile_key == 'cleaning':
        return f'Explain regular cleaning, deep cleaning, and quote requests {area_phrase} so customers can book the right service.'
    if profile_key in {'restaurant', 'bakery'}:
        return f'Help visitors find your menu, opening hours, and the best way to order or reserve {area_phrase}.'
    if profile_key in {'shop', 'shop_catalog'}:
        return f'Show products, categories, and enquiry options {area_phrase} so visitors can quickly find what they need.'
    if service_summary:
        return f'Explain {service_summary} {area_phrase} with a simple way for customers to contact {name}.'
    return f'Give visitors a clear first overview of your services {area_phrase} and how to contact {name}.'


def _service_intro_copy(profile_key, business_name, service_type, city, service_area, location, selected_services):
    area_phrase = _area_phrase(city, service_area, location)
    if profile_key in {'taxi', 'transport'}:
        return f'Help passengers see ride options, transfer routes, and booking details {area_phrase}.'
    if profile_key == 'garage':
        return f'Help drivers understand which repairs, servicing, and vehicle checks you handle {area_phrase}.'
    if profile_key in {'construction', 'painter'}:
        return f'Show the jobs you take on {area_phrase} and make it easy to request a quote.'
    if profile_key in {'beauty', 'makeup_artist'}:
        return f'Show your treatments, appointment options, and booking path {area_phrase}.'
    if profile_key == 'cleaning':
        return f'Explain the spaces you clean, the service options, and how customers can book {area_phrase}.'
    if profile_key in {'restaurant', 'bakery'}:
        return f'Show menu highlights, takeaway options, and the best way to order or reserve {area_phrase}.'
    if profile_key in {'shop', 'shop_catalog'}:
        return f'Guide visitors to the right product categories, featured items, and next steps {area_phrase}.'
    primary_service = _first_non_empty(*(selected_services or []))
    if primary_service:
        return f'Give visitors a quick overview of {primary_service.lower()} and the main services you offer {area_phrase}.'
    business_label = _display_service_type(service_type, {'display_business_type': service_type})
    return f'Explain what your {business_label.lower()} offers {area_phrase} and how customers should contact you.'


def _service_description_line(service_label, profile_key, city, service_area, location):
    label = str(service_label or '').strip()
    if not label:
        return ''

    area_phrase = _area_phrase(city, service_area, location)
    lower_label = label.lower()

    if profile_key in {'taxi', 'transport'}:
        if 'airport' in lower_label:
            return f'{label} with clear pickup and booking requests {area_phrase}.'
        if 'business' in lower_label or 'appointment' in lower_label:
            return f'{label} for planned journeys and regular transport needs {area_phrase}.'
        return f'{label} with a simple booking path for passengers {area_phrase}.'
    if profile_key == 'garage':
        if 'diagnostic' in lower_label:
            return f'{label} to help drivers understand faults and next repair steps {area_phrase}.'
        if 'mot' in lower_label or 'apk' in lower_label:
            return f'{label} with a clear path to book checks and related repair work {area_phrase}.'
        return f'{label} for local drivers who need quick contact and clear workshop support {area_phrase}.'
    if profile_key in {'construction', 'painter'}:
        return f'{label} with straightforward quote requests and practical project information {area_phrase}.'
    if profile_key in {'beauty', 'makeup_artist'}:
        return f'{label} with clear appointment requests and treatment information {area_phrase}.'
    if profile_key == 'cleaning':
        return f'{label} with a simple way to ask about availability and pricing {area_phrase}.'
    if profile_key in {'restaurant', 'bakery'}:
        return f'{label} with clear ordering, booking, or collection information {area_phrase}.'
    if profile_key in {'shop', 'shop_catalog'}:
        return f'{label} presented clearly so visitors can compare options and ask questions {area_phrase}.'
    return f'{label} with a clear enquiry path {area_phrase}.'


def _trust_cards(profile_key, city, service_area, location):
    area_phrase = _area_phrase(city, service_area, location)
    if profile_key in {'taxi', 'transport'}:
        return (
            (_('Clear ride options'), f'Show transfer and journey options {area_phrase} without making visitors guess what you cover.'),
            (_('Simple booking path'), f'Keep calls, WhatsApp, or booking requests easy for passengers {area_phrase}.'),
            (_('Local coverage'), f'Explain the routes, areas, or transfer types you handle {area_phrase}.'),
        )
    if profile_key == 'garage':
        return (
            (_('Clear repair scope'), f'Explain the repair and servicing work you handle {area_phrase}.'),
            (_('Fast contact path'), 'Make it easy for drivers to ask about faults, quotes, or workshop availability.'),
            (_('Practical workshop info'), 'Show the services, vehicle support, and next steps people usually ask about first.'),
        )
    if profile_key in {'construction', 'painter'}:
        return (
            (_('Clear job types'), f'Show the repair, installation, or renovation work you take on {area_phrase}.'),
            (_('Quote-ready enquiries'), 'Make it easy for visitors to send the details you need for a quote.'),
            (_('Local project focus'), 'Use the page to explain where you work and what kind of jobs fit best.'),
        )
    if profile_key in {'beauty', 'makeup_artist'}:
        return (
            (_('Clear treatment list'), 'Help visitors quickly understand your most requested services and appointment options.'),
            (_('Easy booking path'), 'Keep appointment requests simple by showing the best contact method right away.'),
            (_('Confident first impression'), 'Use short, practical copy that makes new clients feel comfortable contacting you.'),
        )
    if profile_key == 'cleaning':
        return (
            (_('Clear cleaning options'), 'Show the spaces you clean and the service types people ask about most.'),
            (_('Simple quote requests'), 'Make it easy to ask about regular cleaning, one-off jobs, or availability.'),
            (_('Local service area'), f'Explain the homes, offices, or areas you cover {area_phrase}.'),
        )
    if profile_key in {'restaurant', 'bakery'}:
        return (
            (_('Menu and ordering clarity'), 'Help visitors quickly find what you serve and how to order or reserve.'),
            (_('Opening hours and location'), 'Keep practical details easy to find before people decide to visit.'),
            (_('Simple next step'), 'Use one clear contact or order action instead of making customers search for it.'),
        )
    if profile_key in {'shop', 'shop_catalog'}:
        return (
            (_('Clear product sections'), 'Show key categories and featured items so visitors know where to start.'),
            (_('Easy product enquiries'), 'Make it simple to ask about stock, product details, or custom requests.'),
            (_('Room to grow'), 'Start with a practical catalog structure that can expand later if needed.'),
        )
    return (
        (_('Clear offer'), 'Explain what you do quickly so visitors know why they should contact you.'),
        (_('Better visibility'), 'Use a page structure that helps people understand your services right away.'),
        (_('Easy contact'), 'Keep calls, messages, and quote requests simple for new visitors.'),
    )


def build_suggestions(
    *,
    business_name,
    service_type,
    city,
    template_slug=None,
    variant_index=0,
    service_area='',
    selected_services=None,
    service_descriptions=None,
    contact_name='',
    phone='',
    email='',
    address='',
    location='',
    website_goal='',
    style_notes='',
    business_description='',
    language='',
    context_data=None,
):
    business_name = business_name.strip()
    service_type = service_type.strip()
    city = city.strip()
    service_area = service_area.strip()
    location = location.strip()
    template_slug = normalize_template_slug(template_slug)
    variant_index = int(variant_index or 0) % SUGGESTION_VARIANTS

    profile = resolve_business_profile(service_type)
    profile_key = _profile_key(profile)
    display_name = _display_business_name(business_name, service_type, profile)
    display_service_type = _display_service_type(service_type, profile)
    display_service_type_lower = display_service_type.lower()
    area_text = _area_label(city, service_area, location)
    service_candidates = _business_specific_service_candidates(service_type)
    provided_selected_services = [
        str(item).strip()
        for item in (selected_services or [])
        if str(item).strip()
    ]
    provided_service_descriptions = [
        str(item).strip()
        for item in (service_descriptions or [])
        if str(item).strip()
    ]
    chosen_services = provided_selected_services or service_candidates[:3]
    if not chosen_services:
        chosen_services = [str(item).strip() for item in profile.get('suggested_services', [])[:3] if str(item).strip()]
    if not chosen_services:
        chosen_services = [_('Main service'), _('Popular option'), _('Customer support')]

    hero_title_variants = [
        _business_specific_hero_title(profile_key, display_name, display_service_type, city, service_area, location, chosen_services),
        f'{display_name} { _area_phrase(city, service_area, location) } for {chosen_services[0].lower()}',
        f'{display_name} helps customers { _area_phrase(city, service_area, location) } with {display_service_type_lower}',
    ]
    hero_description_variants = [
        _business_specific_hero_description(profile_key, display_name, display_service_type, city, service_area, location, chosen_services),
        f'Show {", ".join(chosen_services[:2]).lower()} { _area_phrase(city, service_area, location) } with a clear contact path for new enquiries.',
        f'Give visitors a quick overview of {display_service_type_lower} services, local coverage, and the best way to contact {display_name}.',
    ]
    hero_highlight_text_variants = [
        f'Built to explain {display_service_type_lower} services clearly and guide visitors to a simple next step.',
        f'Use this layout to show what {display_name} handles { _area_phrase(city, service_area, location) } and how customers should get in touch.',
        f'A practical starting point for clearer local service copy, stronger contact paths, and useful first-page structure.',
    ]
    services_intro_variants = [
        _service_intro_copy(profile_key, display_name, display_service_type, city, service_area, location, chosen_services),
        f'Help visitors quickly understand your main services, service area, and the best next step { _area_phrase(city, service_area, location) }.',
        f'Keep this section focused on the services people ask about most so contacting {display_name} feels easy.',
    ]
    cta_description_variants = [
        f'A practical first website for {display_service_type_lower} enquiries with room to refine details later.',
        f'Use this starter setup to present services, local coverage, and contact details without overcomplicating the page.',
        f'A clear website base for {display_name} that can be expanded as the business grows.',
    ]
    benefits_intro_variants = [
        f'Keep the page focused on what customers need first: your services, area, and the fastest way to contact you.',
        f'Use a stronger first-page structure to explain your offer more clearly { _area_phrase(city, service_area, location) }.',
        f'A practical starting point for clearer messaging and better enquiry paths for {display_name}.',
    ]
    trust_cards = _trust_cards(profile_key, city, service_area, location)
    preferred_cta = _preferred_cta(profile_key, chosen_services)

    hero = {
        'kicker': area_text or display_service_type,
        'title': hero_title_variants[variant_index],
        'description': hero_description_variants[variant_index],
        'cta_text': preferred_cta,
        'secondary_cta_text': _('See how it works'),
        'highlight_title': _('Built for your business'),
        'highlight_text': hero_highlight_text_variants[variant_index],
    }

    services = {
        'title': _('Main services'),
        'intro': services_intro_variants[variant_index],
        'item_1': chosen_services[0] if len(chosen_services) > 0 else _('Main service'),
        'item_2': chosen_services[1] if len(chosen_services) > 1 else _('Popular option'),
        'item_3': chosen_services[2] if len(chosen_services) > 2 else _('Customer support'),
    }
    for index in range(3):
        item_value = services.get(f'item_{index + 1}', '')
        provided_description = provided_service_descriptions[index] if index < len(provided_service_descriptions) else ''
        services[f'item_{index + 1}_text'] = (
            provided_description
            or _service_description_line(item_value, profile_key, city, service_area, location)
        )

    contact = {
        'title': _('Ready for new enquiries'),
        'description': (
            f'Keep phone, email, WhatsApp, or a contact form easy to find so customers can reach {display_name} quickly.'
        ),
        'primary_contact': _first_non_empty(phone, email, _('Contact details ready to add')),
        'secondary_contact': _first_non_empty(location, service_area, city, _('Add your preferred contact method or service area')),
        'cta_text': preferred_cta,
    }

    cta = {
        'title': _business_specific_hero_title(profile_key, display_name, display_service_type, city, service_area, location, chosen_services),
        'description': cta_description_variants[variant_index],
        'cta_text': preferred_cta,
    }

    benefits = {
        'title': _('Why this structure works'),
        'intro': benefits_intro_variants[variant_index],
        'card_1_title': trust_cards[0][0],
        'card_1_text': trust_cards[0][1],
        'card_2_title': trust_cards[1][0],
        'card_2_text': trust_cards[1][1],
        'card_3_title': trust_cards[2][0],
        'card_3_text': trust_cards[2][1],
    }

    suggestions = {
        'hero': hero,
        'services': services,
        'contact': contact,
        'cta': cta,
        'benefits': benefits,
    }

    if template_slug == 'visual_hero':
        visual_titles = [
            f'{display_name} helps {city} customers choose {display_service_type_lower} with confidence',
            f'Show {city} customers why {display_name} is a strong choice for {display_service_type_lower}',
            f'A stronger first impression for {display_name} and {display_service_type_lower} visitors in {city}',
        ]
        visual_descriptions = [
            _('Use a stronger sales-focused layout to explain your offer, show value, and guide visitors toward action.'),
            _('Present your offer with more visual impact, clearer trust signals, and stronger calls to action.'),
            _('Give visitors a more persuasive first section that supports visibility, credibility, and response.'),
        ]
        suggestions['hero']['highlight_title'] = _('Built to attract more enquiries')
        visual_highlights = [
            _('A stronger offer layout for businesses that want clearer visibility and promotion.'),
            _('A more confident homepage structure for businesses that want to convert more visitors into enquiries.'),
            _('A visually stronger service layout for businesses that want better attention and clearer next steps.'),
        ]
        suggestions['hero']['title'] = visual_titles[variant_index]
        suggestions['hero']['description'] = visual_descriptions[variant_index]
        suggestions['hero']['highlight_text'] = visual_highlights[variant_index]
    elif template_slug == 'card_grid':
        grid_titles = [
            f'{display_name} - {display_service_type} in {city}',
            f'Explore {display_name} services and categories in {city}',
            f'{display_name} helps {city} customers find the right {display_service_type_lower} option quickly',
        ]
        grid_descriptions = [
            _('A card-based website start for businesses that want to show multiple services or product categories clearly.'),
            _('Use a more structured category layout when visitors need to compare several offers quickly.'),
            _('A multi-card starting point for businesses that want to guide visitors to the right service or product area.'),
        ]
        suggestions['services']['title'] = _('Main categories or services')
        grid_services_intro = [
            _('Use this structure to guide visitors quickly to the right category, service, or product area.'),
            _('A category-first structure that helps visitors scan multiple offers without confusion.'),
            _('Organise different services or product groups into a layout that is easier to browse and act on.'),
        ]
        suggestions['benefits']['title'] = _('Built for multiple offers')
        grid_benefits_intro = [
            _('A clearer structure for businesses that need to present more than one main service or product type.'),
            _('Useful when your business needs to present several categories, service groups, or product types at once.'),
            _('Designed to help visitors understand a wider offer without making the page feel cluttered.'),
        ]
        suggestions['hero']['title'] = grid_titles[variant_index]
        suggestions['hero']['description'] = grid_descriptions[variant_index]
        suggestions['services']['intro'] = grid_services_intro[variant_index]
        suggestions['benefits']['intro'] = grid_benefits_intro[variant_index]
    elif template_slug == 'gof-canva-layout-test-v1':
        suggestions = {
            'hero': {
                'kicker': _('Original GOF starting design'),
                'title': _('Main headline for your business goes here'),
                'description': _('Use this section to explain your most important service or offer in a clear, customer-friendly way.'),
                'cta_text': _('Request a quote'),
                'secondary_cta_text': _('See how it works'),
                'highlight_title': _('Starter layout notes'),
                'highlight_text': _('This design uses neutral demo content so it can later be adapted to your business name, services, images, and colours.'),
            },
            'about': {
                'kicker': _('About this business'),
                'title': _('Use this section to explain who you help and why customers should trust your business'),
                'description': _('Keep the introduction short and practical so visitors quickly understand what the business does and what makes it worth contacting.'),
                'support_title': _('What to include here'),
                'support_text': _('Add a short business summary, experience, service area, or a simple reason customers feel confident contacting you.'),
                'point_1': _('Add a short explanation of the business and who it helps'),
                'point_2': _('Add one or two trust points that support the introduction'),
            },
            'services': {
                'kicker': _('Services / What you offer'),
                'title': _('Services / What you offer'),
                'intro': _('Use these cards for services, product groups, packages, or common customer requests.'),
                'item_1': _('Main service or offer'),
                'item_1_text': _('Short description of the first important service.'),
                'item_2': _('Popular option'),
                'item_2_text': _('Describe a second service, package, or request type.'),
                'item_3': _('Extra service'),
                'item_3_text': _('Use this card for an add-on or related service.'),
                'item_4': _('Specialist service'),
                'item_4_text': _('Use this area for a specialist offer, package, or customer request.'),
                'item_5': _('Support or follow-up service'),
                'item_5_text': _('Explain a follow-up service, maintenance option, or supporting offer.'),
                'item_6': _('Extra service or add-on'),
                'item_6_text': _('Use this final card for another useful category, offer, or service line.'),
            },
            'portfolio': {
                'kicker': _('Work examples / Portfolio'),
                'title': _('Work examples / Portfolio'),
                'intro': _('Show examples of your work, products, or previous results here.'),
                'card_1_title': _('Featured project or result'),
                'card_1_text': _('Use this larger area for a stronger featured example, project highlight, or lead product/result.'),
                'card_2_title': _('Second example'),
                'card_2_text': _('Add another example that helps customers understand the type of work or quality you provide.'),
                'card_3_title': _('Third example'),
                'card_3_text': _('Use this space for one more project, result, product group, or proof-style example.'),
                'card_4_title': _('Product or service example'),
                'card_4_text': _('Add one more visual example to complete the portfolio or gallery section.'),
            },
            'process': {
                'kicker': _('Process / How it works'),
                'title': _('Process / How it works'),
                'intro': _('Explain how customers can start.'),
                'step_1_title': _('Tell us what you need'),
                'step_1_text': _('Explain how customers first get in touch or request information.'),
                'step_2_title': _('Receive a clear answer'),
                'step_2_text': _('Explain what happens next, such as a quote, consultation, or booking step.'),
                'step_3_title': _('Start the service'),
                'step_3_text': _('Explain the final step so customers know how the service moves forward.'),
            },
            'trust': {
                'kicker': _('Trust / Why choose this business'),
                'title': _('Trust / Why choose this business'),
                'intro': _('Add trust points that help customers choose your business.'),
                'card_1_title': _('Quality point'),
                'card_1_text': _('Use this card for a clear quality, service, or guarantee message.'),
                'card_2_title': _('Customer-friendly benefit'),
                'card_2_text': _('Explain a practical benefit that makes the business easier or safer to choose.'),
                'card_3_title': _('Experience or reassurance'),
                'card_3_text': _('Use this card for experience, support, reliability, or another simple trust signal.'),
            },
            'contact': {
                'kicker': _('Contact / Request a quote'),
                'title': _('Contact / Request a quote'),
                'description': _('Add phone, email, WhatsApp, location, service area, and a clear contact button.'),
                'detail_1_label': _('Phone'),
                'detail_1_value': _('Add phone number here'),
                'detail_2_label': _('Email'),
                'detail_2_value': _('Add email address here'),
                'detail_3_label': _('WhatsApp'),
                'detail_3_value': _('Add WhatsApp contact here'),
                'detail_4_label': _('Location or service area'),
                'detail_4_value': _('Add location or service area here'),
                'cta_text': _('Request a quote'),
            },
            'final_cta': {
                'title': _('Final CTA'),
                'description': _('Use this final section for one clear action button and a short closing reason to contact the business now.'),
                'cta_text': _('Contact this business'),
            },
            'footer': {
                'business_name': _('Your business name'),
                'description': _('Short description of the business, service area, and main reason to contact you.'),
                'contact_line': _('Email or phone placeholder'),
                'nav_title': _('Pages'),
                'nav_item_1': _('Home'),
                'nav_item_2': _('About'),
                'nav_item_3': _('Contact'),
                'services_title': _('Services / What you offer'),
                'services_item_1': _('Main service'),
                'services_item_2': _('Popular service'),
                'services_item_3': _('Extra service'),
                'contact_title': _('Contact'),
                'contact_item_1': _('Phone'),
                'contact_item_2': _('Email'),
                'contact_item_3': _('Location or service area'),
                'legal_title': _('Info'),
                'legal_item_1': _('Privacy / Terms'),
                'legal_item_2': _('Request a quote'),
                'legal_item_3': _('Opening hours or support note'),
                'copyright_line': _('© Year Your business name. All rights reserved.'),
                'platform_note': _('Website prepared with Get Online Fast'),
            },
        }

    if isinstance(suggestions.get('services'), dict):
        for index, field_key in enumerate(('item_1', 'item_2', 'item_3')):
            current_value = str(suggestions['services'].get(field_key, '')).strip()
            if _is_generic_service_line(current_value) and index < len(service_candidates):
                suggestions['services'][field_key] = service_candidates[index]
                suggestions['services'][f'{field_key}_text'] = _service_description_line(
                    service_candidates[index],
                    profile_key,
                    city,
                    service_area,
                    location,
                )

    derived_selected_services = []
    if isinstance(suggestions.get('services'), dict):
        for field_key in ('item_1', 'item_2', 'item_3'):
            value = str(suggestions['services'].get(field_key, '')).strip()
            if value:
                derived_selected_services.append(value)
    if not derived_selected_services:
        derived_selected_services = service_candidates[:3]

    polish_context = build_business_context(
        source=context_data,
        business_name=business_name,
        business_type=service_type,
        city=city,
        service_area=service_area,
        selected_services=provided_selected_services or derived_selected_services,
        service_descriptions=provided_service_descriptions,
        contact_name=contact_name,
        phone=phone,
        email=email,
        address=address,
        location=location,
        website_goal=website_goal,
        style_notes=style_notes,
        business_description=business_description,
        language=language,
        template_slug=template_slug,
        platform_mode='starter_preview',
    )

    try:
        from .services_ai import polish_starter_suggestions_with_ai

        suggestions = polish_starter_suggestions_with_ai(
            suggestions,
            polish_context,
        )
    except Exception as exc:
        logger.warning('Starter AI polish integration failed: %s', exc)

    return suggestions


def current_suggestion_variant(site, language):
    hero_title = SiteContent.objects.filter(
        site=site,
        section_key='hero',
        field_key='title',
        language=language,
    ).first() or SiteContent.objects.filter(
        site=site,
        section_key='hero',
        field_key='title',
    ).first()
    if not hero_title or not hero_title.value:
        return 0

    business_name = site.business_name.strip()
    service_type_lower = site.service_type.strip().lower()
    city = site.city.strip()
    hero_title_variants = [
        f'{business_name} for {service_type_lower} in {city}',
        f'Trust {business_name} for {service_type_lower} work in {city}',
        f'{business_name} helps {city} customers with {service_type_lower}',
    ]
    try:
        return hero_title_variants.index(hero_title.value)
    except ValueError:
        return 0


def next_suggestion_variant(site, language):
    return (current_suggestion_variant(site, language) + 1) % SUGGESTION_VARIANTS


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


def _preferred_hero_image_key(site, business_type=None, existing_selection=None):
    if existing_selection and not is_generic_placeholder_image_key(existing_selection):
        return get_image_by_key(existing_selection)['key']
    return get_default_image_for_business_type(business_type or site.service_type)['key']


def ensure_default_site_images(
    site,
    language,
    *,
    business_type=None,
    only_if_missing=True,
    existing_selection=None,
    refresh_generic_existing=False,
):
    image_item = None
    preferred_key = _preferred_hero_image_key(
        site,
        business_type=business_type,
        existing_selection=existing_selection,
    )
    image_item = get_image_by_key(preferred_key)

    hero_content = SiteContent.objects.filter(
        site=site,
        section_key='hero',
        field_key='hero_image',
        language=language,
    ).first()

    should_refresh_generic = bool(
        hero_content
        and refresh_generic_existing
        and hero_content.value
        and is_generic_placeholder_image_key(hero_content.value)
        and not existing_selection
    )

    if hero_content and only_if_missing and hero_content.value and not should_refresh_generic:
        return hero_content.value

    SiteContent.objects.update_or_create(
        site=site,
        section_key='hero',
        field_key='hero_image',
        language=language,
        defaults={'value': image_item['key']},
    )
    return image_item['key']


def get_site_content_map(site, language):
    prefetched_content_map = getattr(site, '_prefetched_content_map', None)
    if isinstance(prefetched_content_map, dict):
        return prefetched_content_map

    requested = list(site.contents.filter(language=language))
    if not requested:
        requested = list(site.contents.all())

    content_map = {}
    for item in requested:
        content_map.setdefault(item.section_key, {})[item.field_key] = item.value
    return content_map


def _build_section_image_context(site):
    business_type = site.service_type
    image_context = {
        'hero': resolve_business_images(business_type, purpose='hero', limit=1),
        'gallery': resolve_business_images(business_type, purpose='gallery', limit=4),
        'service': resolve_business_images(business_type, purpose='service', limit=6),
        'detail': resolve_business_images(business_type, purpose='detail', limit=3),
        'background': resolve_business_images(business_type, purpose='background', limit=2),
        'before_after': resolve_business_images(business_type, purpose='before_after', limit=2),
    }
    return image_context


def _attach_section_images(section_key, section_values, image_context):
    if section_key == 'about':
        story_image = (
            image_context['detail']
            or image_context['gallery']
            or image_context['hero']
        )
        background_image = image_context['background']
        if story_image:
            item = story_image[0]
            section_values['story_image_url'] = static(item['static_path'])
            section_values['story_image_alt'] = item['alt_text']
        if background_image:
            item = background_image[0]
            section_values['story_background_image_url'] = static(item['static_path'])
    elif section_key == 'services':
        service_images = image_context['service'] or image_context['detail'] or image_context['gallery'] or image_context['hero']
        for index in range(6):
            if index >= len(service_images):
                break
            item = service_images[index]
            section_values[f'item_{index + 1}_image_url'] = static(item['static_path'])
            section_values[f'item_{index + 1}_image_alt'] = item['alt_text']
    elif section_key == 'portfolio':
        showcase_images = (
            image_context['gallery']
            + image_context['before_after']
            + image_context['detail']
            + image_context['background']
            + image_context['hero']
        )
        for index in range(4):
            if index >= len(showcase_images):
                break
            item = showcase_images[index]
            section_values[f'card_{index + 1}_image_url'] = static(item['static_path'])
            section_values[f'card_{index + 1}_image_alt'] = item['alt_text']


def ensure_language_content(site, language):
    if site.contents.filter(language=language).exists():
        ensure_default_site_images(site, language, only_if_missing=True)
        return

    fallback_map = get_site_content_map(site, language)
    if fallback_map:
        save_site_content(site, language, fallback_map)
    ensure_default_site_images(site, language, only_if_missing=True)


def build_editor_sections(site, language):
    template_definition = get_template_definition(site.template_slug)
    content_map = get_site_content_map(site, language)
    sections = []
    contextual_choice_sets = {
        'hero_image_choices': get_image_choices_for_business_type(site.service_type),
    }

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
                    'input_type': field.get('input_type', 'textarea'),
                    'choices': contextual_choice_sets.get(
                        field.get('choices', ''),
                        EDITOR_FIELD_CHOICE_SETS.get(field.get('choices', ''), []),
                    ),
                    'display_value': (
                        get_image_by_key(section_values.get(field['key'], '')).get('label', '')
                        if field.get('input_type') == 'select'
                        else ''
                    ),
                    'display_option_label': (
                        get_image_by_key(section_values.get(field['key'], '')).get('option_label', '')
                        if field.get('input_type') == 'select'
                        else ''
                    ),
                    'preview_static_path': (
                        static(get_image_by_key(section_values.get(field['key'], '')).get('static_path'))
                        if field.get('input_type') == 'select'
                        else ''
                    ),
                    'preview_alt': (
                        get_image_by_key(section_values.get(field['key'], '')).get('alt_text', '')
                        if field.get('input_type') == 'select'
                        else ''
                    ),
                    'style_type': (
                        get_image_by_key(section_values.get(field['key'], '')).get('style_type', '')
                        if field.get('input_type') == 'select'
                        else ''
                    ),
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
    image_context = _build_section_image_context(site)
    render_sections = []

    for section in template_definition['layout']:
        schema = SECTION_SCHEMAS[section['type']]
        layout_mode = template_definition['section_layout'].get(section['key'], 'boxed')
        section_values = dict(content_map.get(section['key'], {}))
        if section['key'] == 'hero':
            image_item = get_image_by_key(section_values.get('hero_image'))
            section_values['hero_image'] = image_item['key']
            section_values['hero_image_url'] = static(image_item['static_path'])
            section_values['hero_image_alt'] = image_item['alt_text']
            section_values['hero_image_label'] = image_item['label']
        else:
            _attach_section_images(section['key'], section_values, image_context)
        render_sections.append(
            {
                'key': section['key'],
                'type': section['type'],
                'label': schema['label'],
                'template_name': schema['template'],
                'values': section_values,
                'section_class': f'section--{section["key"]}',
                'section_id': section['key'],
                'section_container_class': (
                    'section-container--full' if layout_mode == 'full_width' else 'section-container--boxed'
                ),
                'section_layout_mode': layout_mode,
            }
        )

    return render_sections


def site_slug(site):
    return slugify(site.business_name) or 'your-business'
