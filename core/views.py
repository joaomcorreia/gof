import random

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from ai_starter.forms import StarterOnboardingForm
from blog.models import BlogPost
from .forms import ContactForm

CONTACT_CAPTCHA_QUESTION_SESSION_KEY = 'contact_captcha_question'
CONTACT_CAPTCHA_ANSWER_SESSION_KEY = 'contact_captcha_answer'


def _set_contact_captcha(request):
    left = random.randint(1, 9)
    right = random.randint(1, 9)
    operator = random.choice(['+', '-'])

    if operator == '-':
        left, right = max(left, right), min(left, right)
        answer = left - right
    else:
        answer = left + right

    request.session[CONTACT_CAPTCHA_QUESTION_SESSION_KEY] = _('{left} {operator} {right} = ?').format(
        left=left,
        operator=operator,
        right=right,
    )
    request.session[CONTACT_CAPTCHA_ANSWER_SESSION_KEY] = str(answer)


def _get_contact_captcha_question(request):
    question = request.session.get(CONTACT_CAPTCHA_QUESTION_SESSION_KEY)
    answer = request.session.get(CONTACT_CAPTCHA_ANSWER_SESSION_KEY)
    if not question or answer is None:
        _set_contact_captcha(request)
        question = request.session[CONTACT_CAPTCHA_QUESTION_SESSION_KEY]
    return question


def home(request):
    language = (getattr(request, 'LANGUAGE_CODE', 'en') or 'en').split('-', 1)[0]
    return render(
        request,
        'core/home.html',
        {
            'onboarding_form': StarterOnboardingForm(),
            'onboarding_modal_open': False,
            'latest_public_blog_posts': BlogPost.objects.public().for_language(language).select_related('category')[:3],
        },
    )


def how_it_works(request):
    return render(request, 'core/how_it_works.html')


def examples(request):
    return render(request, 'core/examples.html')


def plans(request):
    return render(
        request,
        'core/plans.html',
        {
            'page_title': _('Plans'),
            'page_meta_description': _(
                'Compare website plans from Get Online Fast, including one-time websites, monthly support, and upcoming eCommerce options.'
            ),
            'plans': website_plans_overview_cards(),
        },
    )


def faq(request):
    return render(request, 'core/faq.html')


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            expected_answer = str(request.session.get(CONTACT_CAPTCHA_ANSWER_SESSION_KEY, '')).strip()
            provided_answer = form.cleaned_data['security_question'].strip()
            if not expected_answer or provided_answer != expected_answer:
                form.add_error('security_question', _('Please answer the security question correctly.'))
                messages.error(
                    request,
                    _('Please correct the errors below and try again.'),
                )
                _set_contact_captcha(request)
            else:
                body = _(
                    'Name: {name}\n'
                    'Email: {email}\n'
                    'Phone: {phone}\n'
                    '\n'
                    'Message:\n'
                    '{message}'
                ).format(
                    name=form.cleaned_data['name'],
                    email=form.cleaned_data['email'],
                    phone=form.cleaned_data['phone'] or _('Not provided'),
                    message=form.cleaned_data['message'],
                )
                email = EmailMessage(
                    subject=_('New Get Online Fast contact message'),
                    body=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.CONTACT_EMAIL_TO],
                    reply_to=[form.cleaned_data['email']],
                )
                try:
                    email.send(fail_silently=False)
                except Exception:
                    messages.error(
                        request,
                        _('Your message could not be sent right now. Please try again or contact us directly by email.'),
                    )
                else:
                    messages.success(
                        request,
                        _('Your message was sent successfully. We will get back to you soon.'),
                    )
                    _set_contact_captcha(request)
                    return redirect('core:contact')
        else:
            messages.error(
                request,
                _('Please correct the errors below and try again.'),
            )
    else:
        form = ContactForm()
        _set_contact_captcha(request)

    return render(
        request,
        'core/contact.html',
        {
            'form': form,
            'contact_captcha_question': _get_contact_captcha_question(request),
        },
    )


def privacy_policy(request):
    return render(request, 'core/privacy_policy.html')


def terms(request):
    return render(request, 'core/terms.html')


def one_time_website_plan(request):
    return render(
        request,
        'core/plan_one_time.html',
        {
            'onboarding_form': StarterOnboardingForm(),
            'onboarding_modal_open': False,
        },
    )


def monthly_plan(request):
    return render(
        request,
        'core/plan_monthly.html',
        {
            'onboarding_form': StarterOnboardingForm(),
            'onboarding_modal_open': False,
        },
    )


def ecommerce_plan(request):
    return render(request, 'core/plan_ecommerce.html')


