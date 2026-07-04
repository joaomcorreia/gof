import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, override

from ai_starter.forms import StarterOnboardingForm
from ai_starter.template_catalog import available_template_cards, default_template_slug, get_template_card
from blog.models import BlogPost
from .forms import ContactForm
from .models import ServiceOption
from .services_public_assistant import build_public_assistant_response, public_assistant_status
from .template_catalog import template_catalog, template_category_details, template_category_order

CONTACT_CAPTCHA_QUESTION_SESSION_KEY = 'contact_captcha_question'
CONTACT_CAPTCHA_ANSWER_SESSION_KEY = 'contact_captcha_answer'


PUBLIC_INFO_PAGE_LINKS = {
    'contact': {'url_name': 'core:contact', 'label': _('Contact')},
    'plans': {'url_name': 'core:plans', 'label': _('Plans')},
    'terms': {'url_name': 'core:terms', 'label': _('Terms')},
    'privacy': {'url_name': 'core:privacy_policy', 'label': _('Privacy Policy')},
    'support': {'url_name': 'core:support', 'label': _('Support')},
    'cookies': {'url_name': 'core:cookie_policy', 'label': _('Cookie Policy')},
    'what_is_included': {'url_name': 'core:what_is_included', 'label': _('What is included')},
    'payment_and_cancellation': {'url_name': 'core:payment_and_cancellation', 'label': _('Payment & Cancellation')},
    'domain_hosting_dashboard': {'url_name': 'core:domain_hosting_and_dashboard', 'label': _('Domain, hosting & dashboard')},
    'addons_upgrades': {'url_name': 'core:addons_and_upgrades', 'label': _('Add-ons & upgrades')},
    'catalog_and_ecommerce': {'url_name': 'core:catalog_and_ecommerce', 'label': _('Catalogs and online shops')},
    'facebook_posts': {'url_name': 'core:facebook_posts', 'label': _('Facebook Posts')},
    'facebook_instagram_ads': {'url_name': 'core:facebook_instagram_ads', 'label': _('Facebook & Instagram Ads')},
    'google_ads': {'url_name': 'core:google_ads', 'label': _('Google Ads')},
    'linkedin_ads': {'url_name': 'core:linkedin_ads', 'label': _('LinkedIn Ads')},
    'preview_licence': {'url_name': 'core:preview_licence', 'label': _('Preview & demo licence')},
}


WEBSITE_PACKAGE_CONFIRMATION_CHECKBOXES = [
    {
        'name': 'confirm_authorised_payment',
        'label': _('I confirm that I am authorised to approve and pay for this website setup.'),
    },
    {
        'name': 'confirm_included_scope',
        'label': _('I understand what is included in this website setup.'),
    },
    {
        'name': 'confirm_custom_changes',
        'label': _('I understand that custom changes outside the agreed setup may be quoted or billed separately.'),
    },
    {
        'name': 'confirm_platform_basis',
        'label': _('I understand that the website uses WordPress together with the Get Online Fast / JCW website tools and theme setup.'),
    },
    {
        'name': 'confirm_content_rights',
        'label': _('I confirm that the content, images, logo and materials I provide may legally be used on my website.'),
    },
    {
        'name': 'confirm_legal_pages',
        'label': _('I have read and agree to the Terms and Privacy Policy.'),
    },
]

HMD_ACTIVATION_CONFIRMATION_CHECKBOXES = [
    {
        'name': 'confirm_authorised_payment',
        'label': 'Ik bevestig dat ik bevoegd ben om deze websiteactivatie voor HMD Klusbedrijf goed te keuren en te betalen.',
    },
    {
        'name': 'confirm_scope',
        'label': 'Ik begrijp wat er in deze website setup en handoff is inbegrepen.',
    },
    {
        'name': 'confirm_custom_work',
        'label': 'Ik begrijp dat extra maatwerk of aanvullende wijzigingen buiten deze setup apart kunnen worden geoffreerd.',
    },
    {
        'name': 'confirm_manual_handoff',
        'label': 'Ik begrijp dat Get Online Fast de activatie en handoff na betaling handmatig controleert en bevestigt.',
    },
    {
        'name': 'confirm_legal_pages',
        'label': 'Ik heb de gekoppelde voorwaarden en beleidsinformatie gelezen.',
    },
]

SERVICE_OPTION_FALLBACKS = {
    'en': {
        'section_title': 'Catalogs and online shops',
        'section_intro': (
            'Show products, take WhatsApp orders, or sell online with a WooCommerce shop. Start simple with a product catalog, '
            'then grow into checkout, payments, and a stronger store structure when your business needs it.'
        ),
        'pricing_note': (
            'Prices are starting prices and exclude VAT. Final pricing depends on the number of products, product structure, '
            'payment methods, shipping, languages, content preparation, and required integrations.'
        ),
        'options': [
            {
                'option_key': 'starter_catalog',
                'eyebrow': 'Starter Catalog',
                'title': 'Starter Catalog / WhatsApp Orders',
                'price_label': 'From €149 + VAT',
                'summary': (
                    'Best for small resellers, Avon-style sellers, menus, stock lists, parts, and simple product ranges. '
                    'Visitors browse products and order through WhatsApp, phone, or a contact form.'
                ),
                'good_for': [
                    'Small resellers',
                    'Avon-style sellers',
                    'Menus',
                    'Stock lists',
                    'Parts',
                    'Simple product ranges',
                ],
                'includes': [
                    'Product list or catalog pages',
                    'Product images and details',
                    'Categories if needed',
                    'WhatsApp/contact order button',
                    'No full checkout required',
                    'Can grow into a shop later',
                ],
                'cta_label': 'Ask about a catalog',
                'cta_url_name': 'core:contact',
            },
            {
                'option_key': 'full_ecommerce',
                'eyebrow': 'Full eCommerce',
                'title': 'Full eCommerce Shop',
                'price_label': 'From €595 + VAT',
                'summary': (
                    'Best for businesses that want customers to buy online with cart, checkout, and payment setup guidance through WooCommerce.'
                ),
                'good_for': [
                    'Businesses ready to sell online with checkout',
                ],
                'includes': [
                    'WooCommerce setup',
                    'Product pages and categories',
                    'Cart and checkout',
                    'Payment setup guidance',
                    'Shipping and tax/VAT structure',
                    'Shop dashboard',
                ],
                'cta_label': 'Ask about an online shop',
                'cta_url_name': 'core:contact',
            },
            {
                'option_key': 'reseller_ecommerce',
                'eyebrow': 'Reseller eCommerce',
                'title': 'eCommerce for Resellers',
                'price_label': 'From €1,250 + VAT',
                'summary': (
                    'Best for larger catalogs, specialist product ranges, trade products, vehicle parts, or reseller-style businesses '
                    'that need more structure than a basic shop.'
                ),
                'good_for': [
                    'Larger catalogs',
                    'Trade products',
                    'Vehicle/parts businesses',
                ],
                'includes': [
                    'Larger catalog structure',
                    'Product categories and filters',
                    'Quote/order enquiry flow',
                    'Reseller-style product presentation',
                    'Custom setup planning',
                    'Possible upgrade to checkout/payment flow',
                ],
                'cta_label': 'Discuss reseller eCommerce',
                'cta_url_name': 'core:contact',
            },
        ],
    },
    'nl': {
        'section_title': 'Catalogs and online shops',
        'section_intro': (
            'Toon producten, ontvang bestellingen via WhatsApp of verkoop online met een WooCommerce-webshop. '
            'Begin eenvoudig met een productcatalogus en groei later door naar checkout, betalingen en een sterkere shopstructuur wanneer je bedrijf daar klaar voor is.'
        ),
        'pricing_note': (
            'Prijzen zijn vanafprijzen en exclusief btw. De definitieve prijs hangt af van het aantal producten, de productstructuur, '
            'betaalmethoden, verzending, talen, contentvoorbereiding en eventuele koppelingen.'
        ),
        'options': [
            {
                'option_key': 'starter_catalog',
                'eyebrow': 'Starter Catalog',
                'title': 'Starter Catalog / WhatsApp Orders',
                'price_label': 'Vanaf €149 + btw',
                'summary': (
                    'Geschikt voor kleine resellers, Avon-achtige verkopers, menu’s, voorraadoverzichten, onderdelen en eenvoudige productreeksen. '
                    'Bezoekers bekijken producten en bestellen via WhatsApp, telefoon of een contactformulier.'
                ),
                'good_for': [
                    'Kleine resellers',
                    'Avon-achtige verkopers',
                    'Menu’s',
                    'Voorraadoverzichten',
                    'Onderdelen',
                    'Eenvoudige productreeksen',
                ],
                'includes': [
                    'Productlijst of cataloguspagina’s',
                    'Productafbeeldingen en details',
                    'Categorieën indien nodig',
                    'WhatsApp/contactknop voor bestellingen',
                    'Geen volledige checkout nodig',
                    'Kan later doorgroeien naar een shop',
                ],
                'cta_label': 'Vraag naar een catalogus',
                'cta_url_name': 'core:contact',
            },
            {
                'option_key': 'full_ecommerce',
                'eyebrow': 'Full eCommerce',
                'title': 'Full eCommerce Shop',
                'price_label': 'Vanaf €595 + btw',
                'summary': (
                    'Geschikt voor bedrijven die online willen verkopen met winkelwagen, checkout en begeleiding bij de betaalopzet via WooCommerce.'
                ),
                'good_for': [
                    'Bedrijven die online willen verkopen met checkout',
                ],
                'includes': [
                    'WooCommerce-setup',
                    'Productpagina’s en categorieën',
                    'Winkelwagen en checkout',
                    'Begeleiding bij de betaalopzet',
                    'Verzend- en btw-structuur',
                    'Shopdashboard',
                ],
                'cta_label': 'Vraag naar een webshop',
                'cta_url_name': 'core:contact',
            },
            {
                'option_key': 'reseller_ecommerce',
                'eyebrow': 'Reseller eCommerce',
                'title': 'eCommerce for Resellers',
                'price_label': 'Vanaf €1.250 + btw',
                'summary': (
                    'Geschikt voor grotere catalogi, specialistische productreeksen, handelsproducten, voertuigonderdelen of reseller-achtige bedrijven '
                    'die meer structuur nodig hebben dan een basiswebshop.'
                ),
                'good_for': [
                    'Grotere catalogi',
                    'Handelsproducten',
                    'Voertuig-/onderdelenbedrijven',
                ],
                'includes': [
                    'Grotere catalogusstructuur',
                    'Productcategorieën en filters',
                    'Offerte-/bestelaanvraagflow',
                    'Reseller-achtige productpresentatie',
                    'Planning van maatwerkopzet',
                    'Mogelijke uitbreiding naar checkout/betalingen',
                ],
                'cta_label': 'Bespreek reseller eCommerce',
                'cta_url_name': 'core:contact',
            },
        ],
    },
}

