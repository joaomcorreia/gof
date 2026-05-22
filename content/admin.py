from django.contrib import admin

from .models import Article, ArticleCategory


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order', 'updated_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('sort_order', 'name')


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'article_type',
        'visibility',
        'status',
        'language',
        'show_in_help_center',
        'show_on_blog',
        'show_in_dashboard',
        'published_at',
        'updated_at',
    )
    list_filter = (
        'status',
        'visibility',
        'article_type',
        'language',
        'show_in_help_center',
        'show_on_blog',
        'show_in_dashboard',
        'category',
    )
    search_fields = (
        'title',
        'slug',
        'excerpt',
        'body',
        'meta_title',
        'meta_description',
        'dashboard_card_title',
        'dashboard_card_description',
    )
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('category',)
    date_hierarchy = 'published_at'
    ordering = ('sort_order', '-published_at', '-updated_at')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'excerpt', 'body', 'category')
        }),
        ('Publishing', {
            'fields': ('article_type', 'visibility', 'status', 'language', 'published_at', 'sort_order')
        }),
        ('Placement', {
            'fields': (
                'show_in_help_center',
                'show_on_blog',
                'show_in_dashboard',
                'dashboard_card_title',
                'dashboard_card_description',
            )
        }),
        ('Media', {
            'fields': ('featured_image', 'youtube_url', 'youtube_video_id')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

