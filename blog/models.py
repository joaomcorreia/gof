from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


LANGUAGE_CHOICES = tuple(settings.LANGUAGES)


class BlogCategory(models.Model):
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    description = models.TextField(blank=True)
    image = models.URLField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='children',
        null=True,
        blank=True,
    )
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    is_public = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        constraints = [
            models.UniqueConstraint(
                fields=['slug', 'language'],
                name='unique_blog_category_slug_per_language',
            )
        ]
        verbose_name = _('Blog category')
        verbose_name_plural = _('Blog categories')

    def __str__(self):
        return self.title


class BlogPostQuerySet(models.QuerySet):
    def for_language(self, language):
        return self.filter(language=language)

    def public(self):
        return self.filter(visibility=BlogPost.Visibility.PUBLIC)

    def users_only(self):
        return self.filter(visibility=BlogPost.Visibility.USERS_ONLY)

    def published(self):
        return self.exclude(visibility=BlogPost.Visibility.DRAFT)


class BlogPost(models.Model):
    class Visibility(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PUBLIC = 'public', _('Public')
        USERS_ONLY = 'users_only', _('Users only')

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240)
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.PROTECT,
        related_name='posts',
    )
    excerpt = models.TextField(blank=True)
    body = models.TextField(blank=True)
    featured_image = models.URLField(blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.DRAFT,
    )
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    meta_title = models.CharField(max_length=220, blank=True)
    meta_description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BlogPostQuerySet.as_manager()

    class Meta:
        ordering = ['order', '-published_at', '-created_at', 'title']
        constraints = [
            models.UniqueConstraint(
                fields=['slug', 'language'],
                name='unique_blog_post_slug_per_language',
            )
        ]
        verbose_name = _('Blog post')
        verbose_name_plural = _('Blog posts')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.visibility != self.Visibility.DRAFT and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def display_image(self):
        if self.featured_image:
            return self.featured_image
        return self.category.image

    @property
    def seo_title(self):
        return self.meta_title or self.title

    @property
    def seo_description(self):
        return self.meta_description or self.excerpt

    def get_absolute_url(self):
        return reverse('blog:detail', kwargs={'slug': self.slug})

    def get_dashboard_url(self):
        return reverse('blog:guides_detail', kwargs={'slug': self.slug})

