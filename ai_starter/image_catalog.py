from __future__ import annotations

from pathlib import Path

IMAGE_CHOICES = [
    {
        'key': 'generic_service_01',
        'label': 'Local service business photo',
        'category': 'generic_service',
        'static_path': 'core/img/hero-library/generic_service/generic-service-01.png',
        'alt_text': 'Local service business hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'generic_service_02',
        'label': 'Professional service website photo',
        'category': 'generic_service',
        'static_path': 'core/img/hero-library/generic_service/generic-service-02.jpg',
        'alt_text': 'Professional service business photo',
        'style_type': 'photo',
    },
    {
        'key': 'construction_01',
        'label': 'Construction project photo',
        'category': 'construction',
        'static_path': 'core/img/hero-library/construction/construction-01.jpg',
        'alt_text': 'Construction project hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'construction_02',
        'label': 'Construction team photo',
        'category': 'construction',
        'static_path': 'core/img/hero-library/construction/construction-02.jpg',
        'alt_text': 'Construction team hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'garage_01',
        'label': 'Garage service photo',
        'category': 'garage',
        'static_path': 'core/img/hero-library/garage/garage-01.png',
        'alt_text': 'Garage or car repair hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'garage_02',
        'label': 'Workshop repair photo',
        'category': 'garage',
        'static_path': 'core/img/hero-library/garage/garage-02.png',
        'alt_text': 'Workshop repair business photo',
        'style_type': 'photo',
    },
    {
        'key': 'restaurant_01',
        'label': 'Restaurant food photo',
        'category': 'restaurant',
        'static_path': 'core/img/hero-library/restaurant/restaurant-01.jpg',
        'alt_text': 'Restaurant hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'restaurant_02',
        'label': 'Dining experience photo',
        'category': 'restaurant',
        'static_path': 'core/img/hero-library/restaurant/restaurant-02.jpg',
        'alt_text': 'Dining or hospitality hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'beauty_01',
        'label': 'Beauty studio photo',
        'category': 'beauty',
        'static_path': 'core/img/hero-library/beauty/beauty-01.jpg',
        'alt_text': 'Beauty or wellness hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'beauty_02',
        'label': 'Salon treatment photo',
        'category': 'beauty',
        'static_path': 'core/img/hero-library/beauty/beauty-02.jpg',
        'alt_text': 'Salon or treatment hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'shop_01',
        'label': 'Local shop display photo',
        'category': 'shop',
        'static_path': 'core/img/hero-library/shop/shop-01.jpg',
        'alt_text': 'Retail or local shop hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'shop_02',
        'label': 'Catalog product photo',
        'category': 'shop',
        'static_path': 'core/img/hero-library/shop/shop-02.jpg',
        'alt_text': 'Shop or catalog hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'transport_01',
        'label': 'Transport service photo',
        'category': 'transport',
        'static_path': 'core/img/hero-library/transport/transport-01.png',
        'alt_text': 'Transport or taxi hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'transport_02',
        'label': 'Mobility service photo',
        'category': 'transport',
        'static_path': 'core/img/hero-library/transport/transport-02.png',
        'alt_text': 'Mobility service hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'placeholder_clean_01',
        'label': 'Clean professional illustration',
        'category': 'generic_service',
        'static_path': 'core/img/templates/clean-professional-v1.svg',
        'alt_text': 'Placeholder professional hero illustration',
        'style_type': 'placeholder',
    },
    {
        'key': 'placeholder_garage_01',
        'label': 'Garage layout illustration',
        'category': 'garage',
        'static_path': 'core/img/templates/garage-repair-v1.svg',
        'alt_text': 'Placeholder garage hero illustration',
        'style_type': 'placeholder',
    },
]

DEFAULT_IMAGE_KEY = 'generic_service_01'
_BASE_STATIC_DIR = Path(__file__).resolve().parent.parent / 'static'


def _path_exists(static_path):
    return (_BASE_STATIC_DIR / Path(static_path)).exists()


