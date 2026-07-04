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
        'static_path': 'img/hero-library/beauty/hero/beauty-hero-salon-interior-01.png',
        'alt_text': 'Beauty or wellness hero photo',
        'style_type': 'photo',
    },
    {
        'key': 'beauty_02',
        'label': 'Salon treatment photo',
        'category': 'beauty',
        'static_path': 'img/hero-library/beauty/hero/beauty-hero-salon-treatment-01.png',
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
_DYNAMIC_LIBRARY_ROOT = _BASE_STATIC_DIR / 'img' / 'hero-library'
_DYNAMIC_LIBRARY_PREFIX = 'img/hero-library'
_SUPPORTED_IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp', '.svg'}
_PURPOSE_FOLDERS = {
    'hero': {'hero'},
    'gallery': {'salon-interior', 'spa-wellness', 'hair', 'nails', 'makeup-facial', 'skincare-products', 'extras-generic'},
    'background': {'backgrounds-neutral'},
    'service': {'hair', 'nails', 'makeup-facial', 'spa-wellness', 'skincare-products'},
    'detail': {'makeup-facial', 'skincare-products', 'hair', 'nails'},
    'before_after': {'before-after'},
}
_DYNAMIC_IMAGE_CACHE = None


def _path_exists(static_path):
    return (_BASE_STATIC_DIR / Path(static_path)).exists()


def _display_label(item):
    prefix = 'Photo' if item.get('style_type') == 'photo' else 'Placeholder'
    return f'{prefix}: {item["label"]}'


def _with_meta(item):
    enriched = dict(item)
    enriched['path_exists'] = _path_exists(item['static_path'])
    enriched['option_label'] = _display_label(item)
    enriched.setdefault('purpose', 'hero')
    enriched.setdefault('subcategory', enriched.get('category', 'generic_service'))
    enriched.setdefault('source_root', 'legacy')
    return enriched


def _normalize_category(category):
    normalized = str(category or '').strip().lower()
    return normalized or 'generic_service'


def _infer_category_from_business_type(business_type):
    business_text = str(business_type or '').strip().lower()
    category_keywords = [
        (
            'garage',
            (
                'garage', 'oficina', 'mechanic', 'mechanic shop', 'auto repair', 'car repair',
                'automotive', 'vehicle repair', 'car service', 'workshop', 'bodywork',
                'mot', 'apk', 'tyre', 'tire',
            ),
        ),
        (
            'construction',
            (
                'construction', 'builder', 'contractor', 'renovation', 'handyman',
                'roofing', 'carpenter', 'electrician', 'plumber', 'painter',
            ),
        ),
        ('restaurant', ('restaurant', 'cafe', 'cafeteria', 'food', 'pizza', 'bar')),
        ('beauty', ('beauty', 'beauty salon', 'salon', 'spa', 'barber', 'hair', 'wellness', 'makeup', 'make-up', 'facial', 'skincare', 'skin care', 'nail', 'nails', 'manicure', 'pedicure')),
        ('shop', ('shop', 'store', 'drogist', 'retail', 'catalog', 'print shop', 'printing', 'gráfica', 'grafica')),
        ('transport', ('taxi', 'transport', 'transfer', 'mobility', 'delivery', 'courier', 'airport transfer')),
    ]
    for category, keywords in category_keywords:
        if any(keyword in business_text for keyword in keywords):
            return category
    return 'generic_service'


def _beauty_subcategory_for_business_type(business_type):
    business_text = str(business_type or '').strip().lower()
    if any(term in business_text for term in ('nail', 'nails', 'manicure', 'pedicure')):
        return 'nails'
    if any(term in business_text for term in ('makeup', 'make-up', 'facial', 'skincare', 'skin care')):
        return 'makeup-facial'
    if 'hair' in business_text:
        return 'hair'
    if any(term in business_text for term in ('spa', 'wellness', 'massage')):
        return 'spa-wellness'
    return 'beauty'


def _dynamic_folder_to_purpose(folder_name):
    normalized = str(folder_name or '').strip().lower()
    for purpose, folders in _PURPOSE_FOLDERS.items():
        if normalized in folders:
            return purpose
    return 'gallery'


def _scan_dynamic_library():
    items = []
    if not _DYNAMIC_LIBRARY_ROOT.exists():
        return items

    for category_dir in sorted(_DYNAMIC_LIBRARY_ROOT.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name.strip().lower()
        for asset_path in sorted(category_dir.rglob('*')):
            if not asset_path.is_file() or asset_path.suffix.lower() not in _SUPPORTED_IMAGE_SUFFIXES:
                continue
            relative_path = asset_path.relative_to(_BASE_STATIC_DIR).as_posix()
            subcategory = asset_path.parent.name.strip().lower()
            items.append(
                {
                    'key': asset_path.stem,
                    'label': f"{category.replace('_', ' ').title()} {subcategory.replace('-', ' ').title()} {asset_path.stem.replace('-', ' ')}",
                    'category': category,
                    'subcategory': subcategory or category,
                    'purpose': _dynamic_folder_to_purpose(subcategory),
                    'static_path': relative_path,
                    'alt_text': f'{category.replace("_", " ")} image',
                    'style_type': 'photo',
                    'source_root': _DYNAMIC_LIBRARY_PREFIX,
                }
            )
    return items


def _all_image_choices():
    global _DYNAMIC_IMAGE_CACHE
    if _DYNAMIC_IMAGE_CACHE is None:
        _DYNAMIC_IMAGE_CACHE = _scan_dynamic_library()
    return IMAGE_CHOICES + _DYNAMIC_IMAGE_CACHE


def _dedupe_items(items):
    seen = set()
    deduped = []
    for item in items:
        key = item.get('key')
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _beauty_purpose_order(subcategory, purpose):
    orders = {
        'nails': {
            'hero': ['nails', 'hero', 'salon-interior'],
            'gallery': ['nails', 'salon-interior', 'before-after'],
            'service': ['nails', 'makeup-facial', 'salon-interior'],
            'detail': ['nails', 'before-after', 'makeup-facial'],
            'background': ['backgrounds-neutral'],
            'before_after': ['before-after', 'nails'],
        },
        'makeup-facial': {
            'hero': ['makeup-facial', 'hero', 'salon-interior'],
            'gallery': ['makeup-facial', 'skincare-products', 'before-after'],
            'service': ['makeup-facial', 'skincare-products', 'salon-interior'],
            'detail': ['makeup-facial', 'before-after', 'skincare-products'],
            'background': ['backgrounds-neutral'],
            'before_after': ['before-after', 'makeup-facial'],
        },
        'hair': {
            'hero': ['hair', 'hero', 'salon-interior'],
            'gallery': ['hair', 'salon-interior', 'before-after'],
            'service': ['hair', 'salon-interior', 'makeup-facial'],
            'detail': ['hair', 'before-after', 'salon-interior'],
            'background': ['backgrounds-neutral'],
            'before_after': ['before-after', 'hair'],
        },
        'spa-wellness': {
            'hero': ['spa-wellness', 'hero', 'salon-interior'],
            'gallery': ['spa-wellness', 'salon-interior', 'skincare-products'],
            'service': ['spa-wellness', 'skincare-products', 'salon-interior'],
            'detail': ['spa-wellness', 'skincare-products', 'before-after'],
            'background': ['backgrounds-neutral'],
            'before_after': ['before-after', 'spa-wellness'],
        },
        'beauty': {
            'hero': ['hero', 'salon-interior', 'spa-wellness'],
            'gallery': ['salon-interior', 'makeup-facial', 'nails', 'hair', 'spa-wellness'],
            'service': ['makeup-facial', 'nails', 'hair', 'spa-wellness', 'skincare-products'],
            'detail': ['makeup-facial', 'skincare-products', 'nails', 'hair'],
            'background': ['backgrounds-neutral'],
            'before_after': ['before-after', 'makeup-facial', 'nails'],
        },
    }
    return orders.get(subcategory, orders['beauty']).get(purpose, ['hero'])


def resolve_business_images(business_type, *, purpose='hero', limit=None):
    category = _infer_category_from_business_type(business_type)
    requested_purpose = str(purpose or 'hero').strip().lower() or 'hero'
    all_items = [_with_meta(item) for item in _all_image_choices()]
    results = []

    if category == 'beauty':
        beauty_subcategory = _beauty_subcategory_for_business_type(business_type)
        subcategory_order = _beauty_purpose_order(beauty_subcategory, requested_purpose)
        beauty_items = [
            item for item in all_items
            if item['category'] == 'beauty' and item['source_root'] == _DYNAMIC_LIBRARY_PREFIX and item['path_exists']
        ]
        exact_match_order = list(subcategory_order)
        if requested_purpose == 'hero' and beauty_subcategory != 'beauty':
            exact_match_order = [subcategory for subcategory in subcategory_order if subcategory != 'hero']
        for preferred_subcategory in exact_match_order:
            results.extend(
                item for item in beauty_items
                if item.get('subcategory') == preferred_subcategory and item.get('purpose') == requested_purpose
            )
        if not results:
            for preferred_subcategory in subcategory_order:
                results.extend(
                    item for item in beauty_items
                    if item.get('subcategory') == preferred_subcategory
                )
        if not results and requested_purpose == 'hero' and beauty_subcategory != 'beauty':
            results.extend(
                item for item in beauty_items
                if item.get('subcategory') == 'hero' and item.get('purpose') == 'hero'
            )

    if not results:
        results.extend(
            item for item in all_items
            if item['category'] == category and item['style_type'] == 'photo' and item['path_exists']
        )

    if not results and category != 'generic_service':
        results.extend(
            item for item in all_items
            if item['category'] == 'generic_service' and item['style_type'] == 'photo' and item['path_exists']
        )

    deduped = _dedupe_items(results)
    if limit is not None:
        return deduped[:max(0, int(limit))]
    return deduped


def _choices_for_category(category):
    normalized_category = _normalize_category(category)
    return [_with_meta(item) for item in _all_image_choices() if item['category'] == normalized_category]


def get_image_choices(category=None):
    if not category:
        return [_with_meta(item) for item in _all_image_choices()]
    filtered = _choices_for_category(category)
    return filtered or [_with_meta(item) for item in _all_image_choices()]


def get_image_choices_for_business_type(business_type):
    category = _infer_category_from_business_type(business_type)
    category_items = []

    if category == 'beauty':
        beauty_items = []
        for purpose in ('hero', 'gallery', 'service', 'detail', 'background', 'before_after'):
            beauty_items.extend(resolve_business_images(business_type, purpose=purpose, limit=24))
        category_items = _dedupe_items(beauty_items)
    else:
        category_items = [
            _with_meta(item)
            for item in _all_image_choices()
            if _with_meta(item)['category'] == category
        ]

    remaining = [
        _with_meta(item)
        for item in _all_image_choices()
        if item['key'] not in {choice['key'] for choice in category_items}
    ]
    return _dedupe_items(category_items + remaining)


def get_image_by_key(key):
    normalized_key = str(key or '').strip()
    for item in _all_image_choices():
        if item['key'] == normalized_key:
            return _with_meta(item)
    for item in IMAGE_CHOICES:
        if item['key'] == DEFAULT_IMAGE_KEY:
            return _with_meta(item)
    return _with_meta(IMAGE_CHOICES[0])


def is_generic_placeholder_image_key(key):
    item = get_image_by_key(key)
    if not item:
        return True
    if item.get('style_type') == 'placeholder':
        return True
    return item.get('category') == 'generic_service'


def get_default_image_for_business_type(business_type):
    photo_choices = resolve_business_images(business_type, purpose='hero')
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
