from django.contrib import admin
from django.utils.html import format_html

from .models import BlogCategory, BlogPost


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'language',
        'parent',
        'is_public',
        'order',
        'image_preview',
        'updated_at',
    )
    list_filter = ('language', 'is_public', 'parent')
    search_fields = ('title', 'slug', 'description')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('order', 'title')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'image')
        }),
        ('Structure', {
            'fields': ('parent', 'language', 'is_public', 'order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Image')
    def image_preview(self, obj):
        if not obj.image:
            return '—'
        return format_html('<img src="{}" alt="" style="height:40px;width:64px;object-fit:cover;border-radius:8px;">', obj.image)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'visibility',
        'language',
        'is_featured',
        'order',
        'published_at',
        'image_preview',
        'updated_at',
    )
    list_filter = ('language', 'category', 'visibility', 'is_featured')
    search_fields = ('title', 'excerpt', 'body', 'meta_title', 'meta_description')
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('category',)
    ordering = ('order', '-published_at', 'title')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'category', 'excerpt', 'body', 'featured_image')
        }),
        ('Publishing', {
            'fields': ('visibility', 'language', 'is_featured', 'order', 'published_at')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Image')
    def image_preview(self, obj):
        if not obj.display_image:
            return '—'
        return format_html('<img src="{}" alt="" style="height:40px;width:64px;object-fit:cover;border-radius:8px;">', obj.display_image)

