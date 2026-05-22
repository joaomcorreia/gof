from django.contrib import admin

from .models import Site, SiteContent, StarterOnboardingSubmission, Template


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'updated_at')
    search_fields = ('slug', 'name')


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'service_type', 'city', 'template_slug', 'created_at')
    search_fields = ('business_name', 'service_type', 'city', 'template_slug')


@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ('site', 'section_key', 'field_key', 'language', 'updated_at')
    list_filter = ('language', 'section_key')
    search_fields = ('site__business_name', 'section_key', 'field_key', 'value')


@admin.register(StarterOnboardingSubmission)
class StarterOnboardingSubmissionAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'business_type', 'city', 'created_at')
    search_fields = ('business_name', 'business_type', 'city')