def _display_label(item):
    prefix = 'Photo' if item.get('style_type') == 'photo' else 'Placeholder'
    return f'{prefix}: {item["label"]}'


def _with_meta(item):
    enriched = dict(item)
    enriched['path_exists'] = _path_exists(item['static_path'])
    enriched['option_label'] = _display_label(item)
    return enriched


def _normalize_category(category):
    normalized = str(category or '').strip().lower()
    return normalized or 'generic_service'


def _infer_category_from_business_type(business_type):
    business_text = str(business_type or '').strip().lower()
    category_keywords = [
        ('garage', ('garage', 'oficina', 'mechanic', 'mechanic shop', 'auto repair', 'car repair')),
        ('construction', ('construction', 'builder', 'contractor', 'renovation', 'handyman', 'roofing')),
        ('restaurant', ('restaurant', 'cafe', 'cafeteria', 'food', 'pizza', 'bar')),
        ('beauty', ('beauty', 'salon', 'spa', 'barber', 'hair', 'wellness')),
        ('shop', ('shop', 'store', 'drogist', 'retail', 'catalog', 'print shop', 'printing', 'gráfica', 'grafica')),
        ('transport', ('taxi', 'transport', 'transfer', 'mobility', 'delivery')),
    ]
    for category, keywords in category_keywords:
        if any(keyword in business_text for keyword in keywords):
            return category
    return 'generic_service'


def _choices_for_category(category):
    normalized_category = _normalize_category(category)
    return [_with_meta(item) for item in IMAGE_CHOICES if item['category'] == normalized_category]


def get_image_choices(category=None):
    if not category:
        return [_with_meta(item) for item in IMAGE_CHOICES]
    filtered = _choices_for_category(category)
    return filtered or [_with_meta(item) for item in IMAGE_CHOICES]


def get_image_by_key(key):
    normalized_key = str(key or '').strip()
    for item in IMAGE_CHOICES:
        if item['key'] == normalized_key:
            return _with_meta(item)
    for item in IMAGE_CHOICES:
        if item['key'] == DEFAULT_IMAGE_KEY:
            return _with_meta(item)
    return _with_meta(IMAGE_CHOICES[0])


def get_default_image_for_business_type(business_type):
    category = _infer_category_from_business_type(business_type)
    category_choices = _choices_for_category(category)
    photo_choices = [item for item in category_choices if item['style_type'] == 'photo' and item['path_exists']]
    if photo_choices:
        return photo_choices[0]

    generic_photo_choices = [
        item for item in _choices_for_category('generic_service')
        if item['style_type'] == 'photo' and item['path_exists']
    ]
    if generic_photo_choices:
        return generic_photo_choices[0]

    return get_image_by_key(DEFAULT_IMAGE_KEY)


def get_alternate_image_for_business_type(business_type, current_key=None):
    current_item = get_image_by_key(current_key) if current_key else None
    category = _infer_category_from_business_type(business_type)

    def valid_alternates(items):
        results = []
        for item in items:
            if not item['path_exists']:
                continue
            if current_item and item['key'] == current_item['key']:
                continue
            if current_item and item['static_path'] == current_item['static_path']:
                continue
            results.append(item)
        return results

    category_choices = _choices_for_category(category)
    generic_choices = _choices_for_category('generic_service')

    category_photo_alternates = valid_alternates([item for item in category_choices if item['style_type'] == 'photo'])
    if category_photo_alternates:
        return category_photo_alternates[0]

    generic_photo_alternates = valid_alternates([item for item in generic_choices if item['style_type'] == 'photo'])
    if generic_photo_alternates:
        return generic_photo_alternates[0]

    category_any_alternates = valid_alternates(category_choices)
    if category_any_alternates:
        return category_any_alternates[0]

    generic_any_alternates = valid_alternates(generic_choices)
    if generic_any_alternates:
        return generic_any_alternates[0]

    return current_item or get_default_image_for_business_type(business_type)