def ai_website(request):
    return render(request, 'core/detail_page.html', ai_website_context())


def business_website(request):
    return render(request, 'core/detail_page.html', business_website_context())


def managed(request):
    return render(request, 'core/detail_page.html', managed_context())


def website_plans_overview_cards():
    return [
        {
            'title': _('One-Time Website'),
            'price': _('€325 + VAT'),
            'text': _('A full business website with clear structure, search-ready foundations, and a complete launch setup.'),
            'items': [
                _('Full business website'),
                _('Structured search setup'),
                _('Launch support included'),
            ],
            'cta': _('View One-Time Website'),
            'url_name': 'core:one_time_website_plan',
            'featured': True,
        },
        {
            'title': _('Monthly Website'),
            'price': _('€49.90 / month'),
            'text': _('A complete website setup with hosting, support, and ongoing improvements in one monthly plan.'),
            'items': [
                _('Hosting included'),
                _('Ongoing improvements'),
                _('Support included'),
            ],
            'cta': _('View Monthly Website'),
            'url_name': 'core:monthly_plan',
        },
        {
            'title': _('eCommerce Plan'),
            'badge': _('Coming Soon'),
            'price': _('Coming soon'),
            'text': _('A future option for businesses that want to sell products online.'),
            'items': [
                _('Product pages'),
                _('Shopping cart and checkout'),
                _('Small business store setup'),
            ],
            'cta': _('View eCommerce Plan'),
            'url_name': 'core:ecommerce_plan',
            'coming_soon': True,
        },
    ]


def plans_overview_cards():
    return [
        {
            'title': _('One-Time Website'),
            'price': _('€325 + VAT'),
            'text': _('A full business website with clear structure, SEO-ready foundations, and AI-assisted editing.'),
            'items': [
                _('Full business website'),
                _('Structured SEO setup'),
                _('AI-assisted content editing'),
            ],
            'cta': _('View One-Time Website'),
            'url_name': 'core:one_time_website_plan',
            'featured': True,
        },
        {
            'title': _('Monthly Plan'),
            'price': _('From €49.90 / month'),
            'text': _('Hosting, website care, small updates, and practical ongoing support in one plan.'),
            'items': [
                _('Hosting included'),
                _('Small updates'),
                _('Support when needed'),
            ],
            'cta': _('View Monthly Plan'),
            'url_name': 'core:monthly_plan',
        },
        {
            'title': _('eCommerce Plan'),
            'badge': _('Coming Soon'),
            'price': _('Coming soon'),
            'text': _('A future option for businesses that want to sell products online.'),
            'items': [
                _('Product pages'),
                _('Shopping cart and checkout'),
                _('Small business store setup'),
            ],
            'cta': _('View eCommerce Plan'),
            'url_name': 'core:ecommerce_plan',
            'coming_soon': True,
        },
    ]


def ai_website_context():
    return {
        'page_eyebrow': _('Fast launch option'),
        'page_title': _('AI Starter'),
        'page_intro': _(
            'A lightweight one-page website for small businesses that need to get online quickly at the lowest price.'
        ),
        'page_price': _('€50/year'),
        'page_price_note': _(
            'Best for testing a simple web presence before investing in a larger site.'
        ),
        'primary_cta_label': _('See One-Time Website'),
        'primary_cta_url_name': 'core:one_time_website_plan',
        'secondary_cta_label': _('Back to homepage'),
        'secondary_cta_url_name': 'core:home',
        'section_title': _('What AI Starter is for'),
        'section_intro': _(
            'This plan is intentionally limited. It gives a business a clear, usable page on a subdomain without the cost of a custom build.'
        ),
        'feature_cards': [
            {
                'title': _('Fastest route online'),
                'text': _('Start with a compact one-page site generated from your business basics and service information.'),
            },
            {
                'title': _('Simple setup'),
                'text': _('Good for businesses that need contact details, a short service summary, and a clean mobile-friendly presence.'),
            },
            {
                'title': _('Lower commitment'),
                'text': _('Useful when speed and budget matter more than customization, structure, or long-term flexibility.'),
            },
        ],
        'included_title': _('What is included'),
        'included_items': [
            _('One-page website'),
            _('Hosted on a project subdomain'),
            _('Business name, location, and service summary'),
            _('Mobile-friendly layout'),
            _('Path to upgrade later'),
        ],
        'fit_title': _('What it is not'),
        'fit_items': [
            _('Not a custom design build'),
            _('Not intended for complex service structures'),
            _('Not the best fit if SEO depth matters from day one'),
            _('Not a replacement for ongoing support or content work'),
        ],
        'bottom_cta_title': _('Need something stronger than the basic option?'),
        'bottom_cta_text': _(
            'The One-Time Website plan is the better fit if you want a more professional structure, stronger messaging, and room to grow.'
        ),
        'bottom_cta_label': _('View One-Time Website'),
        'bottom_cta_url_name': 'core:one_time_website_plan',
    }


