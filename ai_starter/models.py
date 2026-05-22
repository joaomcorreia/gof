import uuid

from django.conf import settings
from django.db import models


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