PROMOTION_SERVICE_FALLBACKS = {
    'en': {
        'section_title': 'Promote your website',
        'section_intro': (
            'A website is the foundation. Promotion helps people actually find it. Start with simple Facebook posts, local ads, '
            'or search campaigns and improve from there.'
        ),
        'pricing_note': (
            'Ad budget is not included. We help set up or prepare the promotion, but Facebook, Instagram, Google, or LinkedIn '
            'charge separately for clicks, views, or campaign spend.'
        ),
        'options': [
            {
                'option_key': 'facebook_posts',
                'eyebrow': 'Promotion',
                'title': 'Facebook Posts',
                'price_label': 'EUR 79 / month',
                'summary': 'Keep your Facebook page active with ready-made posts for your business. Useful for services, updates, offers, recent work, and local visibility.',
                'cta_label': 'View Facebook Posts',
                'cta_url_name': 'core:facebook_posts',
            },
            {
                'option_key': 'meta_ads',
                'eyebrow': 'Promotion',
                'title': 'Facebook & Instagram Ads',
                'price_label': 'From EUR 70',
                'summary': 'Reach local customers on Facebook and Instagram with simple campaigns for your services, offers, or website launch.',
                'cta_label': 'View Meta Ads',
                'cta_url_name': 'core:facebook_instagram_ads',
            },
            {
                'option_key': 'google_ads',
                'eyebrow': 'Promotion',
                'title': 'Google Ads',
                'price_label': 'From EUR 70',
                'summary': 'Show your business when people search for services like yours in your area. Good for urgent jobs, local services, and high-intent visitors.',
                'cta_label': 'View Google Ads',
                'cta_url_name': 'core:google_ads',
            },
            {
                'option_key': 'linkedin_ads',
                'eyebrow': 'Promotion',
                'title': 'LinkedIn Ads',
                'price_label': 'From EUR 70',
                'summary': 'Promote business services to professionals, companies, and decision-makers. Better for B2B offers than everyday consumer services.',
                'cta_label': 'View LinkedIn Ads',
                'cta_url_name': 'core:linkedin_ads',
            },
        ],
    },
    'nl': {
        'section_title': 'Promoot je website',
        'section_intro': (
            'Een website is de basis. Promotie helpt mensen om die website ook echt te vinden. Begin met eenvoudige Facebook posts, '
            'lokale advertenties of zoekcampagnes en verbeter stap voor stap.'
        ),
        'pricing_note': (
            'Advertentiebudget is niet inbegrepen. Wij helpen met de opzet of voorbereiding van de promotie, maar Facebook, Instagram, '
            'Google en LinkedIn rekenen apart voor klikken, weergaven of campagnebudget.'
        ),
        'options': [
            {
                'option_key': 'facebook_posts',
                'eyebrow': 'Promotie',
                'title': 'Facebook Posts',
                'price_label': 'EUR 79 / maand',
                'summary': 'Houd je Facebook-pagina actief met kant-en-klare posts voor je bedrijf. Handig voor diensten, updates, acties, recent werk en lokale zichtbaarheid.',
                'cta_label': 'Bekijk Facebook Posts',
                'cta_url_name': 'core:facebook_posts',
            },
            {
                'option_key': 'meta_ads',
                'eyebrow': 'Promotie',
                'title': 'Facebook & Instagram Ads',
                'price_label': 'Vanaf EUR 70',
                'summary': 'Bereik lokale klanten op Facebook en Instagram met eenvoudige campagnes voor je diensten, acties of website-lancering.',
                'cta_label': 'Bekijk Meta Ads',
                'cta_url_name': 'core:facebook_instagram_ads',
            },
            {
                'option_key': 'google_ads',
                'eyebrow': 'Promotie',
                'title': 'Google Ads',
                'price_label': 'Vanaf EUR 70',
                'summary': 'Laat je bedrijf zien wanneer mensen zoeken naar diensten zoals die van jou in jouw regio. Geschikt voor spoedklussen, lokale diensten en bezoekers met hoge intentie.',
                'cta_label': 'Bekijk Google Ads',
                'cta_url_name': 'core:google_ads',
            },
            {
                'option_key': 'linkedin_ads',
                'eyebrow': 'Promotie',
                'title': 'LinkedIn Ads',
                'price_label': 'Vanaf EUR 70',
                'summary': 'Promoot zakelijke diensten bij professionals, bedrijven en beslissers. Geschikter voor B2B-aanbod dan voor alledaagse consumentendiensten.',
                'cta_label': 'Bekijk LinkedIn Ads',
                'cta_url_name': 'core:linkedin_ads',
            },
        ],
    },
}

PROMOTION_PAGE_FALLBACKS = {
    'en': {
        'facebook_posts': {
            'eyebrow': 'Promotion',
            'title': 'Facebook Posts',
            'price_label': 'EUR 79 / month',
            'intro': 'Keep your business visible with regular Facebook posts prepared for your services, offers, updates, and recent work.',
            'sections': [
                {'title': 'What this is', 'paragraphs': ['A monthly content service for businesses that want their Facebook page to look active without having to write every post themselves.']},
                {'title': 'Good for', 'paragraphs': ['Local service businesses, trades, salons, restaurants, shops, and small companies that want steady visibility.']},
                {'title': 'What can be included', 'bullets': ['Service posts', 'Offer posts', 'Before/after style posts', 'Seasonal posts', 'Website launch posts', 'Trust-building posts', 'Simple call-to-action posts']},
                {'title': 'Important note', 'paragraphs': ['This is content preparation. It does not include paid advertising budget or automatic posting unless agreed separately.']},
            ],
            'cta_label': 'Request Facebook Posts',
        },
        'meta_ads': {
            'eyebrow': 'Promotion',
            'title': 'Facebook & Instagram Ads',
            'price_label': 'From EUR 70',
            'intro': 'Run simple local campaigns on Facebook and Instagram to promote your services, offers, or new website.',
            'sections': [
                {'title': 'What this is', 'paragraphs': ['A basic campaign setup or support service for businesses that want to reach more people on Meta platforms.']},
                {'title': 'Good for', 'paragraphs': ['Local offers, service awareness, website launches, seasonal campaigns, and businesses with visual work to show.']},
                {'title': 'What can be included', 'bullets': ['Campaign structure', 'Audience direction', 'Ad copy', 'Creative suggestions', 'Basic setup support', 'Campaign improvement notes']},
                {'title': 'Important note', 'paragraphs': ['Ad budget is not included. Meta charges separately for ad spend.']},
            ],
            'cta_label': 'Request Meta Ads Help',
        },
        'google_ads': {
            'eyebrow': 'Promotion',
            'title': 'Google Ads',
            'price_label': 'From EUR 70',
            'intro': 'Help customers find your business when they are already searching for your services.',
            'sections': [
                {'title': 'What this is', 'paragraphs': ['A simple Google Ads setup or support service for local businesses that want search visibility.']},
                {'title': 'Good for', 'paragraphs': ['Urgent services, local trades, repair services, professional services, and businesses where customers search before calling.']},
                {'title': 'What can be included', 'bullets': ['Basic campaign structure', 'Keyword direction', 'Ad text', 'Location targeting', 'Landing page suggestions', 'Improvement notes']},
                {'title': 'Important note', 'paragraphs': ['Ad budget is not included. Google charges separately for clicks and campaign spend.']},
            ],
            'cta_label': 'Request Google Ads Help',
        },
        'linkedin_ads': {
            'eyebrow': 'Promotion',
            'title': 'LinkedIn Ads',
            'price_label': 'From EUR 70',
            'intro': 'Promote business services to professionals, companies, and decision-makers.',
            'sections': [
                {'title': 'What this is', 'paragraphs': ['A simple LinkedIn promotion setup or support service for B2B companies.']},
                {'title': 'Good for', 'paragraphs': ['Professional services, B2B offers, recruitment-related visibility, consultants, agencies, and companies targeting other businesses.']},
                {'title': 'What can be included', 'bullets': ['Campaign direction', 'Audience suggestions', 'Ad copy', 'Offer positioning', 'Landing page suggestions', 'Improvement notes']},
                {'title': 'Important note', 'paragraphs': ['Ad budget is not included. LinkedIn charges separately for campaign spend and is usually more expensive than Facebook or Google.']},
            ],
            'cta_label': 'Request LinkedIn Ads Help',
        },
        'advice_title': 'Not sure which one fits?',
        'advice_text': 'For most small local businesses, Facebook Posts or Google Ads are usually the simplest first step.',
        'advice_button_label': 'Ask for advice',
    },
    'nl': {
        'facebook_posts': {
            'eyebrow': 'Promotie',
            'title': 'Facebook Posts',
            'price_label': 'EUR 79 / maand',
            'intro': 'Houd je bedrijf zichtbaar met regelmatige Facebook posts voor je diensten, acties, updates en recent werk.',
            'sections': [
                {'title': 'Wat dit is', 'paragraphs': ['Een maandelijkse contentservice voor bedrijven die hun Facebook-pagina actief willen laten ogen zonder zelf elke post te moeten schrijven.']},
                {'title': 'Geschikt voor', 'paragraphs': ['Lokale dienstverleners, vakbedrijven, salons, restaurants, winkels en kleine bedrijven die constant zichtbaar willen blijven.']},
                {'title': 'Wat kan inbegrepen zijn', 'bullets': ['Posts over diensten', 'Actieposts', 'Voor/na-achtige posts', 'Seizoensposts', 'Website-lanceringsposts', 'Vertrouwen-opbouwende posts', 'Eenvoudige call-to-action posts']},
                {'title': 'Belangrijke opmerking', 'paragraphs': ['Dit is contentvoorbereiding. Het omvat geen advertentiebudget of automatisch posten tenzij dat apart is afgesproken.']},
            ],
            'cta_label': 'Vraag Facebook Posts aan',
        },
        'meta_ads': {
            'eyebrow': 'Promotie',
            'title': 'Facebook & Instagram Ads',
            'price_label': 'Vanaf EUR 70',
            'intro': 'Draai eenvoudige lokale campagnes op Facebook en Instagram om je diensten, acties of nieuwe website te promoten.',
            'sections': [
                {'title': 'Wat dit is', 'paragraphs': ['Een basisservice voor campagne-opzet of ondersteuning voor bedrijven die meer mensen willen bereiken via Meta-platformen.']},
                {'title': 'Geschikt voor', 'paragraphs': ['Lokale acties, bekendheid voor diensten, website-lanceringen, seizoenscampagnes en bedrijven met visueel werk om te tonen.']},
                {'title': 'Wat kan inbegrepen zijn', 'bullets': ['Campagnestructuur', 'Richting voor doelgroep', 'Advertentietekst', 'Creatieve suggesties', 'Basis hulp bij opzet', 'Verbeternotities voor campagnes']},
                {'title': 'Belangrijke opmerking', 'paragraphs': ['Advertentiebudget is niet inbegrepen. Meta rekent advertentiekosten apart.']},
            ],
            'cta_label': 'Vraag hulp bij Meta Ads',
        },
        'google_ads': {
            'eyebrow': 'Promotie',
            'title': 'Google Ads',
            'price_label': 'Vanaf EUR 70',
            'intro': 'Help klanten je bedrijf te vinden wanneer ze al zoeken naar jouw diensten.',
            'sections': [
                {'title': 'Wat dit is', 'paragraphs': ['Een eenvoudige Google Ads-opzet of ondersteuningsservice voor lokale bedrijven die zoekzichtbaarheid willen.']},
                {'title': 'Geschikt voor', 'paragraphs': ['Spoeddiensten, lokale vakbedrijven, reparatieservices, professionele diensten en bedrijven waarbij klanten zoeken voordat ze bellen.']},
                {'title': 'Wat kan inbegrepen zijn', 'bullets': ['Basis campagnestructuur', 'Richting voor zoekwoorden', 'Advertentietekst', 'Locatietargeting', 'Suggesties voor landingspagina', 'Verbeternotities']},
                {'title': 'Belangrijke opmerking', 'paragraphs': ['Advertentiebudget is niet inbegrepen. Google rekent apart voor klikken en campagnebudget.']},
            ],
            'cta_label': 'Vraag hulp bij Google Ads',
        },
        'linkedin_ads': {
            'eyebrow': 'Promotie',
            'title': 'LinkedIn Ads',
            'price_label': 'Vanaf EUR 70',
            'intro': 'Promoot zakelijke diensten bij professionals, bedrijven en beslissers.',
            'sections': [
                {'title': 'Wat dit is', 'paragraphs': ['Een eenvoudige LinkedIn-promotie-opzet of ondersteuningsservice voor B2B-bedrijven.']},
                {'title': 'Geschikt voor', 'paragraphs': ['Professionele diensten, B2B-aanbiedingen, zichtbaarheid rond recruitment, consultants, agencies en bedrijven die andere bedrijven targeten.']},
                {'title': 'Wat kan inbegrepen zijn', 'bullets': ['Campagnerichting', 'Doelgroepsuggesties', 'Advertentietekst', 'Positionering van aanbod', 'Suggesties voor landingspagina', 'Verbeternotities']},
                {'title': 'Belangrijke opmerking', 'paragraphs': ['Advertentiebudget is niet inbegrepen. LinkedIn rekent campagnekosten apart en is meestal duurder dan Facebook of Google.']},
            ],
            'cta_label': 'Vraag hulp bij LinkedIn Ads',
        },
        'advice_title': 'Weet je niet zeker welke past?',
        'advice_text': 'Voor de meeste kleine lokale bedrijven zijn Facebook Posts of Google Ads meestal de eenvoudigste eerste stap.',
        'advice_button_label': 'Vraag advies',
    },
}

