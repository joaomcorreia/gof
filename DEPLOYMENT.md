# Get Online Fast deployment notes

Target: CyberPanel Python App on Hostinger.

## Production settings

Create a `.env` file on the server from `.env.example` and set real values:

- `DJANGO_DEBUG=False`
- `DJANGO_SECRET_KEY=<long random secret>`
- `DJANGO_ALLOWED_HOSTS=getonlinefast.eu,www.getonlinefast.eu`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://getonlinefast.eu,https://www.getonlinefast.eu`
- `DJANGO_SESSION_COOKIE_SECURE=True`
- `DJANGO_CSRF_COOKIE_SECURE=True`
- `DJANGO_SECURE_SSL_REDIRECT=False`
- `DJANGO_SECURE_HSTS_SECONDS=0`
- `STATIC_ROOT=staticfiles`
- `MEDIA_ROOT=media`

Keep `DJANGO_SECURE_SSL_REDIRECT=False` if CyberPanel/OpenLiteSpeed handles HTTPS redirects. Enable `DJANGO_SECURE_HSTS_SECONDS` only after confirming the live domain and HTTPS setup are stable.

The default database is SQLite at `db.sqlite3`. For a larger production setup, move to MySQL later and install/configure the required database driver.

## WSGI entry

Use:

```text
passenger_wsgi.py
```

The Django WSGI application path inside the project is:

```text
config.wsgi.application
```

## Server commands

Run these from the project directory on the server:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

## Static/media

`collectstatic` writes to:

```text
staticfiles/
```

Configure CyberPanel/OpenLiteSpeed to serve:

- URL `/static/` from `<project>/staticfiles/`
- URL `/media/` from `<project>/media/` if user uploads are added later

## Upload

Upload the project code, including:

- `ai_starter/`
- `config/`
- `core/`
- `locale/`
- `static/`
- `templates/`
- `manage.py`
- `requirements.txt`
- `passenger_wsgi.py`
- `.env` on the server only

Do not upload local-only generated files:

- `.env` with development secrets
- `.venv/`
- `__pycache__/`
- local `db.sqlite3` unless intentionally using it as the first production database
- `staticfiles/` unless CyberPanel cannot run `collectstatic`
