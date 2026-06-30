from django.contrib import admin

from .models import ServiceOption


@admin.register(ServiceOption)
class ServiceOptionAdmin(admin.ModelAdmin):
    list_display = ('section_key', 'option_key', 'language', 'title', 'price_label', 'sort_order', 'is_active')
    list_filter = ('section_key', 'language', 'is_active')
    search_fields = ('title', 'option_key', 'summary')
    ordering = ('section_key', 'language', 'sort_order', 'id')