ASSISTANT_PUBLIC_KNOWLEDGE = {
    'en': {
        'greeting': (
            'Hi! I\'m the Get Online Fast helper. I can help with websites, plans, support, payment, and how the platform works. '
            'What would you like to know?'
        ),
        'fallback': (
            'I can mainly help with website plans, payment, support, business email, and the WordPress dashboard. '
            'Try asking "Which plan fits my business?" or "How does payment work?"'
        ),
        'plans': (
            'Get Online Fast offers practical website options for small businesses, including starter pages, one-time website setup, '
            'monthly website plans, and catalog or online shop options. The best starting overview is on {plans_url}.'
        ),
        'preview': (
            'Preview creation is not publicly available right now. Please contact Get Online Fast and we will help you choose the right website setup.'
        ),
        'ecommerce': (
            'Yes. Get Online Fast can help with product catalogs, WhatsApp ordering catalogs, and WordPress/WooCommerce online shops. '
            'Starter catalogs begin from €149 + VAT, full WooCommerce shop setup begins from €595 + VAT, and larger reseller eCommerce '
            'projects begin from €1,250 + VAT. Final pricing depends on products, payments, shipping, languages, and setup needs.'
        ),
        'promotion': (
            'Yes. Get Online Fast can also help promote your website after launch with Facebook posts, Meta ads, Google Ads support, '
            'or LinkedIn ads for B2B offers. A simple starting point is usually Facebook Posts or Google Ads, depending on your business.'
        ),
        'activation': (
            'When your website is ready for activation, Get Online Fast will provide the correct activation page or payment link. '
            'Payment is handled securely by Stripe. After payment, Get Online Fast checks the activation and handoff manually '
            'and will contact you if anything else is needed.'
        ),
        'payment': (
            'Payment is handled securely by Stripe. If you want to activate a website, Get Online Fast will provide the correct '
            'payment link or activation page. You can also review the payment information on {payment_url}. After payment, activation is checked manually.'
        ),
        'included': (
            'Get Online Fast offers practical website services for small businesses, including WordPress website setup, support, '
            'and optional growth services. The best overview is on {included_url}.'
        ),
        'support': (
            'Support is available through Get Online Fast. Use {support_url} for practical guidance and {contact_url} if you '
            'need direct contact about setup, payment, support, or extra work.'
        ),
        'dashboard': (
            'The WordPress dashboard is there for practical updates such as content, images, services, and projects where that '
            'is included in your website setup. If you need help with edits, use {support_url} or {contact_url}.'
        ),
        'email': (
            'Business email or domain email setup can be requested separately. If you want mailbox help or company email setup, '
            'use {contact_url} so Get Online Fast can confirm the scope.'
        ),
        'changes': (
            'Yes. Extra changes, edits, or additional work can be requested separately. They are not treated as '
            'unlimited by default, so it is best to ask through {contact_url}.'
        ),
        'company_legal': (
            'Get Online Fast is operated by Just Code Works, based in Amsterdam, the Netherlands. You can review the Terms at '
            '{terms_url}, the Privacy Policy at {privacy_url}, the Cookie Policy at {cookies_url}, and the payment information at '
            '{payment_url}. This assistant does not give legal advice.'
        ),
    },
    'nl': {
        'greeting': (
            'Hoi! Ik ben de Get Online Fast hulp. Ik kan je helpen met websites, pakketten, support, betaling en hoe het platform werkt. '
            'Waar wil je meer over weten?'
        ),
        'fallback': (
            'Ik kan vooral helpen met vragen over websitepakketten, betaling, support, e-mailadressen en het WordPress dashboard. '
            'Probeer bijvoorbeeld: "Welk pakket past bij mijn bedrijf?" of "Hoe werkt betalen?"'
        ),
        'plans': (
            'Get Online Fast biedt praktische website-opties voor kleine bedrijven, waaronder starter pages, eenmalige website setup, '
            'maandelijkse websiteplannen en catalogus- of webshopopties. Het beste startoverzicht staat op {plans_url}.'
        ),
        'preview': (
            'Preview creation is not publicly available right now. Please contact Get Online Fast and we will help you choose the right website setup.'
        ),
        'ecommerce': (
            'Ja. Get Online Fast kan helpen met productcatalogi, WhatsApp-bestelcatalogi en WordPress/WooCommerce-webshops. '
            'Starter catalogi beginnen vanaf €149 + btw, volledige WooCommerce-webshops vanaf €595 + btw en grotere reseller/eCommerce-projecten '
            'vanaf €1.250 + btw. De definitieve prijs hangt af van producten, betalingen, verzending, talen en de gewenste opzet.'
        ),
        'promotion': (
            'Ja. Get Online Fast kan ook helpen om je website na livegang te promoten met Facebook posts, Meta ads, Google Ads-ondersteuning '
            'of LinkedIn ads voor B2B-aanbiedingen. Voor veel kleine lokale bedrijven zijn Facebook Posts of Google Ads meestal de eenvoudigste eerste stap.'
        ),
        'activation': (
            'Wanneer je website klaar is voor activatie, stuurt Get Online Fast de juiste activatiepagina of betaallink. '
            'De betaling wordt veilig verwerkt via Stripe. Na betaling controleert Get Online Fast de activatie handmatig en '
            'nemen we contact op als er nog iets nodig is.'
        ),
        'payment': (
            'Betalen verloopt veilig via Stripe. Als je een website wilt activeren, ontvang je een betaallink of activatiepagina van Get Online Fast. '
            'Na betaling controleren we de activatie handmatig en nemen we contact op als er nog iets nodig is. Meer informatie staat op de pagina Betaling en annulering.'
        ),
        'included': (
            'Get Online Fast biedt praktische websitediensten voor kleine bedrijven, waaronder WordPress website setup, support '
            'en optionele groeidiensten. Het overzicht staat op {included_url}.'
        ),
        'support': (
            'Support verloopt via Get Online Fast. Gebruik {support_url} voor praktische hulp en {contact_url} als je direct contact '
            'nodig hebt over setup, betaling, support of extra werk.'
        ),
        'dashboard': (
            'Het WordPress dashboard is bedoeld voor praktische updates zoals teksten, afbeeldingen, diensten en projecten waar dat '
            'in je website setup is inbegrepen. Als je hulp nodig hebt met aanpassen, gebruik dan {support_url} of {contact_url}.'
        ),
        'email': (
            'Zakelijke e-mail of domeinmail kan apart worden aangevraagd. Als je hulp wilt met mailboxen of een bedrijfsadres, '
            'gebruik dan {contact_url} zodat Get Online Fast de scope kan bevestigen.'
        ),
        'changes': (
            'Ja. Extra wijzigingen, aanpassingen of meerwerk kunnen apart worden aangevraagd. Dat is niet standaard '
            'onbeperkt inbegrepen, dus vraag dit het beste aan via {contact_url}.'
        ),
        'company_legal': (
            'Get Online Fast wordt beheerd door Just Code Works, gevestigd in Amsterdam, Nederland. Je kunt de Voorwaarden bekijken op '
            '{terms_url}, de Privacy Policy op {privacy_url}, de Cookie Policy op {cookies_url} en de betalingsinformatie op '
            '{payment_url}. Deze assistent geeft geen juridisch advies.'
        ),
    },
}

ASSISTANT_INTENT_KEYWORDS = {
    'greeting': {
        'en': ['hi', 'hello', 'hey'],
        'nl': ['hallo', 'hoi', 'goedemorgen', 'goedemiddag', 'goedenavond'],
    },
    'activation': {
        'en': ['activation', 'activate', 'go live', 'handoff', 'launch'],
        'nl': ['activatie', 'activeren', 'website activeren', 'live zetten', 'online zetten', 'oplevering'],
    },
    'preview': {
        'en': ['preview', 'start', 'create preview', 'start preview', 'ai preview', 'starter page generator'],
        'nl': ['preview', 'voorbeeld', 'start', 'preview maken', 'start preview', 'ai preview', 'starterpagina generator'],
    },
    'ecommerce': {
        'en': ['catalog', 'catalogs', 'catalogue', 'shop', 'online shop', 'online shops', 'ecommerce', 'woo commerce', 'woocommerce', 'webshop', 'products', 'reseller'],
        'nl': ['catalogus', 'catalogussen', 'webshop', 'webshops', 'online shop', 'online shops', 'woocommerce', 'producten', 'reseller', 'bestellen via whatsapp'],
    },
    'promotion': {
        'en': ['promotion', 'promote', 'ads', 'google ads', 'facebook posts', 'facebook ads', 'instagram ads', 'linkedin ads', 'meta ads', 'marketing'],
        'nl': ['promotie', 'promoten', 'ads', 'google ads', 'facebook posts', 'facebook ads', 'instagram ads', 'linkedin ads', 'meta ads', 'marketing'],
    },
    'payment': {
        'en': ['pay', 'payment', 'stripe', 'invoice'],
        'nl': ['betalen', 'betaling', 'betaallink', 'stripe', 'factuur'],
    },
    'plans': {
        'en': ['plan', 'plans', 'package', 'packages', 'pricing', 'website prices', 'view prices', 'price', 'prices', 'cost', 'costs', 'start a website'],
        'nl': ['pakket', 'pakketten', 'pricing', 'prijzen', 'website prijzen', 'prijs', 'kosten', 'website starten', 'website beginnen'],
    },
    'included': {
        'en': ['included', 'what do i get', 'package', 'website setup'],
        'nl': ['inbegrepen', 'wat krijg ik', 'pakket', 'website setup'],
    },
    'support': {
        'en': ['support', 'help', 'contact'],
        'nl': ['support', 'hulp', 'ondersteuning', 'vraag', 'contact'],
    },
    'dashboard': {
        'en': ['dashboard', 'edit', 'content', 'images', 'services', 'projects'],
        'nl': ['dashboard', 'aanpassen', 'teksten', 'afbeeldingen', 'diensten', 'projecten'],
    },
    'email': {
        'en': ['email', 'mailbox', 'business email', 'domain email'],
        'nl': ['email', 'e-mail', 'mailbox', 'info@', 'domeinmail'],
    },
    'changes': {
        'en': ['changes', 'extra work', 'edits', 'updates'],
        'nl': ['wijziging', 'wijzigingen', 'extra werk', 'aanpassing', 'meerwerk'],
    },
    'company_legal': {
        'en': ['terms', 'privacy', 'cookies', 'company', 'just code works', 'amsterdam'],
        'nl': ['voorwaarden', 'privacy', 'cookies', 'bedrijf', 'just code works', 'amsterdam'],
    },
}


