from django.db import models


class ServiceOption(models.Model):
    SECTION_CATALOG_ECOMMERCE = 'catalog_ecommerce'
    SECTION_CHOICES = [
        (SECTION_CATALOG_ECOMMERCE, 'Catalog / eCommerce'),
    ]

    OPTION_STARTER_CATALOG = 'starter_catalog'
    OPTION_FULL_ECOMMERCE = 'full_ecommerce'
    OPTION_RESELLER_ECOMMERCE = 'reseller_ecommerce'
    OPTION_CHOICES = [
        (OPTION_STARTER_CATALOG, 'Starter catalog'),
        (OPTION_FULL_ECOMMERCE, 'Full eCommerce'),
        (OPTION_RESELLER_ECOMMERCE, 'Reseller eCommerce'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('nl', 'Dutch'),
    ]

    section_key = models.CharField(max_length=64, choices=SECTION_CHOICES, default=SECTION_CATALOG_ECOMMERCE)
    option_key = models.CharField(max_length=64, choices=OPTION_CHOICES)
    language = models.CharField(max_length=8, choices=LANGUAGE_CHOICES, default='en')
    eyebrow = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=200)
    price_label = models.CharField(max_length=120, blank=True)
    summary = models.TextField()
    good_for = models.TextField(blank=True)
    includes = models.TextField(blank=True)
    cta_label = models.CharField(max_length=120, blank=True)
    cta_url = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['section_key', 'language', 'sort_order', 'id']
        unique_together = [('section_key', 'option_key', 'language')]

    def __str__(self):
        return f'{self.section_key} | {self.language} | {self.title}'
