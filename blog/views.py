from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _

from .models import BlogCategory, BlogPost


def active_language(request):
    return (getattr(request, 'LANGUAGE_CODE', 'en') or 'en').split('-', 1)[0]


def public_categories(language):
    return BlogCategory.objects.filter(
        language=language,
        is_public=True,
        posts__visibility=BlogPost.Visibility.PUBLIC,
    ).distinct()


def public_posts(language):
    return BlogPost.objects.public().for_language(language).select_related('category')


def users_only_posts(language):
    return BlogPost.objects.users_only().for_language(language).select_related('category')


def index(request):
    language = active_language(request)
    posts = public_posts(language)
    categories = public_categories(language)
    return render(
        request,
        'blog/index.html',
        {
            'page_title': _('Blog'),
            'page_intro': _(
                'Short articles, practical explanations, and useful information from Get Online Fast.'
            ),
            'posts': posts,
            'categories': categories,
        },
    )


def category_detail(request, slug):
    language = active_language(request)
    category = get_object_or_404(
        BlogCategory,
        slug=slug,
        language=language,
        is_public=True,
    )
    posts = public_posts(language).filter(category=category)
    return render(
        request,
        'blog/category.html',
        {
            'category': category,
            'posts': posts,
        },
    )


def detail(request, slug):
    language = active_language(request)
    post = get_object_or_404(
        public_posts(language),
        slug=slug,
    )
    return render(
        request,
        'blog/detail.html',
        {
            'post': post,
        },
    )


@login_required(login_url='/admin/login/')
def guides_index(request):
    language = active_language(request)
    posts = users_only_posts(language)
    return render(
        request,
        'dashboard/guides/index.html',
        {
            'page_title': _('Help & Guides'),
            'page_intro': _(
                'Practical guides for logged-in users who want to manage and improve their website.'
            ),
            'posts': posts,
            'recent_posts': posts[:6],
        },
    )


@login_required(login_url='/admin/login/')
def guides_detail(request, slug):
    language = active_language(request)
    post = get_object_or_404(
        users_only_posts(language),
        slug=slug,
    )
    recent_posts = users_only_posts(language).exclude(pk=post.pk)[:6]
    return render(
        request,
        'dashboard/guides/detail.html',
        {
            'post': post,
            'recent_posts': recent_posts,
        },
    )

