from django.utils.translation import gettext_lazy as _


TEMPLATE_CATEGORY_ORDER = [
    'Business',
    'Trades',
    'Automotive',
    'Local business',
]


TEMPLATE_CATEGORY_DETAILS = {
    'Business': {
        'title': _('Business'),
        'description': _('Clear, professional layout starting points for service businesses, consultants, and smaller companies.'),
    },
    'Trades': {
        'title': _('Trades'),
        'description': _('More direct layout directions for builders, renovation teams, installers, and practical local services.'),
    },
    'Automotive': {
        'title': _('Automotive'),
        'description': _('Layout directions focused on trust, workshop services, diagnostics, and local repair visibility.'),
    },
    'Local business': {
        'title': _('Local business'),
        'description': _('Warmer layout starting points for cafes, restaurants, takeaways, and neighbourhood shops.'),
    },
}


TEMPLATE_CATALOG = [
    {
        'template_id': 'clean-professional-v1',
        'name': _('Clean Professional'),
        'category': 'Business',
        'best_for': _('consultants, local services, small companies'),
        'description': _('A calm, structured layout starter for service businesses that want trust, clarity, and fast enquiries.'),
        'image_path': 'core/img/templates/clean-professional-v1.svg',
        'status': 'ready',
    },
    {
        'template_id': 'construction-trades-v1',
        'name': _('Construction & Trades'),
        'category': 'Trades',
        'best_for': _('builders, handymen, renovation companies'),
        'description': _('A stronger trades layout direction focused on credibility, project highlights, and clear contact actions.'),
        'image_path': 'core/img/templates/construction-trades-v1.svg',
        'status': 'reference',
    },
    {
        'template_id': 'garage-repair-v1',
        'name': _('Garage & Repair'),
        'category': 'Automotive',
        'best_for': _('mechanics, garages, repair shops'),
        'description': _('A practical automotive layout direction for repair services, diagnostics, bookings, and local visibility.'),
        'image_path': 'core/img/templates/garage-repair-v1.svg',
        'status': 'reference',
    },
    {
        'template_id': 'restaurant-local-v1',
        'name': _('Restaurant & Local Shop'),
        'category': 'Local business',
        'best_for': _('restaurants, cafes, takeaways, shops'),
        'description': _('A warmer local-business layout direction for menus, locations, opening times, and quick customer actions.'),
        'image_path': 'core/img/templates/restaurant-local-v1.svg',
        'status': 'reference',
    },
]


def template_catalog():
    return TEMPLATE_CATALOG


def template_category_details():
    return TEMPLATE_CATEGORY_DETAILS


def template_category_order():
    return TEMPLATE_CATEGORY_ORDER


def template_lookup():
    return {entry['template_id']: entry for entry in TEMPLATE_CATALOG}
