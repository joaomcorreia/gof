from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _

from .models import Article


def _visible_article_queryset(request):
    queryset = Article.objects.filter(status=Article.Status.PUBLISHED)
    if request.user.is_staff or request.user.is_superuser:
        return queryset
    queryset = queryset.exclude(visibility=Article.Visibility.ADMIN_ONLY)
    if request.user.is_authenticated:
        return queryset
    return queryset.filter(visibility=Article.Visibility.PUBLIC)


def _get_section_article(request, slug, section_flag):
    article = get_object_or_404(
        Article.objects.select_related('category'),
        slug=slug,
        status=Article.Status.PUBLISHED,
        **{section_flag: True},
    )
    if article.visibility == Article.Visibility.ADMIN_ONLY:
        if request.user.is_staff or request.user.is_superuser:
            return article
        if request.user.is_authenticated:
            raise Http404
        return redirect_to_login(request.get_full_path(), login_url='/admin/login/')
    if article.visibility in {
        Article.Visibility.LOGGED_IN,
        Article.Visibility.CUSTOMER_ONLY,
    } and not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), login_url='/admin/login/')
    if article.visibility == Article.Visibility.PUBLIC or request.user.is_authenticated:
        return article
    raise Http404


def help_index(request):
    articles = _visible_article_queryset(request).filter(show_in_help_center=True)
    categories = [category for category in {
        article.category for article in articles if article.category is not None
    }]
    categories.sort(key=lambda category: (category.sort_order, category.name.lower()))
    return render(
        request,
        'content/help_index.html',
        {
            'page_title': _('Help'),
            'page_intro': _(
                'Practical guides, answers, and short explanations to help you use Get Online Fast.'
            ),
            'articles': articles,
            'categories': categories,
        },
    )


def help_detail(request, slug):
    article = _get_section_article(request, slug, 'show_in_help_center')
    if not isinstance(article, Article):
        return article
    return render(
        request,
        'content/help_detail.html',
        {
            'article': article,
            'back_label': _('Back to Help'),
        },
    )


def blog_index(request):
    articles = Article.objects.filter(
        status=Article.Status.PUBLISHED,
        visibility=Article.Visibility.PUBLIC,
        show_on_blog=True,
    ).select_related('category')
    return render(
        request,
        'content/blog_index.html',
        {
            'page_title': _('Blog'),
            'page_intro': _(
                'Updates, practical ideas, and short articles from Get Online Fast.'
            ),
            'articles': articles,
        },
    )


def blog_detail(request, slug):
    article = _get_section_article(request, slug, 'show_on_blog')
    if not isinstance(article, Article):
        return article
    return render(
        request,
        'content/blog_detail.html',
        {
            'article': article,
            'back_label': _('Back to Blog'),
        },
    )