PUBLIC_INFO_PAGES = {
    'terms': {
        'eyebrow': 'Legal',
        'title': 'Terms',
        'meta_description': 'Read the terms for Get Online Fast website setup, activation, customer content responsibility, support scope, and infringement handling.',
        'intro': (
            'These terms explain the main practical rules for Get Online Fast website setup, activation, support, and customer responsibilities. '
            'Get Online Fast provides the website and payment flow and is operated by Just Code Works.'
        ),
        'sections': [
            {
                'title': 'What is included in the website setup',
                'paragraphs': [
                    'Get Online Fast provides website setup, launch preparation, customer dashboard access where included, and related website tooling for small businesses.',
                    'The exact scope depends on the agreed package, approved preview, and any written add-ons or support work confirmed separately.',
                ],
            },
            {
                'title': 'Provider and payment chain',
                'paragraphs': [
                    'Get Online Fast provides the website and payment flow for managed website setup, activation, and handoff.',
                    'Get Online Fast is operated by Just Code Works. Secure card payment pages are handled by Stripe when a Stripe payment link is used.',
                ],
            },
            {
                'title': 'Customer responsibilities',
                'paragraphs': [
                    'Customers are responsible for providing accurate business details, lawful content, correct contact information, and materials they have permission to use.',
                    'Customers must review website text, images, offers, claims, and contact routes carefully before public launch or public use.',
                ],
            },
            {
                'title': 'Content, copyright, and intellectual property',
                'paragraphs': [
                    'The customer confirms that any text, logos, images, branding materials, documents, or other content they provide may legally be used on the website and in the website setup workflow.',
                    'Get Online Fast does not accept responsibility for customer-supplied content that infringes copyright, trademark, privacy, portrait, licensing, or other intellectual-property rights.',
                ],
            },
            {
                'title': 'Infringing or unlawful content',
                'paragraphs': [
                    'If Get Online Fast reasonably believes that customer content, business activity, or website usage is unlawful, misleading, infringing, abusive, or creates legal risk, the website, page, feature, or content may be removed, disabled, suspended, unpublished, or taken down without prior public notice.',
                    'This includes suspected copyright infringement, impersonation, prohibited business activity, or repeated refusal to remove problematic material after a warning.',
                ],
            },
            {
                'title': 'Custom changes and extra work',
                'paragraphs': [
                    'The agreed website setup covers the scope described on the payment page, preview, or written agreement. Custom changes outside that scope may be quoted or billed separately.',
                    'Extra design changes, extra content entry, custom sections, technical fixes, and other non-standard work may be scheduled separately from normal launch work.',
                ],
            },
            {
                'title': 'Activation, hosting, and service continuity',
                'paragraphs': [
                    'Activation, hosting, dashboard access, forms, and related tools may depend on payment, the agreed setup, and the ongoing service position for the website.',
                    'Get Online Fast does not promise instant activation the moment payment is made. Manual review, final checks, or follow-up communication may still be required.',
                ],
            },
            {
                'title': 'Support and practical limits',
                'paragraphs': [
                    'Normal support covers practical questions, small corrections, and routine guidance within the agreed service level.',
                    'It does not automatically include unlimited redesign work, unlimited copywriting, SEO guarantees, third-party service work, or urgent same-day development unless explicitly agreed.',
                ],
            },
            {
                'title': 'Contact',
                'paragraphs': [
                    'Questions about these terms can be sent to info@getonlinefast.eu.',
                ],
            },
        ],
        'related_links': ['privacy', 'support', 'payment_and_cancellation'],
    },
    'privacy': {
        'eyebrow': 'Privacy',
        'title': 'Privacy Policy',
        'meta_description': 'Read the privacy policy for Get Online Fast website activation, support requests, contact details, and customer account information.',
        'intro': (
            'This privacy policy explains the main types of information Get Online Fast may receive, how that information is used, '
            'and the practical choices customers and visitors have when Get Online Fast provides the website and payment flow.'
        ),
        'sections': [
            {
                'title': 'Information we may collect',
                'paragraphs': [
                    'We may collect contact details, business details, website preferences, uploaded materials, support messages, and billing-related information.',
                    'We may also collect basic technical information needed to keep the website, forms, dashboard, and related services working properly.',
                ],
            },
            {
                'title': 'Who provides the service',
                'paragraphs': [
                    'Get Online Fast provides the website and payment flow and is operated by Just Code Works.',
                    'If secure payment is completed through a Stripe payment link, Stripe processes the payment step on its own payment pages.',
                ],
            },
            {
                'title': 'How information is used',
                'paragraphs': [
                    'We use information to prepare and deliver website setups, respond to support questions, manage accounts, process activation or payment-related steps, and improve the service.',
                    'If customer-facing tools or assisted drafting tools are used, customers remain responsible for reviewing public-facing content before it is published.',
                ],
            },
            {
                'title': 'Sharing and service providers',
                'paragraphs': [
                    'We do not sell personal information.',
                    'Information may be processed by trusted providers used for hosting, email, forms, analytics, payment administration, security, or platform operations where needed to provide the service.',
                ],
            },
            {
                'title': 'Retention',
                'paragraphs': [
                    'We keep information for as long as reasonably needed to deliver the service, manage records, resolve issues, meet legal obligations, and protect the business.',
                    'Information may later be deleted, archived, anonymised, or limited when a service is no longer active, subject to practical record-keeping needs.',
                ],
            },
            {
                'title': 'Your choices',
                'paragraphs': [
                    'Where applicable, you can contact us to ask about access, correction, or deletion of your information.',
                    'Some information may still need to be kept for legal, accounting, fraud-prevention, or business record reasons.',
                ],
            },
            {
                'title': 'Contact',
                'paragraphs': [
                    'For privacy questions, contact info@getonlinefast.eu.',
                ],
            },
        ],
        'related_links': ['terms', 'support', 'cookies'],
    },
    'support': {
        'eyebrow': 'Support',
        'title': 'Support',
        'meta_description': 'See how Get Online Fast handles normal website support, practical customer questions, and paid custom changes outside the agreed setup.',
        'intro': (
            'This page explains the difference between normal support and paid custom changes so customers know what to expect after handoff or payment.'
        ),
        'sections': [
            {
                'title': 'Normal support',
                'paragraphs': [
                    'Normal support covers practical questions about the website, basic guidance, and small corrections related to the agreed setup.',
                    'This may include help with contact details, content clarification, dashboard guidance, or small launch-related follow-up items.',
                ],
            },
            {
                'title': 'Paid custom changes',
                'paragraphs': [
                    'Larger edits, layout adjustments, extra content work, technical fixes, custom sections, or work outside the agreed setup may be quoted or billed separately.',
                    'If a request is outside normal support, Get Online Fast can review it first and reply with the next step, time estimate, or quote.',
                ],
            },
            {
                'title': 'Response and scheduling',
                'paragraphs': [
                    'Support requests are reviewed as soon as practical, but review time does not guarantee immediate same-day completion.',
                    'More complex requests may need clarification, planning, or a separate approval before work starts.',
                ],
            },
            {
                'title': 'How to ask for help',
                'paragraphs': [
                    'For support or custom work questions, contact info@getonlinefast.eu and explain the page, issue, or requested change as clearly as possible.',
                ],
            },
        ],
        'related_links': ['terms', 'privacy', 'what_is_included'],
    },
    'after_payment': {
        'eyebrow': 'Next step',
        'title': 'Thank you, your payment has been received',
        'meta_description': 'Thank you for your website activation payment. Read the next manual steps and where to get support if anything is still needed.',
        'intro': (
            'Thank you for your payment. Your website activation is now in the review queue and the next steps are handled manually.'
        ),
        'sections': [
            {
                'title': 'What happens next',
                'paragraphs': [
                    'We will review the payment, check the website handoff details, and confirm the next activation step as soon as practical.',
                    'Please do not assume instant activation unless that was already agreed in writing. Final checks or follow-up questions may still be needed.',
                ],
            },
            {
                'title': 'What to prepare',
                'paragraphs': [
                    'If any final text, images, logo files, or contact details still need to be sent, please send them clearly in one message so nothing is missed.',
                    'If you requested changes outside the agreed setup, those may still need a separate quote or approval.',
                ],
            },
            {
                'title': 'Need help',
                'paragraphs': [
                    'If you need support after payment, use the support page or email info@getonlinefast.eu and mention your business name so we can find your website quickly.',
                ],
            },
        ],
        'related_links': ['support', 'terms', 'privacy'],
    },
    'cookies': {
        'eyebrow': 'Cookies',
        'title': 'Cookie Policy',
        'meta_description': 'Learn how Get Online Fast uses essential cookies, analytics, and basic technical tools on the website and platform.',
        'intro': (
            'This page explains the basic cookie and tracking information for Get Online Fast in plain language.'
        ),
        'sections': [
            {
                'title': 'Essential website cookies',
                'paragraphs': [
                    'Some cookies or similar storage may be used to keep forms, language choices, sessions, and core website functions working properly.',
                    'Without essential technical storage, some parts of the website or dashboard may not work as expected.',
                ],
            },
            {
                'title': 'Analytics and product improvement',
                'paragraphs': [
                    'We may use basic analytics or session tools to understand how visitors use the site, which pages are useful, and where the experience needs improvement.',
                    'These tools help with product decisions, support, and website quality, but they do not guarantee any commercial outcome for customers.',
                ],
            },
            {
                'title': 'Third-party services',
                'paragraphs': [
                    'Some embedded or connected tools may set their own cookies or technical identifiers when needed for analytics, security, payment handling, or platform operation.',
                    'Those providers may apply their own privacy or cookie terms in addition to this page.',
                ],
            },
            {
                'title': 'Provider chain',
                'paragraphs': [
                    'Get Online Fast provides the website and payment flow and is operated by Just Code Works.',
                    'If a Stripe payment link is used, Stripe may apply its own payment-related cookies or technical identifiers on the secure Stripe payment page.',
                ],
            },
            {
                'title': 'Your options',
                'paragraphs': [
                    'You can usually control cookies through your browser settings, although blocking essential cookies may affect how the site works.',
                    'If the cookie setup changes significantly in the future, this page should be updated accordingly.',
                ],
            },
        ],
        'related_links': ['privacy', 'terms'],
    },
    'what_is_included': {
        'eyebrow': 'Packages',
        'title': 'What is included',
        'meta_description': 'Understand what Get Online Fast website packages can include, such as previews, launch setup, hosting, support, dashboard access, and optional add-ons.',
        'intro': (
            'This page explains the practical scope of Get Online Fast website packages in plain language. Exact details can vary by package, quote, or agreed add-ons.'
        ),
        'sections': [
            {
                'title': 'Common package elements',
                'paragraphs': [
                    'Depending on the selected package, a website setup may include a private preview, launch preparation, page structure, contact options, mobile-friendly layout, and support for practical business content.',
                ],
                'bullets': [
                    'Private website preview before activation',
                    'Public website setup under the agreed package',
                    'Contact buttons, forms, and business information sections where included',
                    'Managed hosting or dashboard access where included',
                    'Support or small update handling where included',
                ],
            },
            {
                'title': 'What packages are not',
                'paragraphs': [
                    'A package does not automatically include unlimited redesign work, unlimited copywriting, unlimited SEO work, ad management, or guaranteed business results.',
                    'Some larger changes, migrations, integrations, or content-heavy updates may require a separate agreement or add-on.',
                ],
            },
            {
                'title': 'Editing and practical control',
                'paragraphs': [
                    'Customers can usually update practical information such as contact details, services, project items, and similar business content through the available workflow.',
                    'Larger content, layout, or search-sensitive changes should be handled carefully because they can affect clarity, structure, or performance.',
                ],
            },
            {
                'title': 'Package differences',
                'paragraphs': [
                    'Some packages focus on one-time setup, while others include ongoing hosting, support, dashboard access, and maintenance while the package remains active.',
                    'The package page, quote, or agreed plan should always be checked for the exact current scope.',
                ],
            },
        ],
        'related_links': ['payment_and_cancellation', 'domain_hosting_dashboard', 'addons_upgrades'],
    },
    'payment_and_cancellation': {
        'eyebrow': 'Payments',
        'title': 'Payment, renewal, and cancellation',
        'meta_description': 'Read how Get Online Fast handles payment timing, renewals, continuation, suspension, cancellation, and general withdrawal information.',
        'intro': (
            'This page explains the practical payment, renewal, and cancellation rules customers should understand before choosing a package.'
        ),
        'sections': [
            {
                'title': 'Payment and activation',
                'paragraphs': [
                    'A preview can be shown before full activation, but live service, hosting, domain continuation, dashboard access, or support may depend on payment and the agreed package.',
                    'Get Online Fast provides the website and payment flow and is operated by Just Code Works. Secure payment pages are handled by Stripe when a Stripe payment link is used.',
                    'Package pages, quotes, or payment instructions should be checked carefully before confirming an order.',
                ],
            },
            {
                'title': 'Renewal and continuation',
                'paragraphs': [
                    'Where a package includes ongoing hosting, dashboard access, domain continuation, or support, those services normally depend on active payment or continuation.',
                    'If a renewal is not continued or a package is not paid, related services may be suspended, expire, or be taken offline according to the package terms.',
                ],
            },
            {
                'title': 'Cancellation and service changes',
                'paragraphs': [
                    'Customers can contact Get Online Fast about stopping or changing a package, but the exact effect depends on what was purchased and what services have already been delivered.',
                    'One-time setup work, active subscriptions, domain handling, hosting periods, or completed support work may be treated differently.',
                ],
            },
            {
                'title': 'Withdrawal / cooling-off information',
                'paragraphs': [
                    'Where applicable, online purchases or services may include a 14-day withdrawal or cooling-off period.',
                    'Customers may also request immediate start or delivery during that period. If work or services begin immediately at the customer’s request, cancellation or refund handling may take delivered work, reserved capacity, or incurred costs into account.',
                    'Exact rights can depend on whether the customer is a consumer or business customer and on the purchased service or package. This page is practical guidance only and is not legal advice.',
                ],
            },
        ],
        'related_links': ['what_is_included', 'domain_hosting_dashboard', 'terms'],
    },
    'domain_hosting_dashboard': {
        'eyebrow': 'Access',
        'title': 'Domain, hosting, and dashboard access',
        'meta_description': 'Understand how Get Online Fast handles domain setup, hosting, dashboard access, forms, support limits, and active package responsibilities.',
        'intro': (
            'Get Online Fast websites are managed website packages. This means domain handling, hosting, dashboard access, support, forms, and connected tools should be understood as service components, not just static files.'
        ),
        'sections': [
            {
                'title': 'Who provides the workflow',
                'paragraphs': [
                    'Get Online Fast provides the website and payment flow and is operated by Just Code Works.',
                    'Payment pages may redirect to a secure Stripe checkout page, but activation and handoff review remain manual unless explicitly confirmed otherwise.',
                ],
            },
            {
                'title': 'Domain and hosting responsibility',
                'paragraphs': [
                    'Domain registration, domain continuation, hosting, and email-related setup can depend on the selected package and the current payment or continuation status.',
                    'If a customer does not continue the agreed service or does not pay for ongoing elements, the domain, hosting, or connected website services may expire, be suspended, or be taken offline according to the package terms.',
                ],
            },
            {
                'title': 'Dashboard access',
                'paragraphs': [
                    'Where dashboard access is included, it is provided as part of the active website package and platform workflow.',
                    'The exact scope of what customers can edit may vary. Practical content updates are usually suitable, while large structural or search-sensitive changes should be handled carefully or with support.',
                ],
            },
            {
                'title': 'Forms, integrations, and support limits',
                'paragraphs': [
                    'Contact forms, connected tools, support routes, and related features depend on the active package and the current technical setup.',
                    'Support is usually practical and scoped. It should not be interpreted as unlimited development, unlimited redesign, or unlimited marketing work unless explicitly agreed.',
                ],
            },
        ],
        'related_links': ['what_is_included', 'payment_and_cancellation', 'addons_upgrades'],
    },
    'addons_upgrades': {
        'eyebrow': 'Add-ons',
        'title': 'Add-ons and upgrades',
        'meta_description': 'See how optional add-ons and upgrades can extend a Get Online Fast website package after the first launch.',
        'intro': (
            'Some businesses start with a simpler package and add more later. This page explains that optional add-ons and upgrades may be available on request through Get Online Fast.'
        ),
        'sections': [
            {
                'title': 'Optional services',
                'paragraphs': [
                    'Optional services may include additional content work, more pages, extra service areas, visual improvements, catalog or shop features, marketing support, or platform-related setup work.',
                    'Availability can depend on the current package, project fit, technical setup, and agreed scope.',
                ],
            },
            {
                'title': 'Upgrading later',
                'paragraphs': [
                    'A customer may start with a simpler setup and later request a stronger package, more support, or additional features.',
                    'An upgrade can change what is included, such as hosting scope, dashboard tools, support level, content help, or add-on availability.',
                ],
            },
            {
                'title': 'No automatic inclusion',
                'paragraphs': [
                    'Add-ons are optional unless they are explicitly listed as included in the agreed package.',
                    'Features shown in examples, demos, or future product notes should not be assumed to be included automatically.',
                ],
            },
        ],
        'related_links': ['what_is_included', 'domain_hosting_dashboard', 'payment_and_cancellation'],
    },
    'catalog_and_ecommerce': {
        'eyebrow': 'Catalogs and online shops',
        'title': 'Catalogs and online shops',
        'meta_description': 'See the difference between starter catalogs, WooCommerce shops, and larger reseller-style catalog or eCommerce projects.',
        'intro': (
            'Start simple with a product catalog and WhatsApp orders, or grow into a full WooCommerce shop with checkout, payments, and a stronger store structure.'
        ),
        'sections': [],
        'related_links': ['plans', 'contact'],
    },
    'preview_licence': {
        'eyebrow': 'Preview rules',
        'title': 'Preview, demo, ownership, and licence',
        'meta_description': 'Understand the ownership and licence rules for Get Online Fast previews, demos, draft content, and unpaid website concepts.',
        'intro': (
            'Private previews and demos help customers understand direction before activation, but they are not automatically transferred, published, or licensed for reuse without agreement and payment.'
        ),
        'sections': [
            {
                'title': 'Provider chain',
                'paragraphs': [
                    'Get Online Fast provides the website and payment flow and is operated by Just Code Works.',
                    'A secure Stripe payment step can be used for activation payments, but preview approval, activation, and handoff review remain subject to the agreed setup.',
                ],
            },
            {
                'title': 'Preview status before payment',
                'paragraphs': [
                    'Previews, demos, draft layouts, example copy, structural mockups, and unpaid setup materials remain owned or licensed by Just Code Works / Get Online Fast until the relevant package is accepted and paid under the agreed terms.',
                    'A preview is for evaluation. It does not give permission to copy, publish, reuse, or recreate the work elsewhere without permission.',
                ],
            },
            {
                'title': 'No copying or publishing without permission',
                'paragraphs': [
                    'Copying preview text, layouts, images, structures, or demo assets for public use without permission or payment is not allowed.',
                    'This includes using preview material on another website, in another builder, or in another public channel without agreement.',
                ],
            },
            {
                'title': 'What changes after activation',
                'paragraphs': [
                    'Once a package is agreed and paid, the customer receives the rights or usage scope that belong to that package and the final delivered setup.',
                    'The exact ownership, usage, and access position can depend on whether the service is a one-time setup, an active managed package, or a platform-supported subscription.',
                ],
            },
        ],
        'related_links': ['terms', 'what_is_included', 'payment_and_cancellation'],
    },
}


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


