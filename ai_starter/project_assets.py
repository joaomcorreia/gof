from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from django.templatetags.static import static

PROJECT_ASSET_ROOT = Path(__file__).resolve().parent.parent / 'static' / 'core' / 'img' / 'template-assets'
PROJECT_ASSET_STATIC_PREFIX = 'core/img/template-assets'
ALLOWED_ASSET_TYPES = {
    'logo',
    'hero',
    'services',
    'portfolio',
    'backgrounds',
}
ALLOWED_IMAGE_EXTENSIONS = {
    '.jpg',
    '.jpeg',
    '.png',
    '.webp',
    '.svg',
}
_SAFE_FILENAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')


def normalize_project_slug(slug):
    raw_slug = str(slug or '').strip()
    if not raw_slug or '..' in raw_slug or '/' in raw_slug or '\\' in raw_slug:
        return ''

    normalized = unicodedata.normalize('NFKD', raw_slug)
    normalized = normalized.encode('ascii', 'ignore').decode('ascii')
    normalized = normalized.strip().lower().replace('_', '-').replace(' ', '-')
    normalized = re.sub(r'[^a-z0-9-]+', '-', normalized)
    normalized = re.sub(r'-{2,}', '-', normalized).strip('-')
    return normalized


def _validate_asset_type(asset_type):
    normalized = str(asset_type or '').strip().lower()
    if normalized not in ALLOWED_ASSET_TYPES:
        raise ValueError(f'Unsupported asset type: {asset_type}')
    return normalized


def _is_safe_filename(filename):
    name = str(filename or '').strip()
    if not name or Path(name).name != name:
        return False
    if not _SAFE_FILENAME_RE.match(name):
        return False
    return Path(name).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS


def _project_asset_dir(project_slug, asset_type):
    normalized_slug = normalize_project_slug(project_slug)
    if not normalized_slug:
        return '', None
    validated_type = _validate_asset_type(asset_type)
    return normalized_slug, PROJECT_ASSET_ROOT / normalized_slug / validated_type


def _relative_project_asset_path(project_slug, asset_type, filename):
    return f'template-assets/{project_slug}/{asset_type}/{filename}'


def _asset_entry(project_slug, asset_type, filename):
    static_path = f'{PROJECT_ASSET_STATIC_PREFIX}/{project_slug}/{asset_type}/{filename}'
    relative_path = _relative_project_asset_path(project_slug, asset_type, filename)
    return {
        'filename': filename,
        'project_slug': project_slug,
        'asset_type': asset_type,
        'static_path': static_path,
        'url': static(static_path),
        'relative_path': relative_path,
    }


def list_project_assets(project_slug, asset_type):
    normalized_slug, asset_dir = _project_asset_dir(project_slug, asset_type)
    if not normalized_slug or asset_dir is None or not asset_dir.exists():
        return []

    assets = []
    for path in sorted(asset_dir.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file():
            continue
        if not _is_safe_filename(path.name):
            continue
        assets.append(_asset_entry(normalized_slug, asset_type, path.name))
    return assets


def get_project_asset_url(project_slug, asset_type, filename):
    normalized_slug, asset_dir = _project_asset_dir(project_slug, asset_type)
    if not normalized_slug or asset_dir is None or not _is_safe_filename(filename):
        return ''

    candidate = asset_dir / Path(filename).name
    if not candidate.exists() or not candidate.is_file():
        return ''
    return _asset_entry(normalized_slug, asset_type, candidate.name)['url']


def get_first_project_asset(project_slug, asset_type):
    assets = list_project_assets(project_slug, asset_type)
    return assets[0] if assets else None
