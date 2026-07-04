import uuid

from django.conf import settings
from django.db import models
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateUploadStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('location', settings.BASE_DIR / 'private_uploads')
        super().__init__(*args, **kwargs)


website_request_storage = PrivateUploadStorage()


def build_request_storage_key():
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'{timestamp}-{uuid.uuid4().hex[:10]}'


def request_file_upload_path(instance, filename):
    safe_name = get_valid_filename(filename or 'upload')
    return f'website_requests/{instance.website_request.storage_key}/{safe_name}'


class StarterOnboardingSubmission(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    business_name = models.CharField(max_length=120)
    business_type = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    short_description = models.TextField()
    phone = models.CharField(max_length=40)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.business_name


class WebsiteRequest(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        REVIEWED = 'reviewed', 'Reviewed'
        CONTACTED = 'contacted', 'Contacted'
        CONVERTED = 'converted', 'Converted'
        CANCELLED = 'cancelled', 'Cancelled'

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    storage_key = models.CharField(max_length=40, default=build_request_storage_key, unique=True, editable=False)
    source_code = models.CharField(max_length=40, default='GEMEENTE50')
    normal_price = models.DecimalField(max_digits=8, decimal_places=2, default=325)
    offer_price = models.DecimalField(max_digits=8, decimal_places=2, default=275)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    business_name = models.CharField(max_length=120)
    business_type = models.CharField(max_length=120)
    existing_website_url = models.URLField(blank=True)
    current_domain = models.CharField(max_length=255, blank=True)
    needs_domain_help = models.BooleanField(default=False)
    business_address = models.CharField(max_length=255, blank=True)
    service_area = models.CharField(max_length=255, blank=True)
    main_language = models.CharField(max_length=12)
    extra_languages = models.CharField(max_length=255, blank=True)
    contact_name = models.CharField(max_length=120)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=40, blank=True)
    contact_whatsapp = models.CharField(max_length=40, blank=True)
    main_services = models.TextField()
    business_description = models.TextField(blank=True)
    opening_hours = models.CharField(max_length=255, blank=True)
    social_links = models.TextField(blank=True)
    preferred_colors = models.CharField(max_length=255, blank=True)
    style_notes = models.TextField(blank=True)
    special_requests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.business_name} ({self.public_id})'


class WebsiteRequestFile(models.Model):
    website_request = models.ForeignKey(
        WebsiteRequest,
        on_delete=models.CASCADE,
        related_name='files',
    )
    file = models.FileField(upload_to=request_file_upload_path, storage=website_request_storage)
    original_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.original_name


class Template(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    layout_json = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Site(models.Model):
    class ColorPalette(models.TextChoices):
        ORANGE_BLACK = 'orange_black', 'Orange / Black'
        BLUE_DARK = 'blue_dark', 'Blue / Dark'
        GREEN_NEUTRAL = 'green_neutral', 'Green / Neutral'
        RED_CHARCOAL = 'red_charcoal', 'Red / Charcoal'

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='starter_sites',
    )
    template_slug = models.SlugField(max_length=80, default='local_service')
    color_palette = models.CharField(
        max_length=40,
        choices=ColorPalette.choices,
        default=ColorPalette.ORANGE_BLACK,
    )
    business_name = models.CharField(max_length=120)
    service_type = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.business_name


class SiteContent(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='contents')
    section_key = models.CharField(max_length=80)
    field_key = models.CharField(max_length=80)
    value = models.TextField(blank=True)
    language = models.CharField(max_length=12, default='en')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['section_key', 'field_key', 'language']
        constraints = [
            models.UniqueConstraint(
                fields=['site', 'section_key', 'field_key', 'language'],
                name='unique_site_content_field_per_language',
            )
        ]

    def __str__(self):
        return f'{self.site_id}:{self.section_key}:{self.field_key}:{self.language}'


class SiteHandoff(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PREPARED = 'prepared', 'Prepared'
        SENT = 'sent', 'Sent'
        APPLIED = 'applied', 'Applied'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        FAILED = 'failed', 'Failed'

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='handoffs',
    )
    website_request = models.ForeignKey(
        WebsiteRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handoffs',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    target_system = models.CharField(max_length=40, default='wordpress_jcw')
    wordpress_site_url = models.URLField(blank=True)
    wordpress_admin_url = models.URLField(blank=True)
    wordpress_user_reference = models.CharField(max_length=255, blank=True)
    handoff_payload = models.JSONField(default=dict, blank=True)
    staff_ai_brief = models.TextField(blank=True)
    staff_ai_brief_generated_at = models.DateTimeField(null=True, blank=True)
    staff_ai_brief_error = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prepared_site_handoffs',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']

    def __str__(self):
        return f'Handoff for {self.site.business_name} ({self.get_status_display()})'

    def refresh_payload(self, save=True):
        from .services_handoff import build_site_handoff_payload

        payload = build_site_handoff_payload(self.site, website_request=self.website_request)
        payload['wordpress_target'] = {
            'site_url': self.wordpress_site_url,
            'admin_url': self.wordpress_admin_url,
            'user_reference': self.wordpress_user_reference,
        }
        self.handoff_payload = payload

        if save:
            self.save(update_fields=['handoff_payload', 'updated_at'])

        return self.handoff_payload

    def mark_completed(self, save=True):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        if save:
            self.save(update_fields=['status', 'completed_at', 'updated_at'])
        return self

    def generate_staff_ai_brief(self, save=True):
        from .services_ai import generate_handoff_brief
        self.refresh_payload()

        try:
            brief = generate_handoff_brief(self)
        except Exception as exc:
            self.staff_ai_brief_error = str(exc).strip() or 'Could not generate staff AI brief.'
            if save:
                self.save(update_fields=['staff_ai_brief_error', 'updated_at'])
            raise

        self.staff_ai_brief = brief
        self.staff_ai_brief_generated_at = timezone.now()
        self.staff_ai_brief_error = ''

        if save:
            self.save(
                update_fields=[
                    'staff_ai_brief',
                    'staff_ai_brief_generated_at',
                    'staff_ai_brief_error',
                    'updated_at',
                ]
            )

        return self.staff_ai_brief