def _public_info_link_items(keys):
    links = []
    for key in keys:
        item = PUBLIC_INFO_PAGE_LINKS.get(key)
        if not item:
            continue
        links.append(
            {
                'label': item['label'],
                'url': reverse(item['url_name']),
            }
        )
    return links


def _render_public_info_page(request, key):
    language = (getattr(request, 'LANGUAGE_CODE', 'en') or 'en').split('-', 1)[0]
    page = dict(PUBLIC_INFO_PAGES[key])
    page_sections = page['sections']
    extra_context = {}

    if key == 'catalog_and_ecommerce':
        service_options = _service_options_context(language)
        page['title'] = service_options['section_title']
        page['intro'] = service_options['section_intro']
        page_sections = _catalog_ecommerce_detail_sections(language)
        extra_context['service_options'] = service_options['options']
        extra_context['service_pricing_note'] = service_options['pricing_note']

    return render(
        request,
        'core/public_info_page.html',
        {
            'site_noindex': page.get('site_noindex', False),
            'force_indexable': page.get('force_indexable', True),
            'page_eyebrow': page['eyebrow'],
            'page_title': page['title'],
            'page_intro': page['intro'],
            'page_meta_description': page['meta_description'],
            'page_sections': page_sections,
            'related_links': _public_info_link_items(page.get('related_links', [])),
            'contact_email': 'info@getonlinefast.eu',
            **extra_context,
        },
    )


def _website_package_confirmation_context(*, posted_checks=None, error_message=''):
    payment_url = getattr(settings, 'GETONLINEFAST_WEBSITE_PACKAGE_PAYMENT_URL', '').strip()
    checks = posted_checks or {}
    helpful_links = [
        {'label': _('Support'), 'url': reverse('core:support')},
        {'label': _('Terms'), 'url': reverse('core:terms')},
        {'label': _('Privacy Policy'), 'url': reverse('core:privacy_policy')},
    ]
    checkbox_rows = []
    for checkbox in WEBSITE_PACKAGE_CONFIRMATION_CHECKBOXES:
        row = dict(checkbox)
        row['checked'] = bool(checks.get(checkbox['name']))
        checkbox_rows.append(row)

    return {
        'payment_url': payment_url,
        'payment_link_configured': bool(payment_url),
        'payment_error_message': error_message,
        'package_price': _('EUR 325 + VAT'),
        'package_checks': checkbox_rows,
        'package_helpful_links': helpful_links,
        'site_noindex': True,
        'page_meta_description': _('Complete your website activation by reviewing what is included, confirming the required points, and continuing to secure payment.'),
    }


def _checkbox_rows(checkboxes, checks):
    rows = []
    for checkbox in checkboxes:
        row = dict(checkbox)
        row['checked'] = bool(checks.get(checkbox['name']))
        rows.append(row)
    return rows


def _service_option_language(language):
    language_code = (language or 'en').split('-', 1)[0].lower()
    return language_code if language_code in SERVICE_OPTION_FALLBACKS else 'en'


def _service_option_fallback_map(section_key):
    if section_key == 'promotion':
        return PROMOTION_SERVICE_FALLBACKS
    return SERVICE_OPTION_FALLBACKS


def _resolve_cta_url(language, option_data):
    cta_url = (option_data.get('cta_url') or '').strip()
    if cta_url:
        return cta_url

    url_name = option_data.get('cta_url_name') or 'core:contact'
    if url_name == 'core:catalog_and_ecommerce' and language == 'nl':
        return reverse('core:catalog_and_ecommerce_nl')
    return reverse(url_name)


