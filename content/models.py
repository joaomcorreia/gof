from urllib.parse import parse_qs, urlparse

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ArticleCategory(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = _('Article category')
        verbose_name_plural = _('Article categories')

    def __str__(self):
        return self.name


class Article(models.Model):
    class ArticleType(models.TextChoices):
        GUIDE = 'guide', _('Guide')
        SERVICE_EXPLANATION = 'service_explanation', _('Service explanation')
        FAQ = 'faq', _('FAQ')
        UPDATE = 'update', _('Update')
        PROMOTION = 'promotion', _('Promotion')

    class Visibility(models.TextChoices):
        PUBLIC = 'public', _('Public')
        LOGGED_IN = 'logged_in', _('Logged in')
        CUSTOMER_ONLY = 'customer_only', _('Customer only')
        ADMIN_ONLY = 'admin_only', _('Admin only')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PUBLISHED = 'published', _('Published')

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    excerpt = models.TextField(blank=True)
    body = models.TextField(blank=True)
    category = models.ForeignKey(
        ArticleCategory,
        on_delete=models.SET_NULL,
        related_name='articles',
        null=True,
        blank=True,
    )
    article_type = models.CharField(
        max_length=32,
        choices=ArticleType.choices,
        default=ArticleType.GUIDE,
    )
    visibility = models.CharField(
        max_length=32,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    language = models.CharField(max_length=10, default='en')
    show_on_blog = models.BooleanField(default=False)
    show_in_help_center = models.BooleanField(default=False)
    show_in_dashboard = models.BooleanField(default=False)
    dashboard_card_title = models.CharField(max_length=200, blank=True)
    dashboard_card_description = models.TextField(blank=True)
    featured_image = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    youtube_video_id = models.CharField(max_length=50, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', '-published_at', '-created_at', 'title']
        verbose_name = _('Article')
        verbose_name_plural = _('Articles')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.youtube_url and not self.youtube_video_id:
            self.youtube_video_id = self.extract_youtube_video_id(self.youtube_url)
        elif not self.youtube_url:
            self.youtube_video_id = ''

        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    @staticmethod
    def extract_youtube_video_id(url):
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if 'youtu.be' in host:
            return parsed.path.strip('/')
        if 'youtube.com' in host:
            if parsed.path == '/watch':
                return parse_qs(parsed.query).get('v', [''])[0]
            if parsed.path.startswith('/embed/'):
                return parsed.path.split('/embed/', 1)[1].strip('/')
        return ''