def business_website_context():
    return {
        'page_eyebrow': _('Main offer'),
        'page_title': _('One-Time Website'),
        'page_intro': _(
            'A professional small-business website built with clear structure, stronger messaging, and a foundation for long-term growth.'
        ),
        'page_price': _('€325 + VAT'),
        'page_price_note': _(
            'Best for businesses that want to pay once and launch a serious public website.'
        ),
        'primary_cta_label': _('View Monthly Plan'),
        'primary_cta_url_name': 'core:monthly_plan',
        'secondary_cta_label': _('Back to homepage'),
        'secondary_cta_url_name': 'core:home',
        'section_title': _('Why this works as a one-time website'),
        'section_intro': _(
            'This is the offer for businesses that want a clear, complete website without ongoing website care bundled in.'
        ),
        'feature_cards': [
            {
                'title': _('Better structure'),
                'text': _('The site can be organized around your services, location, and real customer actions instead of a generic template block.'),
            },
            {
                'title': _('More trust from day one'),
                'text': _('A clearer layout, stronger content flow, and more professional setup help the business look established faster.'),
            },
            {
                'title': _('Easier to grow later'),
                'text': _('This package gives you a cleaner base for extra pages, content updates, and future improvements when needed.'),
            },
        ],
        'included_title': _('What is included'),
        'included_items': [
            _('Full business website'),
            _('Structured SEO setup'),
            _('AI-assisted content editing'),
            _('Built to help visitors contact your business'),
            _('Strong foundation for long-term growth'),
        ],
        'fit_title': _('Good fit if you want'),
        'fit_items': [
            _('A professional website with one payment'),
            _('A clearer offer and stronger conversion flow'),
            _('A site you can build on later'),
            _('A better balance between speed, quality, and budget'),
        ],
        'bottom_cta_title': _('Want help every month as well?'),
        'bottom_cta_text': _(
            'Choose the Monthly Plan if you want hosting, support, and ongoing website care handled for you.'
        ),
        'bottom_cta_label': _('View Monthly Plan'),
        'bottom_cta_url_name': 'core:monthly_plan',
    }


def managed_context():
    return {
        'page_eyebrow': _('Ongoing support'),
        'page_title': _('Monthly Plan'),
        'page_intro': _(
            'A monthly website plan for businesses that want hosting, updates, support, and ongoing care handled for them.'
        ),
        'page_price': _('From €49.90/month'),
        'page_price_note': _(
            'Best for owners who want continuity instead of handling every change themselves.'
        ),
        'primary_cta_label': _('View One-Time Website'),
        'primary_cta_url_name': 'core:one_time_website_plan',
        'secondary_cta_label': _('Back to homepage'),
        'secondary_cta_url_name': 'core:home',
        'section_title': _('What the monthly plan covers'),
        'section_intro': _(
            'This plan keeps the website online and looked after after launch. It is meant for practical ongoing support, not a full rebuild every month.'
        ),
        'feature_cards': [
            {
                'title': _('Content edits'),
                'text': _('Update text, swap images, adjust key sections, and keep the website current as the business changes.'),
            },
            {
                'title': _('Priority support'),
                'text': _('Get a simpler path for small requests and future website improvements without starting from zero each time.'),
            },
            {
                'title': _('Less owner hassle'),
                'text': _('Useful for businesses that would rather stay focused on clients and operations than website maintenance.'),
            },
        ],
        'included_title': _('What is included'),
        'included_items': [
            _('Hosting included'),
            _('Website stays online'),
            _('Small updates and support'),
            _('Ongoing website care'),
            _('Optional Facebook posts add-on'),
        ],
        'fit_title': _('Good fit if you want'),
        'fit_items': [
            _('Someone to handle routine website updates'),
            _('A simpler way to request changes after launch'),
            _('Support without building an in-house workflow'),
            _('A site that stays maintained instead of going stale'),
        ],
        'bottom_cta_title': _('Need the website build first?'),
        'bottom_cta_text': _(
            'Start with the One-Time Website if you prefer to pay once and add services later.'
        ),
        'bottom_cta_label': _('View One-Time Website'),
        'bottom_cta_url_name': 'core:one_time_website_plan',
    }