def _normalized_service_option(option_data, language):
    includes = option_data.get('includes', [])
    if isinstance(includes, str):
        includes = [item.strip() for item in includes.splitlines() if item.strip()]

    good_for = option_data.get('good_for', [])
    if isinstance(good_for, str):
        good_for = [item.strip() for item in good_for.splitlines() if item.strip()]

    return {
        'option_key': option_data['option_key'],
        'eyebrow': option_data.get('eyebrow', ''),
        'title': option_data['title'],
        'price_label': option_data.get('price_label', ''),
        'summary': option_data['summary'],
        'good_for': good_for,
        'includes': includes,
        'cta_label': option_data.get('cta_label', ''),
        'cta_url': _resolve_cta_url(language, option_data),
    }


def _service_options_fallback(language, section_key='catalog_ecommerce'):
    language_code = _service_option_language(language)
    fallback = _service_option_fallback_map(section_key)[language_code]
    options = [_normalized_service_option(option_data, language_code) for option_data in fallback['options']]
    return {
        'section_title': fallback['section_title'],
        'section_intro': fallback['section_intro'],
        'pricing_note': fallback['pricing_note'],
        'options': options,
    }


def _service_options_context(language, section_key='catalog_ecommerce'):
    language_code = _service_option_language(language)
    fallback = _service_options_fallback(language_code, section_key=section_key)
    rows = list(
        ServiceOption.objects.filter(section_key=section_key, language=language_code, is_active=True)
        .order_by('sort_order', 'id')
    )
    if not rows:
        return fallback

    options = []
    for row in rows:
        options.append(
            _normalized_service_option(
                {
                    'option_key': row.option_key,
                    'eyebrow': row.eyebrow,
                    'title': row.title,
                    'price_label': row.price_label,
                    'summary': row.summary,
                    'good_for': row.good_for,
                    'includes': row.includes,
                    'cta_label': row.cta_label,
                    'cta_url': row.cta_url,
                },
                language_code,
            )
        )

    return {
        'section_title': fallback['section_title'],
        'section_intro': fallback['section_intro'],
        'pricing_note': fallback['pricing_note'],
        'options': options,
    }


def _catalog_ecommerce_table_rows(language):
    language_code = _service_option_language(language)
    if language_code == 'nl':
        return [
            {'label': 'Product pages', 'values': ['check', 'check', 'check']},
            {'label': 'WhatsApp/contact ordering', 'values': ['check', 'Optioneel', 'Offerteflow']},
            {'label': 'Cart and checkout', 'values': ['dash', 'check', 'Later mogelijk']},
            {'label': 'Payment setup guidance', 'values': ['dash', 'check', 'Maatwerkscope']},
            {'label': 'Shipping/tax structure', 'values': ['dash', 'check', 'Maatwerkscope']},
            {'label': 'Larger catalog/filter structure', 'values': ['Basis', 'Standaard shop', 'check']},
            {'label': 'WooCommerce dashboard', 'values': ['dash', 'check', 'Afhankelijk van setup']},
        ]

    return [
        {'label': 'Product pages', 'values': ['check', 'check', 'check']},
        {'label': 'WhatsApp/contact ordering', 'values': ['check', 'Optional', 'Enquiry flow']},
        {'label': 'Cart and checkout', 'values': ['dash', 'check', 'Possible later']},
        {'label': 'Payment setup guidance', 'values': ['dash', 'check', 'Custom scope']},
        {'label': 'Shipping/tax structure', 'values': ['dash', 'check', 'Custom scope']},
        {'label': 'Larger catalog/filter structure', 'values': ['Basic only', 'Standard shop', 'check']},
        {'label': 'WooCommerce dashboard', 'values': ['dash', 'check', 'Depends on setup']},
    ]


def _catalog_ecommerce_badges(language):
    language_code = _service_option_language(language)
    if language_code == 'nl':
        return ['SSL', 'WhatsApp-bestellingen', 'EU betaalopzet-begeleiding', 'WooCommerce', 'Catalogusstructuur']
    return ['SSL', 'WhatsApp orders', 'EU payment setup guidance', 'WooCommerce', 'Catalog structure']


def _catalog_ecommerce_detail_sections(language):
    language_code = _service_option_language(language)
    service_options = _service_options_context(language_code)
    sections = []
    for option in service_options['options']:
        sections.append(
            {
                'title': f"{option['title']} - {option['price_label']}" if option['price_label'] else option['title'],
                'paragraphs': [option['summary']],
                'bullets': option['includes'],
            }
        )

    if language_code == 'nl':
        sections.extend(
            [
                {
                    'title': 'Catalogus versus volledige eCommerce',
                    'paragraphs': [
                        'Een catalogus is geschikt wanneer klanten producten bekijken en daarna bestellen via WhatsApp, telefoon of een contactformulier.',
                        'Volledige eCommerce is geschikter wanneer klanten een winkelwagen, checkout, betaling en een uitgebreidere shopflow nodig hebben.',
                    ],
                },
                {
                    'title': 'Hoe projecten worden afgestemd',
                    'paragraphs': [
                        'Catalogus- en eCommerce-projecten worden afgestemd op producten, betalingen, verzending, talen en de gewenste opzet.',
                        service_options['pricing_note'],
                    ],
                },
            ]
        )
    else:
        sections.extend(
            [
                {
                    'title': 'Catalog versus full eCommerce',
                    'paragraphs': [
                        'A catalog works well when customers browse products and then order through WhatsApp, phone, or a contact form.',
                        'Full eCommerce is the better fit when customers need a cart, checkout, payment handling, and a more complete online shop flow.',
                    ],
                },
                {
                    'title': 'How projects are scoped',
                    'paragraphs': [
                        'Catalog and eCommerce projects are discussed based on products, payments, shipping, languages, and the setup your business needs.',
                        service_options['pricing_note'],
                    ],
                },
            ]
        )

    return sections


def _promotion_page_config(language, option_key):
    language_code = _service_option_language(language)
    promotion_pages = PROMOTION_PAGE_FALLBACKS[language_code]
    return promotion_pages[option_key]


def _promotion_related_links(option_key):
    return [
        'facebook_posts',
        'facebook_instagram_ads',
        'google_ads',
        'linkedin_ads',
        'plans',
        'contact',
    ]


def _promotion_page_context(language, option_key):
    language_code = _service_option_language(language)
    service_options = _service_options_context(language_code, section_key='promotion')
    option_map = {option['option_key']: option for option in service_options['options']}
    option = option_map.get(option_key)
    page = _promotion_page_config(language_code, option_key)

    if option is None:
        option = _normalized_service_option(
            {
                'option_key': option_key,
                'eyebrow': page['eyebrow'],
                'title': page['title'],
                'price_label': page['price_label'],
                'summary': page['intro'],
                'cta_label': page['cta_label'],
                'cta_url_name': 'core:contact',
            },
            language_code,
        )

    advice = PROMOTION_PAGE_FALLBACKS[language_code]

    return {
        'site_noindex': False,
        'force_indexable': True,
        'page_eyebrow': page['eyebrow'],
        'page_title': option['title'],
        'page_intro': page['intro'],
        'page_price_label': option.get('price_label') or page['price_label'],
        'page_meta_description': page['intro'],
        'page_sections': page['sections'],
        'related_links': _public_info_link_items(_promotion_related_links(option_key)),
        'page_primary_cta_label': page['cta_label'],
        'page_primary_cta_url': reverse('core:contact'),
        'advice_title': advice['advice_title'],
        'advice_text': advice['advice_text'],
        'advice_button_label': advice['advice_button_label'],
        'advice_button_url': reverse('core:contact'),
        'contact_email': 'info@getonlinefast.eu',
    }


def _assistant_language(request):
    language = (request.GET.get('lang') or getattr(request, 'LANGUAGE_CODE', 'en') or 'en').split('-', 1)[0].lower()
    return language if language in ASSISTANT_PUBLIC_KNOWLEDGE else 'en'


def _assistant_links(language):
    catalog_url_name = 'core:catalog_and_ecommerce_nl' if language == 'nl' else 'core:catalog_and_ecommerce'
    with override(language):
        return {
            'support_url': reverse('core:support'),
            'contact_url': reverse('core:contact'),
            'plans_url': reverse('core:plans'),
            'catalog_url': reverse(catalog_url_name),
            'promotion_url': reverse('core:facebook_posts'),
            'terms_url': reverse('core:terms'),
            'privacy_url': reverse('core:privacy_policy'),
            'cookies_url': reverse('core:cookie_policy'),
            'payment_url': reverse('core:payment_and_cancellation'),
            'included_url': reverse('core:what_is_included'),
        }


def _assistant_normalize_question(question):
    question_text = (question or '').strip().lower()
    return ' '.join(question_text.replace('?', ' ').replace('!', ' ').replace('.', ' ').replace(',', ' ').split())


def _assistant_detect_intent(question, language):
    normalized_question = _assistant_normalize_question(question)
    if not normalized_question:
        return 'fallback'

    for intent, language_keywords in ASSISTANT_INTENT_KEYWORDS.items():
        keywords = list(language_keywords.get(language, [])) + list(language_keywords.get('en', [])) + list(language_keywords.get('nl', []))
        for keyword in keywords:
            if keyword and keyword in normalized_question:
                return intent
    return 'fallback'


def _assistant_link_items(intent, language, links):
    labels = {
        'en': {
            'activation': 'Activation page',
            'catalog_ecommerce': 'Catalogs and online shops',
            'promotion': 'Promotion',
            'payment': 'Payment info',
            'included': 'What is included',
            'support': 'Support',
            'contact': 'Contact',
            'terms': 'Terms',
            'privacy': 'Privacy Policy',
            'cookies': 'Cookie Policy',
        },
        'nl': {
            'activation': 'Activatiepagina',
            'catalog_ecommerce': 'Catalogus en webshop',
            'promotion': 'Promotie',
            'payment': 'Betaling en annulering',
            'included': 'Wat is inbegrepen',
            'support': 'Support',
            'contact': 'Contact',
            'terms': 'Voorwaarden',
            'privacy': 'Privacy Policy',
            'cookies': 'Cookie Policy',
        },
    }
    copy = labels.get(language, labels['en'])

    if intent == 'greeting':
        return []
    if intent == 'activation':
        return [
            {'label': copy['payment'], 'url': links['payment_url']},
            {'label': copy['contact'], 'url': links['contact_url']},
        ]
    if intent == 'preview':
        return [
            {'label': copy['contact'], 'url': links['contact_url']},
            {'label': copy['support'], 'url': links['support_url']},
        ]
    if intent == 'plans':
        return [
            {'label': 'Plans' if language == 'en' else 'Pakketten', 'url': links['plans_url']},
            {'label': copy['contact'], 'url': links['contact_url']},
        ]
    if intent == 'ecommerce':
        return [
            {'label': copy['catalog_ecommerce'], 'url': links['catalog_url']},
            {'label': copy['contact'], 'url': links['contact_url']},
        ]
    if intent == 'promotion':
        return [
            {'label': copy['promotion'], 'url': links['promotion_url']},
            {'label': copy['contact'], 'url': links['contact_url']},
        ]
    if intent == 'payment':
        return [
            {'label': copy['payment'], 'url': links['payment_url']},
            {'label': copy['contact'], 'url': links['contact_url']},
        ]
    if intent == 'included':
        return [{'label': copy['included'], 'url': links['included_url']}]
    if intent in {'support', 'dashboard', 'email', 'changes'}:
        return [
            {'label': copy['support'], 'url': links['support_url']},
            {'label': copy['contact'], 'url': links['contact_url']},
        ]
    if intent == 'company_legal':
        return [
            {'label': copy['terms'], 'url': links['terms_url']},
            {'label': copy['privacy'], 'url': links['privacy_url']},
            {'label': copy['cookies'], 'url': links['cookies_url']},
        ]
    return [
        {'label': copy['payment'], 'url': links['payment_url']},
        {'label': copy['included'], 'url': links['included_url']},
    ]


def _assistant_answer(question, language):
    knowledge = ASSISTANT_PUBLIC_KNOWLEDGE[language]
    intent = _assistant_detect_intent(question, language)
    links = _assistant_links(language)
    template_key = intent if intent in knowledge else 'fallback'
    answer = knowledge[template_key].format(**links)
    return {
        'intent': intent,
        'answer': answer,
        'suggested_links': _assistant_link_items(intent, language, links),
    }


def _hmd_activation_context(*, posted_checks=None, error_message=''):
    payment_url = getattr(settings, 'GETONLINEFAST_HMD_KLUSBEDRIJF_PAYMENT_URL', '').strip()
    checks = posted_checks or {}
    helpful_links = [
        {'label': 'Voorwaarden', 'url': reverse('core:terms')},
        {'label': 'Privacy Policy', 'url': reverse('core:privacy_policy')},
        {'label': 'Cookie Policy', 'url': reverse('core:cookie_policy')},
        {'label': 'Payment & Cancellation', 'url': reverse('core:payment_and_cancellation')},
        {'label': 'Contact', 'url': reverse('core:contact')},
    ]
    legal_links = [
        {'label': 'Voorwaarden', 'url': reverse('core:terms')},
        {'label': 'Privacy Policy', 'url': reverse('core:privacy_policy')},
        {'label': 'Cookie Policy', 'url': reverse('core:cookie_policy')},
        {'label': 'Payment & Cancellation', 'url': reverse('core:payment_and_cancellation')},
    ]

    return {
        'payment_url': payment_url,
        'payment_link_configured': bool(payment_url),
        'payment_error_message': error_message,
        'activation_eyebrow': 'HMD activatie',
        'activation_title': 'Website activatie voor HMD Klusbedrijf',
        'activation_intro': (
            'Deze activatiepagina wordt aangeboden door Get Online Fast voor de website setup en handoff van '
            'HMD Klusbedrijf. Betaling verloopt veilig via Stripe. Na betaling controleert en bevestigt Get Online Fast '
            'de activatie en handoff handmatig.'
        ),
        'activation_included_items': [
            'Website setup op basis van de afgesproken preview en scope voor HMD Klusbedrijf',
            'Inhoudelijke basisinvoer voor bedrijfsinformatie, diensten, contactgegevens en branding waar afgesproken',
            'Handoff en activatiecontrole door Get Online Fast na betaling',
            'Praktische opvolging als er nog beperkte afrondingspunten nodig zijn voor de livegang',
        ],
        'activation_not_included_items': [
            'Onbeperkte revisies of onbeperkte ontwerpwijzigingen',
            'Extra maatwerk, extra paginas of aanvullende technische koppelingen buiten de afgesproken setup',
            'Doorlopende marketing, SEO-resultaatgaranties of externe betaalde licenties tenzij apart afgesproken',
            'Automatische activatie of automatische eigendomsoverdracht zonder handmatige bevestiging',
        ],
        'activation_checks': _checkbox_rows(HMD_ACTIVATION_CONFIRMATION_CHECKBOXES, checks),
        'activation_helpful_links': helpful_links,
        'activation_legal_links': legal_links,
        'payment_button_label': 'Verder naar beveiligde betaling',
        'payment_note': 'De betaling wordt veilig afgehandeld via Stripe. De knop wordt pas actief nadat alle bevestigingen zijn aangevinkt.',
        'payment_missing_message': 'De betaallink is tijdelijk niet beschikbaar. Neem contact met ons op om de activatie af te ronden.',
        'site_noindex': True,
        'force_indexable': False,
        'page_meta_description': 'Activeer de website setup voor HMD Klusbedrijf via Get Online Fast en ga daarna verder naar de beveiligde Stripe betaling.',
    }


def _public_sitemap_route_names():
    return [
        'core:home',
        'core:how_it_works',
        'ai_starter:start',
        'core:plans',
        'core:catalog_and_ecommerce',
        'core:facebook_posts',
        'core:facebook_instagram_ads',
        'core:google_ads',
        'core:linkedin_ads',
        'core:faq',
        'core:contact',
        'core:support',
        'core:terms',
        'core:privacy_policy',
        'core:cookie_policy',
        'core:what_is_included',
        'core:payment_and_cancellation',
        'core:domain_hosting_and_dashboard',
        'core:addons_and_upgrades',
        'core:preview_licence',
    ]


def robots_txt(request):
    lines = [
        'User-agent: *',
        'Allow: /',
    ]
    for language_code, _label in settings.LANGUAGES:
        lines.append(f'Disallow: /{language_code}/payment/')
        lines.append(f'Disallow: /{language_code}/pay/website-package/')
        lines.append(f'Disallow: /{language_code}/activate/website-package/')
        lines.append(f'Disallow: /{language_code}/activate/hmd-klusbedrijf/')
        lines.append(f'Disallow: /{language_code}/activate/hmd-klusbedrijf/thank-you/')
        lines.append(f'Disallow: /{language_code}/after-payment/')
        lines.append(f'Disallow: /{language_code}/templates/')
        lines.append(f'Disallow: /{language_code}/examples/')
        lines.append(f'Disallow: /{language_code}/ai-website/')
        lines.append(f'Disallow: /{language_code}/managed/')
        lines.append(f'Disallow: /{language_code}/plans/monthly-website/')
        lines.append(f'Disallow: /{language_code}/plans/monthly-plan/')
        lines.append(f'Disallow: /{language_code}/plans/ecommerce-plan/')
    sitemap_url = request.build_absolute_uri(reverse('sitemap_xml'))
    lines.append(f'Sitemap: {sitemap_url}')
    lines.append('')
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')


def sitemap_xml(request):
    with override('en'):
        urls = [request.build_absolute_uri(reverse(route_name)) for route_name in _public_sitemap_route_names()]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        xml.append('  <url>')
        xml.append(f'    <loc>{url}</loc>')
        xml.append('  </url>')
    xml.append('</urlset>')
    return HttpResponse('\n'.join(xml), content_type='application/xml; charset=utf-8')


def assistant_help(request):
    language = _assistant_language(request)
    question = request.GET.get('q', '')
    link_urls = _assistant_links(language)
    assistant_response = build_public_assistant_response(
        request=request,
        question=question,
        language=language,
        fallback_response=_assistant_answer(question, language),
        links=link_urls,
    )
    payload = {
        'language': language,
        'intent': assistant_response['intent'],
        'answer': assistant_response['answer'],
        'suggested_links': assistant_response['suggested_links'],
        'links': {
            'support': link_urls['support_url'],
            'contact': link_urls['contact_url'],
            'plans': link_urls['plans_url'],
            'catalog_and_ecommerce': link_urls['catalog_url'],
            'promotion': link_urls['promotion_url'],
            'terms': link_urls['terms_url'],
            'privacy': link_urls['privacy_url'],
            'cookies': link_urls['cookies_url'],
            'payment_and_cancellation': link_urls['payment_url'],
        },
        'mode': assistant_response['mode'],
        'fallback_reason': assistant_response['fallback_reason'],
        'ai_enabled': assistant_response['ai_enabled'],
        'public_ai_enabled': assistant_response['public_ai_enabled'],
        'has_openai_key': assistant_response['has_openai_key'],
        'model_used': assistant_response['model_used'],
    }
    if settings.DEBUG:
        payload.update(assistant_response.get('diagnostics') or {})
    return JsonResponse(payload)


def _raise_non_staff_or_debug_page_unavailable(request):
    if settings.DEBUG:
        return
    if request.user.is_authenticated and request.user.is_staff:
        return
    raise Http404('Not found.')


def assistant_proof(request):
    _raise_non_staff_or_debug_page_unavailable(request)
    language = _assistant_language(request)
    return render(
        request,
        'core/assistant_proof.html',
        {
            'assistant_proof_language': language,
            'assistant_proof_status': public_assistant_status(),
            'site_noindex': True,
            'force_indexable': False,
        },
    )


def home(request):
    language = (getattr(request, 'LANGUAGE_CODE', 'en') or 'en').split('-', 1)[0]
    selected_template_slug = default_template_slug()
    service_options = _service_options_context(language)
    promotion_options = _service_options_context(language, section_key='promotion')
    return render(
        request,
        'core/home.html',
        {
            'onboarding_form': StarterOnboardingForm(),
            'onboarding_modal_open': False,
            'template_cards': available_template_cards(),
            'selected_template_slug': selected_template_slug,
            'selected_template_card': get_template_card(selected_template_slug),
            'latest_public_blog_posts': BlogPost.objects.public().for_language(language).select_related('category')[:3],
            'catalog_service_section_title': service_options['section_title'],
            'catalog_service_section_intro': service_options['section_intro'],
            'catalog_service_options': service_options['options'],
            'catalog_service_pricing_note': service_options['pricing_note'],
            'catalog_service_table_rows': _catalog_ecommerce_table_rows(language),
            'catalog_service_badges': _catalog_ecommerce_badges(language),
            'promotion_section_title': promotion_options['section_title'],
            'promotion_section_intro': promotion_options['section_intro'],
            'promotion_service_options': promotion_options['options'],
            'promotion_service_note': promotion_options['pricing_note'],
            'force_indexable': True,
            'site_noindex': False,
            'page_meta_description': 'Get Online Fast helps small businesses launch practical WordPress websites with clear structure, support, and room to grow.',
        },
    )


def how_it_works(request):
    return render(
        request,
        'core/how_it_works.html',
        {
            'force_indexable': True,
            'site_noindex': False,
            'page_meta_description': 'See how Get Online Fast helps small businesses go from business details to a live WordPress website.',
        },
    )


def _raise_non_staff_public_page_unavailable(request):
    if request.user.is_authenticated and request.user.is_staff:
        return
    raise Http404('Not found.')


def examples(request):
    _raise_non_staff_public_page_unavailable(request)
    cards = []
    for entry in template_catalog():
        mode = 'template' if entry['status'] == 'ready' else 'style_reference'
        cards.append(
            {
                **entry,
                'button_label': _('Contact us about this layout') if entry['status'] == 'ready' else _('Ask about this layout'),
                'button_url': reverse('core:contact'),
            }
        )

    category_meta = template_category_details()
    grouped_cards = []
    for category_key in template_category_order():
        category_cards = [card for card in cards if card['category'] == category_key]
        if not category_cards:
            continue

        grouped_cards.append(
            {
                'key': category_key,
                'title': category_meta[category_key]['title'],
                'description': category_meta[category_key]['description'],
                'cards': category_cards,
            }
        )

    return render(
        request,
        'core/examples.html',
        {
            'template_groups': grouped_cards,
            'force_indexable': False,
            'site_noindex': True,
            'page_meta_description': 'Choose a starting website layout, then adapt the colours, images, content, and style to fit your business.',
            'reference_note': _(
                'Layout direction only. Final website can be adapted to your content, logo, colours, images, pages, and selected features.'
            ),
        },
    )


def plans(request):
    return render(
        request,
        'core/plans.html',
        {
            'force_indexable': True,
            'site_noindex': False,
            'page_title': _('Plans'),
            'page_meta_description': _(
                'Compare website plans from Get Online Fast, including starter websites, one-time or monthly website plans, and catalog or online shop options.'
            ),
            'plans': website_plans_overview_cards(),
        },
    )


def faq(request):
    return render(
        request,
        'core/faq.html',
        {
            'force_indexable': True,
            'site_noindex': False,
            'page_meta_description': 'Read practical answers about previews, website plans, support, and launching with Get Online Fast.',
        },
    )


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
            'force_indexable': True,
            'site_noindex': False,
            'page_meta_description': 'Contact Get Online Fast about website plans, support, launch timing, or the right setup for your business.',
        },
    )


def website_package_payment(request):
    if request.method == 'POST':
        posted_checks = {
            checkbox['name']: request.POST.get(checkbox['name']) == 'on'
            for checkbox in WEBSITE_PACKAGE_CONFIRMATION_CHECKBOXES
        }
        missing = [checkbox for checkbox in WEBSITE_PACKAGE_CONFIRMATION_CHECKBOXES if not posted_checks[checkbox['name']]]
        payment_url = getattr(settings, 'GETONLINEFAST_WEBSITE_PACKAGE_PAYMENT_URL', '').strip()
        if missing:
            return render(
                request,
                'core/website_package_payment.html',
                _website_package_confirmation_context(
                    posted_checks=posted_checks,
                    error_message=_('Please confirm all required points before continuing to secure payment.'),
                ),
                status=400,
            )
        if not payment_url:
            return render(
                request,
                'core/website_package_payment.html',
                _website_package_confirmation_context(
                    posted_checks=posted_checks,
                    error_message=_('Payment link is not configured yet. Please contact info@getonlinefast.eu.'),
                ),
                status=200,
            )
        return redirect(payment_url)

    return render(
        request,
        'core/website_package_payment.html',
        _website_package_confirmation_context(),
    )


def hmd_activation(request):
    if request.method == 'POST':
        posted_checks = {
            checkbox['name']: request.POST.get(checkbox['name']) == 'on'
            for checkbox in HMD_ACTIVATION_CONFIRMATION_CHECKBOXES
        }
        missing = [checkbox for checkbox in HMD_ACTIVATION_CONFIRMATION_CHECKBOXES if not posted_checks[checkbox['name']]]
        payment_url = getattr(settings, 'GETONLINEFAST_HMD_KLUSBEDRIJF_PAYMENT_URL', '').strip()
        if missing:
            return render(
                request,
                'core/hmd_activation_page.html',
                _hmd_activation_context(
                    posted_checks=posted_checks,
                    error_message='Bevestig eerst alle verplichte punten voordat je doorgaat naar de beveiligde betaling.',
                ),
                status=400,
            )
        if not payment_url:
            return render(
                request,
                'core/hmd_activation_page.html',
                _hmd_activation_context(
                    posted_checks=posted_checks,
                    error_message='De betaallink is tijdelijk niet beschikbaar. Neem contact met ons op om de activatie af te ronden.',
                ),
                status=200,
            )
        return redirect(payment_url)

    return render(
        request,
        'core/hmd_activation_page.html',
        _hmd_activation_context(),
    )


def hmd_activation_thank_you(request):
    return render(
        request,
        'core/public_info_page.html',
        {
            'site_noindex': True,
            'force_indexable': False,
            'page_eyebrow': 'HMD activatie',
            'page_title': 'Bedankt voor je betaling',
            'page_intro': (
                'De betaling is afgehandeld via Stripe. Get Online Fast controleert de activatie en handoff van '
                'HMD Klusbedrijf handmatig en neemt contact op als er nog iets nodig is.'
            ),
            'page_meta_description': 'Bedankt voor je betaling voor de websiteactivatie van HMD Klusbedrijf. Get Online Fast controleert de handoff handmatig.',
            'page_sections': [
                {
                    'title': 'Wat gebeurt er nu',
                    'paragraphs': [
                        'Get Online Fast controleert de ontvangen betaling en bekijkt daarna handmatig de activatie- en handoffstappen voor HMD Klusbedrijf.',
                        'Ga niet uit van automatische activatie of automatische overdracht zolang dit niet handmatig door Get Online Fast is bevestigd.',
                    ],
                },
                {
                    'title': 'Als er nog iets nodig is',
                    'paragraphs': [
                        'Als er nog aanvullende informatie, bestanden of afrondingspunten nodig zijn, neemt Get Online Fast contact met je op.',
                        'Extra werk buiten de afgesproken setup kan nog steeds apart worden afgestemd of geoffreerd.',
                    ],
                },
            ],
            'related_links': [
                {'label': 'Contact', 'url': reverse('core:contact')},
                {'label': 'Payment & Cancellation', 'url': reverse('core:payment_and_cancellation')},
                {'label': 'Privacy Policy', 'url': reverse('core:privacy_policy')},
            ],
            'contact_email': 'info@getonlinefast.eu',
        },
    )


def after_payment(request):
    return _render_public_info_page(request, 'after_payment')


def support(request):
    return _render_public_info_page(request, 'support')


def catalog_and_ecommerce(request):
    return _render_public_info_page(request, 'catalog_and_ecommerce')


def _render_promotion_page(request, option_key):
    return render(
        request,
        'core/public_info_page.html',
        _promotion_page_context((getattr(request, 'LANGUAGE_CODE', 'en') or 'en').split('-', 1)[0], option_key),
    )


def facebook_posts(request):
    return _render_promotion_page(request, 'facebook_posts')


def facebook_instagram_ads(request):
    return _render_promotion_page(request, 'meta_ads')


def google_ads(request):
    return _render_promotion_page(request, 'google_ads')


def linkedin_ads(request):
    return _render_promotion_page(request, 'linkedin_ads')


def privacy_policy(request):
    return _render_public_info_page(request, 'privacy')


def terms(request):
    return _render_public_info_page(request, 'terms')


def cookie_policy(request):
    return _render_public_info_page(request, 'cookies')


def what_is_included(request):
    return _render_public_info_page(request, 'what_is_included')


def payment_and_cancellation(request):
    return _render_public_info_page(request, 'payment_and_cancellation')


def domain_hosting_and_dashboard(request):
    return _render_public_info_page(request, 'domain_hosting_dashboard')


def _domain_information_context():
    return {
        'page_title': _('Domain Information'),
        'page_intro': _(
            'See the current domain management position for your website package and the main boundaries around continuation or transfer information.'
        ),
        'domain_rows': [
            {'label': _('Domain'), 'value': 'example.nl'},
            {'label': _('Domain status'), 'value': _('Managed')},
            {'label': _('Managed by'), 'value': _('Get Online Fast')},
            {'label': _('Website connection'), 'value': _('Connected to your website package')},
            {'label': _('Renewal date/status'), 'value': _('Shown here when available')},
            {'label': _('DNS management'), 'value': _('Managed while package is active')},
            {'label': _('Email/DNS records where applicable'), 'value': _('Managed where included in the active setup')},
            {'label': _('Transfer/auth code status'), 'value': _('Available after payment/settlement where applicable')},
        ],
        'domain_explanations': [
            {
                'title': _('While your package is active'),
                'body': _(
                    'Your domain is managed as part of your active website package. As long as your package is active and paid, Get Online Fast keeps the domain connected to your website and manages the technical DNS settings needed for the website, email, and related services where applicable.'
                ),
            },
            {
                'title': _('If you decide not to continue'),
                'body': _(
                    'If you decide not to continue with the website package, the domain transfer/auth code can be made available here after any open balance, renewal cost, or agreed administration/support cost has been paid.'
                ),
            },
            {
                'title': _('What this does not include'),
                'body': _(
                    'This does not include website migration, email setup, DNS setup with another provider, or technical support for another provider.'
                ),
            },
        ],
        'domain_actions': [
            {'label': _('Continue website package'), 'url': reverse('core:monthly_plan')},
            {'label': _('View payment/settlement information'), 'url': reverse('core:payment_and_cancellation')},
            {'label': _('Contact support'), 'url': reverse('core:contact')},
        ],
    }


@login_required(login_url='/admin/login/')
def dashboard_domain_information(request):
    return render(
        request,
        'dashboard/domain_information.html',
        {
            **_domain_information_context(),
            'site_noindex': True,
        },
    )


def addons_and_upgrades(request):
    return _render_public_info_page(request, 'addons_upgrades')


def preview_licence(request):
    return _render_public_info_page(request, 'preview_licence')


def one_time_website_plan(request):
    selected_template_slug = default_template_slug()
    return render(
        request,
        'core/plan_one_time.html',
        {
            'onboarding_form': StarterOnboardingForm(),
            'onboarding_modal_open': False,
            'template_cards': available_template_cards(),
            'selected_template_slug': selected_template_slug,
            'selected_template_card': get_template_card(selected_template_slug),
            'force_indexable': True,
            'site_noindex': False,
        },
    )


def monthly_plan(request):
    selected_template_slug = default_template_slug()
    return render(
        request,
        'core/plan_monthly.html',
        {
            'onboarding_form': StarterOnboardingForm(),
            'onboarding_modal_open': False,
            'template_cards': available_template_cards(),
            'selected_template_slug': selected_template_slug,
            'selected_template_card': get_template_card(selected_template_slug),
            'force_indexable': True,
            'site_noindex': False,
        },
    )


def ecommerce_plan(request):
    return render(
        request,
        'core/plan_ecommerce.html',
        {
            'force_indexable': True,
            'site_noindex': False,
        },
    )


def ai_website(request):
    return render(request, 'core/detail_page.html', {**ai_website_context(), 'force_indexable': True, 'site_noindex': False})


def business_website(request):
    return render(request, 'core/detail_page.html', {**business_website_context(), 'force_indexable': True, 'site_noindex': False})


def managed(request):
    return render(request, 'core/detail_page.html', {**managed_context(), 'force_indexable': True, 'site_noindex': False})


def website_plans_overview_cards():
    return [
        {
            'title': _('Starter Page'),
            'price': _('EUR 20/month'),
            'text': _('A simple starting point for businesses that want to get online quickly with the basics.'),
            'items': [
                _('Starter page'),
                _('Temporary Get Online Fast subdomain'),
                _('Basic editable content'),
                _('WhatsApp or contact button'),
                _('Upgrade to a full website later'),
            ],
            'cta': _('Start with Starter Page'),
            'url_name': 'core:ai_website',
        },
        {
            'title': _('One-Time Website'),
            'price': _('€325 + VAT'),
            'text': _('A complete business website prepared once, with a private preview and optional add-ons later.'),
            'items': [
                _('Full business website'),
                _('Structured SEO setup'),
                _('Assisted content editing'),
                _('Built to help visitors contact your business'),
                _('Can grow later with catalog, online shop, extra pages, languages, or marketing'),
            ],
            'cta': _('See One-Time Website'),
            'url_name': 'core:one_time_website_plan',
            'featured': True,
        },
        {
            'title': _('Monthly Website'),
            'price': _('From EUR 49.90/month'),
            'text': _('A website plan with hosting, support, and ongoing website care included.'),
            'items': [
                _('Hosting included'),
                _('Website stays online'),
                _('Small updates and support'),
                _('Ongoing website care'),
                _('Optional content and promotion add-ons'),
            ],
            'cta': _('See Monthly Website'),
            'url_name': 'core:monthly_plan',
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
            'badge': '',
            'price': _('Custom scope'),
            'text': _('Catalog and online shop work is discussed based on the products, checkout flow, and store structure your business needs.'),
            'items': [
                _('Product pages'),
                _('Shopping cart and checkout'),
                _('Small business store setup'),
            ],
            'cta': _('Discuss eCommerce'),
            'url_name': 'core:ecommerce_plan',
        },
    ]


def ai_website_context():
    return {
        'page_eyebrow': _('Fast launch option'),
        'page_title': _('AI Starter'),
        'page_meta_description': _('See the AI Starter option from Get Online Fast for businesses that want a simple low-cost website starting point.'),
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
        'page_meta_description': _('Learn about the One-Time Website package from Get Online Fast for businesses that want a stronger website with one clear payment.'),
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
        'page_meta_description': _('Learn about the Monthly Plan from Get Online Fast for businesses that want hosting, support, and ongoing website care included.'),
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
