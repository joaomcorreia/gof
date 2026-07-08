import copy
import random
from difflib import SequenceMatcher

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
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
SUPPORTED_LANGUAGE_CODES = {code for code, _label in settings.LANGUAGES}


def _preferred_public_language(request):
    language = translation.get_language_from_request(request, check_path=False) or settings.LANGUAGE_CODE
    language_code = (language or settings.LANGUAGE_CODE).split('-', 1)[0].lower()
    if language_code in SUPPORTED_LANGUAGE_CODES:
        return language_code
    return 'en'


def redirect_public_entry_to_language(request, url_name):
    language_code = _preferred_public_language(request)
    with override(language_code):
        destination = reverse(url_name)
    query_string = request.META.get('QUERY_STRING', '').strip()
    if query_string:
        destination = f'{destination}?{query_string}'
    return HttpResponseRedirect(destination)


def unprefixed_staff_route_not_found(_request):
    return HttpResponse(status=403)


PUBLIC_INFO_PAGE_LINKS = {
    'contact': {'url_name': 'core:contact', 'label': _('Contact')},
    'plans': {'url_name': 'core:plans', 'label': _('Pricing')},
    'pricing': {'url_name': 'core:pricing', 'label': _('Pricing')},
    'websites': {'url_name': 'core:websites', 'label': _('Websites')},
    'ads': {'url_name': 'core:ads', 'label': _('Ads')},
    'online_shop': {'url_name': 'core:online_shop', 'label': _('Online Shop')},
    'payment_methods': {'url_name': 'core:payment_methods', 'label': _('Payment Methods')},
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
                'price_label': 'Ask for setup guidance',
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
                'price_label': 'Manual setup required',
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
                'price_label': 'Larger custom setup',
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
                'price_label': 'Vraag naar opzetadvies',
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
                'price_label': 'Handmatige setup nodig',
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
                'price_label': 'Grotere maatwerk setup',
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
    'fr': {
        'section_title': 'Catalogues et boutiques en ligne',
        'section_intro': (
            'Montrez vos produits, prenez des commandes par WhatsApp ou vendez en ligne avec une boutique WooCommerce. '
            'Commencez simplement avec un catalogue de produits, puis ajoutez le paiement, le checkout et une structure de boutique plus solide quand votre entreprise en a besoin.'
        ),
        'pricing_note': (
            'Les prix sont des prix de départ et hors TVA. Le prix final dépend du nombre de produits, de la structure du catalogue, '
            'des moyens de paiement, de la livraison, des langues, de la préparation du contenu et des intégrations nécessaires.'
        ),
        'options': [
            {
                'option_key': 'starter_catalog',
                'eyebrow': 'Catalogue de départ',
                'title': 'Catalogue de départ / commandes WhatsApp',
                'price_label': 'Demandez un conseil de mise en place',
                'summary': (
                    'Convient aux petits revendeurs, vendeurs de type Avon, menus, listes de stock, pièces et gammes de produits simples. '
                    'Les visiteurs consultent les produits et commandent via WhatsApp, téléphone ou formulaire de contact.'
                ),
                'good_for': [
                    'Petits revendeurs',
                    'Vendeurs de type Avon',
                    'Menus',
                    'Listes de stock',
                    'Pièces',
                    'Gammes de produits simples',
                ],
                'includes': [
                    'Pages de liste de produits ou de catalogue',
                    'Images et détails des produits',
                    'Catégories si nécessaire',
                    'Bouton de commande WhatsApp/contact',
                    'Pas de checkout complet nécessaire',
                    'Peut évoluer plus tard vers une boutique',
                ],
                'cta_label': 'Demander un catalogue',
                'cta_url_name': 'core:contact',
            },
            {
                'option_key': 'full_ecommerce',
                'eyebrow': 'eCommerce complet',
                'title': 'Boutique eCommerce complète',
                'price_label': 'Configuration manuelle nécessaire',
                'summary': (
                    'Convient aux entreprises qui veulent vendre en ligne avec panier, checkout et accompagnement pour la mise en place du paiement via WooCommerce.'
                ),
                'good_for': [
                    'Entreprises prêtes à vendre en ligne avec checkout',
                ],
                'includes': [
                    'Configuration WooCommerce',
                    'Pages produit et catégories',
                    'Panier et checkout',
                    'Accompagnement pour la configuration des paiements',
                    'Structure livraison et taxes/TVA',
                    'Tableau de bord de la boutique',
                ],
                'cta_label': 'Demander une boutique en ligne',
                'cta_url_name': 'core:contact',
            },
            {
                'option_key': 'reseller_ecommerce',
                'eyebrow': 'eCommerce revendeur',
                'title': 'eCommerce pour revendeurs',
                'price_label': 'Configuration sur mesure plus large',
                'summary': (
                    'Convient aux catalogues plus grands, gammes spécialisées, produits de négoce, pièces automobiles ou entreprises de type revendeur '
                    'qui ont besoin de plus de structure qu’une boutique de base.'
                ),
                'good_for': [
                    'Catalogues plus grands',
                    'Produits de négoce',
                    'Entreprises de pièces/véhicules',
                ],
                'includes': [
                    'Structure de catalogue plus grande',
                    'Catégories et filtres produit',
                    'Flux de demande de devis/commande',
                    'Présentation de produits de type revendeur',
                    'Planification d’une configuration sur mesure',
                    'Évolution possible vers checkout/paiement',
                ],
                'cta_label': 'Parler eCommerce revendeur',
                'cta_url_name': 'core:contact',
            },
        ],
    },
    'pt': {
        'section_title': 'Catálogos e lojas online',
        'section_intro': (
            'Mostre produtos, receba encomendas por WhatsApp ou venda online com uma loja WooCommerce. '
            'Comece de forma simples com um catálogo de produtos e depois avance para checkout, pagamentos e uma estrutura de loja mais forte quando o seu negócio precisar.'
        ),
        'pricing_note': (
            'Os preços são valores de partida e não incluem IVA. O preço final depende do número de produtos, da estrutura do catálogo, '
            'dos métodos de pagamento, da entrega, dos idiomas, da preparação do conteúdo e das integrações necessárias.'
        ),
        'options': [
            {
                'option_key': 'starter_catalog',
                'eyebrow': 'Catálogo inicial',
                'title': 'Catálogo inicial / encomendas por WhatsApp',
                'price_label': 'Peça orientação de configuração',
                'summary': (
                    'Indicado para pequenos revendedores, vendedores tipo Avon, menus, listas de stock, peças e gamas simples de produtos. '
                    'Os visitantes veem os produtos e encomendam por WhatsApp, telefone ou formulário de contacto.'
                ),
                'good_for': [
                    'Pequenos revendedores',
                    'Vendedores tipo Avon',
                    'Menus',
                    'Listas de stock',
                    'Peças',
                    'Gamas simples de produtos',
                ],
                'includes': [
                    'Páginas de lista de produtos ou catálogo',
                    'Imagens e detalhes dos produtos',
                    'Categorias se necessário',
                    'Botão de encomenda por WhatsApp/contacto',
                    'Sem checkout completo',
                    'Pode crescer mais tarde para uma loja',
                ],
                'cta_label': 'Perguntar sobre um catálogo',
                'cta_url_name': 'core:contact',
            },
            {
                'option_key': 'full_ecommerce',
                'eyebrow': 'eCommerce completo',
                'title': 'Loja eCommerce completa',
                'price_label': 'Configuração manual necessária',
                'summary': (
                    'Indicado para empresas que querem vender online com carrinho, checkout e apoio na configuração de pagamentos através do WooCommerce.'
                ),
                'good_for': [
                    'Empresas prontas para vender online com checkout',
                ],
                'includes': [
                    'Configuração WooCommerce',
                    'Páginas de produto e categorias',
                    'Carrinho e checkout',
                    'Apoio na configuração de pagamentos',
                    'Estrutura de envio e impostos/IVA',
                    'Painel da loja',
                ],
                'cta_label': 'Perguntar sobre uma loja online',
                'cta_url_name': 'core:contact',
            },
            {
                'option_key': 'reseller_ecommerce',
                'eyebrow': 'eCommerce para revenda',
                'title': 'eCommerce para revendedores',
                'price_label': 'Configuração personalizada maior',
                'summary': (
                    'Indicado para catálogos maiores, gamas especializadas, produtos de revenda, peças automóveis ou negócios de revenda '
                    'que precisam de mais estrutura do que uma loja básica.'
                ),
                'good_for': [
                    'Catálogos maiores',
                    'Produtos de revenda',
                    'Negócios de peças/veículos',
                ],
                'includes': [
                    'Estrutura de catálogo maior',
                    'Categorias e filtros de produto',
                    'Fluxo de pedido de orçamento/encomenda',
                    'Apresentação de produtos para revenda',
                    'Planeamento de configuração personalizada',
                    'Possível evolução para checkout/pagamentos',
                ],
                'cta_label': 'Falar sobre eCommerce de revenda',
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
    'fr': {
        'section_title': 'Faites connaître votre site',
        'section_intro': (
            'Le site est la base. La promotion aide les gens à le trouver réellement. Commencez avec des publications Facebook simples, '
            'des annonces locales ou des campagnes de recherche, puis améliorez étape par étape.'
        ),
        'pricing_note': (
            'Le budget publicitaire n’est pas inclus. Nous aidons à préparer ou configurer la promotion, mais Facebook, Instagram, '
            'Google et LinkedIn facturent séparément les clics, vues ou dépenses de campagne.'
        ),
        'options': [
            {
                'option_key': 'facebook_posts',
                'eyebrow': 'Promotion',
                'title': 'Publications Facebook',
                'price_label': '79 EUR / mois',
                'summary': 'Gardez votre page Facebook active avec des publications prêtes à l’emploi pour votre entreprise. Utile pour les services, mises à jour, offres, travaux récents et visibilité locale.',
                'cta_label': 'Voir les publications Facebook',
                'cta_url_name': 'core:facebook_posts',
            },
            {
                'option_key': 'meta_ads',
                'eyebrow': 'Promotion',
                'title': 'Publicités Facebook et Instagram',
                'price_label': 'À partir de 70 EUR',
                'summary': 'Touchez des clients locaux sur Facebook et Instagram avec des campagnes simples pour vos services, offres ou lancement de site.',
                'cta_label': 'Voir les pubs Meta',
                'cta_url_name': 'core:facebook_instagram_ads',
            },
            {
                'option_key': 'google_ads',
                'eyebrow': 'Promotion',
                'title': 'Google Ads',
                'price_label': 'À partir de 70 EUR',
                'summary': 'Montrez votre entreprise quand des personnes recherchent des services comme les vôtres dans votre zone. Idéal pour les demandes urgentes, services locaux et visiteurs à forte intention.',
                'cta_label': 'Voir Google Ads',
                'cta_url_name': 'core:google_ads',
            },
            {
                'option_key': 'linkedin_ads',
                'eyebrow': 'Promotion',
                'title': 'LinkedIn Ads',
                'price_label': 'À partir de 70 EUR',
                'summary': 'Faites la promotion de services professionnels auprès de professionnels, d’entreprises et de décideurs. Plus adapté au B2B qu’aux services grand public du quotidien.',
                'cta_label': 'Voir LinkedIn Ads',
                'cta_url_name': 'core:linkedin_ads',
            },
        ],
    },
    'pt': {
        'section_title': 'Promova o seu website',
        'section_intro': (
            'O website é a base. A promoção ajuda as pessoas a encontrá-lo de verdade. Comece com publicações simples no Facebook, '
            'anúncios locais ou campanhas de pesquisa e melhore a partir daí.'
        ),
        'pricing_note': (
            'O orçamento de anúncios não está incluído. Nós ajudamos a preparar ou configurar a promoção, mas Facebook, Instagram, '
            'Google e LinkedIn cobram separadamente por cliques, visualizações ou gasto de campanha.'
        ),
        'options': [
            {
                'option_key': 'facebook_posts',
                'eyebrow': 'Promoção',
                'title': 'Publicações no Facebook',
                'price_label': '79 EUR / mês',
                'summary': 'Mantenha a sua página de Facebook ativa com publicações preparadas para o seu negócio. Útil para serviços, atualizações, ofertas, trabalhos recentes e visibilidade local.',
                'cta_label': 'Ver publicações no Facebook',
                'cta_url_name': 'core:facebook_posts',
            },
            {
                'option_key': 'meta_ads',
                'eyebrow': 'Promoção',
                'title': 'Anúncios no Facebook e Instagram',
                'price_label': 'Desde 70 EUR',
                'summary': 'Chegue a clientes locais no Facebook e Instagram com campanhas simples para os seus serviços, ofertas ou lançamento do website.',
                'cta_label': 'Ver anúncios Meta',
                'cta_url_name': 'core:facebook_instagram_ads',
            },
            {
                'option_key': 'google_ads',
                'eyebrow': 'Promoção',
                'title': 'Google Ads',
                'price_label': 'Desde 70 EUR',
                'summary': 'Mostre o seu negócio quando as pessoas procuram serviços como os seus na sua zona. Bom para trabalhos urgentes, serviços locais e visitantes com forte intenção.',
                'cta_label': 'Ver Google Ads',
                'cta_url_name': 'core:google_ads',
            },
            {
                'option_key': 'linkedin_ads',
                'eyebrow': 'Promoção',
                'title': 'LinkedIn Ads',
                'price_label': 'Desde 70 EUR',
                'summary': 'Promova serviços empresariais junto de profissionais, empresas e decisores. Mais indicado para ofertas B2B do que para serviços do dia a dia para consumidores.',
                'cta_label': 'Ver LinkedIn Ads',
                'cta_url_name': 'core:linkedin_ads',
            },
        ],
    },
}

PROMOTION_PAGE_FALLBACKS = {
    'en': {
        'facebook_posts': {
            'eyebrow': 'Free with new websites',
            'title': 'Facebook Launch Posts',
            'price_label': 'Free with new website customers',
            'subtitle': 'Keep your new website and Facebook page active from day one.',
            'intro': 'Your new website should not launch alone. With Facebook Launch Posts, your business starts with ready-made posts and stories that point people to your website, Facebook page, phone, WhatsApp, and email.',
            'highlights': [
                {
                    'title': 'Included with setup',
                    'text': 'Need a Facebook page? We can help prepare one with your business details and website link.',
                },
                {
                    'title': 'Launch posts ready',
                    'text': 'Get 10 Facebook posts and 5 stories prepared for your first 5 weeks online.',
                },
                {
                    'title': 'More ways to be found',
                    'text': 'Send people to your website, Facebook page, phone, WhatsApp, or email.',
                },
            ],
            'sections': [
                {
                    'title': 'A simple Facebook start for your business',
                    'paragraphs': [
                        'When your website goes online, your Facebook page should also look active. Facebook Launch Posts help announce your services, recent work, offers, opening hours, photos, and contact details.',
                        'For new website customers, this launch pack can be included as a free start. You receive 10 Facebook posts and 5 Facebook stories, planned as 2 posts per week for 5 weeks, plus 1 story per week.',
                    ],
                    'image_label': 'Facebook launch example image',
                },
                {
                    'title': 'If you already have a Facebook page',
                    'paragraphs': [
                        'You do not need to add Get Online Fast as an admin. We can send the prepared posts to you by email with simple instructions, so you can copy, paste, and publish them yourself.',
                        'If you want us to publish the posts for you, you can add Get Online Fast as a publisher or editor on your Facebook page.',
                    ],
                },
                {
                    'title': 'What the posts can be about',
                    'bullets': [
                        'Your main services',
                        'Recent projects or work',
                        'Before and after photos',
                        'Offers or seasonal reminders',
                        'Opening hours',
                        'Website launch announcement',
                        'Phone, WhatsApp, and email contact',
                        'Trust and local business posts',
                    ],
                    'image_label': 'Post ideas preview',
                },
                {
                    'title': 'How often should a small business post?',
                    'paragraphs': [
                        'For most freelancers, handymen, salons, garages, shops, restaurants, and local service businesses, 2 to 3 posts per week is a good start. It keeps your page active without becoming too much work.',
                        'Stories are useful for quick updates, offers, photos, reminders, and simple "we are available" messages.',
                    ],
                },
                {
                    'title': 'After the launch pack',
                    'paragraphs': [
                        'The free launch pack helps your business start active after your website goes online. If you want your Facebook page to stay active every month, Get Online Fast also offers monthly Facebook post packages.',
                    ],
                },
            ],
            'faqs': [
                {
                    'question': 'Will these Facebook Launch Posts guarantee me new customers?',
                    'answer': 'No. No Facebook post service can promise guaranteed customers. The goal is to help your business look active, show your services, guide people to your website, and make it easier for them to contact you.',
                },
                {
                    'question': 'Do I need a Facebook Business Page?',
                    'answer': 'Yes, but if you do not have one yet, we can help prepare it as part of your website setup package.',
                },
                {
                    'question': 'Do I need to give Get Online Fast admin access?',
                    'answer': 'No. By default, we send the posts and simple instructions to you by email, so you can publish them yourself.',
                },
                {
                    'question': 'Can you publish the posts for me?',
                    'answer': 'Yes. If you want us to publish the posts, you can add Get Online Fast as a publisher or editor on your Facebook page.',
                },
                {
                    'question': 'Are Facebook ads included?',
                    'answer': 'No. This page is about prepared Facebook posts and stories. Paid Facebook ads are a separate service.',
                },
                {
                    'question': 'What happens after the first 5 weeks?',
                    'answer': 'You can continue posting yourself, or choose a monthly Facebook posts package if you want help keeping your page active.',
                },
            ],
            'faq_title': 'Questions about Facebook Launch Posts',
            'cta_label': 'Questions? Contact Get Online Fast',
            'cta_block_title': 'Ready to start your website and Facebook launch?',
            'cta_block_text': 'Start with your website today, and we can help prepare your first Facebook posts so your business looks active from day one.',
            'cta_block_primary_label': 'Start your website',
            'cta_block_primary_url_name': 'ai_starter:start',
            'cta_block_secondary_label': 'Contact Get Online Fast',
            'cta_block_secondary_url_name': 'core:contact',
        },
        'meta_ads': {
            'eyebrow': 'Promotion',
            'title': 'Facebook & Instagram Ads',
            'price_label': 'From EUR 70',
            'intro': 'Run simple local campaigns on Facebook and Instagram to promote your services, offers, or new website.',
            'sections': [
                {'title': 'What this is', 'paragraphs': ['A practical Facebook and Instagram ads setup service for small businesses that want more local visibility around a service area, offer, launch, or seasonal campaign.']},
                {'title': 'How the costs work', 'paragraphs': ['You pay a setup fee for the first campaign setup and guidance. You also choose the ad budget that is spent through Meta on Facebook and Instagram.', 'For this estimator, campaign budget is calculated as daily budget multiplied by the number of campaign days. Real delivery depends on the audience, service area, offer, creative, landing page, and competition.']},
                {'title': 'How it works', 'paragraphs': ['The first campaign is kept simple so you can review the direction before launch.'], 'bullets': ['Choose the platform', 'Choose your daily budget and campaign length', 'Choose the local targeting radius', 'We prepare the campaign', 'You review and launch', 'We check the basic campaign setup and performance']},
                {'title': 'What can affect results', 'bullets': ['Audience targeting', 'Service area and radius', 'Offer strength', 'Ad image or creative', 'Landing page quality', 'Local competition and seasonality']},
                {'title': 'Important note', 'paragraphs': ['Ad spend is paid separately through Meta. Results are not guaranteed.']},
            ],
            'cta_label': 'Request Meta Ads Help',
        },
        'google_ads': {
            'eyebrow': 'Promotion',
            'title': 'Google Ads',
            'price_label': 'From EUR 70',
            'intro': 'Help customers find your business when they are already searching for your services.',
            'sections': [
                {'title': 'What this is', 'paragraphs': ['A practical Google Ads setup service for local businesses that want to appear when people are already searching for a service or urgent solution.']},
                {'title': 'How the costs work', 'paragraphs': ['You pay a setup fee for the campaign setup, targeting direction, and first campaign structure. You also choose the ad budget that Google Ads uses during the campaign.', 'Google Ads often works with cost per click. Click prices can change based on keywords, location, industry, and competition. Daily budget helps control approximate spend, but results are not guaranteed.']},
                {'title': 'How it works', 'paragraphs': ['The first campaign is kept simple so you can review the direction before launch.'], 'bullets': ['Choose the platform', 'Choose your daily budget and campaign length', 'Choose the local targeting radius', 'We prepare the campaign', 'You review and launch', 'We check the basic campaign setup and performance']},
                {'title': 'What can affect results', 'bullets': ['Keyword competition', 'Search demand in your area', 'Service urgency', 'Landing page quality', 'Location targeting', 'Competitor activity']},
                {'title': 'Important note', 'paragraphs': ['Ad spend is paid separately through Google Ads. Results are not guaranteed.']},
            ],
            'cta_label': 'Request Google Ads Help',
        },
        'linkedin_ads': {
            'eyebrow': 'Promotion',
            'title': 'LinkedIn Ads',
            'price_label': 'From EUR 70',
            'intro': 'Promote business services to professionals, companies, and decision-makers.',
            'sections': [
                {'title': 'What this is', 'paragraphs': ['A practical LinkedIn Ads setup service for B2B companies, consultants, agencies, and professional services that want targeted visibility among business audiences.']},
                {'title': 'How the costs work', 'paragraphs': ['You pay a setup fee for the campaign setup, audience direction, and first campaign structure. You also choose the ad budget that LinkedIn uses during the campaign.', 'LinkedIn Ads are often more expensive than Facebook or Google because the targeting is more business and professional focused. Cost can depend on audience size, job roles, location, competition, and campaign objective. Results are not guaranteed.']},
                {'title': 'How it works', 'paragraphs': ['The first campaign is kept simple so you can review the direction before launch.'], 'bullets': ['Choose the platform', 'Choose your daily budget and campaign length', 'Choose the local targeting radius', 'We prepare the campaign', 'You review and launch', 'We check the basic campaign setup and performance']},
                {'title': 'What can affect results', 'bullets': ['Audience size and job roles', 'Business location and market', 'Campaign objective', 'Offer quality', 'Landing page quality', 'Competition for the same audience']},
                {'title': 'Important note', 'paragraphs': ['Ad spend is paid separately through LinkedIn Ads. Results are not guaranteed.']},
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
                {'title': 'Wat dit is', 'paragraphs': ['Een praktische Facebook en Instagram ads-opzet voor kleine bedrijven die lokaal beter zichtbaar willen zijn rond een dienst, actie, lancering of seizoenscampagne.']},
                {'title': 'Hoe de kosten werken', 'paragraphs': ['Je betaalt een setup fee voor de eerste campagne-opzet en begeleiding. Daarnaast kies je zelf het advertentiebudget dat via Meta op Facebook en Instagram wordt uitgegeven.', 'Voor deze simulator wordt het campagnebudget berekend als dagbudget maal het aantal campagnedagen. Werkelijke levering hangt af van doelgroep, servicegebied, aanbod, creatieve uiting, landingspagina en concurrentie.']},
                {'title': 'Hoe het werkt', 'paragraphs': ['De eerste campagne blijft eenvoudig zodat je de richting eerst kunt controleren voor de livegang.'], 'bullets': ['Kies het platform', 'Kies je dagbudget en campagneduur', 'Kies de lokale targeting-straal', 'Wij bereiden de campagne voor', 'Je controleert en lanceert', 'Wij controleren de basisopzet en prestaties van de campagne']},
                {'title': 'Wat invloed heeft op resultaat', 'bullets': ['Doelgroepselectie', 'Servicegebied en straal', 'Sterkte van het aanbod', 'Advertentiebeeld of creatieve uiting', 'Kwaliteit van de landingspagina', 'Lokale concurrentie en seizoen']},
                {'title': 'Belangrijke opmerking', 'paragraphs': ['Advertentiebudget wordt apart via Meta betaald. Resultaten zijn niet gegarandeerd.']},
            ],
            'cta_label': 'Vraag hulp bij Meta Ads',
        },
        'google_ads': {
            'eyebrow': 'Promotie',
            'title': 'Google Ads',
            'price_label': 'Vanaf EUR 70',
            'intro': 'Help klanten je bedrijf te vinden wanneer ze al zoeken naar jouw diensten.',
            'sections': [
                {'title': 'Wat dit is', 'paragraphs': ['Een praktische Google Ads-opzet voor lokale bedrijven die zichtbaar willen worden wanneer mensen al actief zoeken naar een dienst of snelle oplossing.']},
                {'title': 'Hoe de kosten werken', 'paragraphs': ['Je betaalt een setup fee voor de campagne-opzet, targeting-richting en eerste campagnestructuur. Daarnaast kies je het advertentiebudget dat tijdens de campagne via Google Ads wordt gebruikt.', 'Google Ads werkt vaak met kosten per klik. Klikprijzen kunnen veranderen op basis van zoekwoorden, locatie, branche en concurrentie. Het dagbudget helpt om de uitgaven ongeveer te sturen, maar resultaten zijn niet gegarandeerd.']},
                {'title': 'Hoe het werkt', 'paragraphs': ['De eerste campagne blijft eenvoudig zodat je de richting eerst kunt controleren voor de livegang.'], 'bullets': ['Kies het platform', 'Kies je dagbudget en campagneduur', 'Kies de lokale targeting-straal', 'Wij bereiden de campagne voor', 'Je controleert en lanceert', 'Wij controleren de basisopzet en prestaties van de campagne']},
                {'title': 'Wat invloed heeft op resultaat', 'bullets': ['Concurrentie op zoekwoorden', 'Zoekvolume in jouw regio', 'Spoed van de dienst', 'Kwaliteit van de landingspagina', 'Locatietargeting', 'Activiteit van concurrenten']},
                {'title': 'Belangrijke opmerking', 'paragraphs': ['Advertentiebudget wordt apart via Google Ads betaald. Resultaten zijn niet gegarandeerd.']},
            ],
            'cta_label': 'Vraag hulp bij Google Ads',
        },
        'linkedin_ads': {
            'eyebrow': 'Promotie',
            'title': 'LinkedIn Ads',
            'price_label': 'Vanaf EUR 70',
            'intro': 'Promoot zakelijke diensten bij professionals, bedrijven en beslissers.',
            'sections': [
                {'title': 'Wat dit is', 'paragraphs': ['Een praktische LinkedIn Ads-opzet voor B2B-bedrijven, consultants, agencies en professionele diensten die gericht zichtbaar willen zijn bij zakelijke doelgroepen.']},
                {'title': 'Hoe de kosten werken', 'paragraphs': ['Je betaalt een setup fee voor de campagne-opzet, doelgroep-richting en eerste campagnestructuur. Daarnaast kies je het advertentiebudget dat tijdens de campagne via LinkedIn wordt gebruikt.', 'LinkedIn Ads zijn vaak duurder dan Facebook of Google, omdat de targeting sterker op zakelijke en professionele doelgroepen is gericht. De kosten hangen af van doelgroepgrootte, functierollen, locatie, concurrentie en campagnedoel. Resultaten zijn niet gegarandeerd.']},
                {'title': 'Hoe het werkt', 'paragraphs': ['De eerste campagne blijft eenvoudig zodat je de richting eerst kunt controleren voor de livegang.'], 'bullets': ['Kies het platform', 'Kies je dagbudget en campagneduur', 'Kies de lokale targeting-straal', 'Wij bereiden de campagne voor', 'Je controleert en lanceert', 'Wij controleren de basisopzet en prestaties van de campagne']},
                {'title': 'Wat invloed heeft op resultaat', 'bullets': ['Grootte van de doelgroep en functierollen', 'Zakelijke locatie en markt', 'Campagnedoel', 'Sterkte van het aanbod', 'Kwaliteit van de landingspagina', 'Concurrentie voor dezelfde doelgroep']},
                {'title': 'Belangrijke opmerking', 'paragraphs': ['Advertentiebudget wordt apart via LinkedIn Ads betaald. Resultaten zijn niet gegarandeerd.']},
            ],
            'cta_label': 'Vraag hulp bij LinkedIn Ads',
        },
        'advice_title': 'Weet je niet zeker welke past?',
        'advice_text': 'Voor de meeste kleine lokale bedrijven zijn Facebook Posts of Google Ads meestal de eenvoudigste eerste stap.',
        'advice_button_label': 'Vraag advies',
    },
}

ADS_SIMULATOR_CONFIGS = {
    'en': {
        'meta_ads': {
            'platform_name': 'Facebook & Instagram Ads',
            'setup_fee': 49,
            'budget_presets': [5, 10, 15, 20],
            'duration_presets': [7, 14, 30],
            'radius_presets': [5, 10, 20, 30, 50],
            'default_budget': 5,
            'default_duration': 7,
            'default_radius': 20,
            'heading': 'Estimate your first campaign cost',
            'intro': 'Choose a daily budget, campaign length, and local targeting radius to see a simple estimate before you contact us.',
            'budget_label': 'Daily ad budget',
            'custom_budget_label': 'Custom daily budget',
            'duration_label': 'Campaign duration',
            'radius_label': 'Targeting radius',
            'radius_suffix': 'km',
            'duration_suffix': 'days',
            'daily_budget_suffix': '/day',
            'setup_fee_label': 'Setup fee',
            'daily_budget_label': 'Daily ad budget',
            'campaign_duration_label': 'Campaign duration',
            'estimated_budget_label': 'Estimated ad budget',
            'estimated_total_label': 'Estimated first campaign total',
            'radius_result_label': 'Selected targeting radius',
            'radius_result_suffix': 'around your selected service area',
            'disclaimer': 'This simulator is only an estimate. The selected radius is an estimated targeting area, not a guarantee that ads will show to every person inside it. Final cost and delivery depend on the selected budget, campaign settings, platform rules, competition, and audience availability. Results are not guaranteed.',
        },
        'google_ads': {
            'platform_name': 'Google Ads',
            'setup_fee': 69,
            'budget_presets': [10, 15, 25, 50],
            'duration_presets': [7, 14, 30],
            'radius_presets': [5, 10, 20, 30, 50],
            'default_budget': 10,
            'default_duration': 14,
            'default_radius': 20,
            'heading': 'Estimate your first campaign cost',
            'intro': 'Choose a daily budget, campaign length, and local targeting radius to see a simple estimate before you contact us.',
            'budget_label': 'Daily ad budget',
            'custom_budget_label': 'Custom daily budget',
            'duration_label': 'Campaign duration',
            'radius_label': 'Targeting radius',
            'radius_suffix': 'km',
            'duration_suffix': 'days',
            'daily_budget_suffix': '/day',
            'setup_fee_label': 'Setup fee',
            'daily_budget_label': 'Daily ad budget',
            'campaign_duration_label': 'Campaign duration',
            'estimated_budget_label': 'Estimated ad budget',
            'estimated_total_label': 'Estimated first campaign total',
            'radius_result_label': 'Selected targeting radius',
            'radius_result_suffix': 'around your selected service area',
            'disclaimer': 'This simulator is only an estimate. The selected radius is an estimated targeting area, not a guarantee that ads will show to every person inside it. Final cost and delivery depend on the selected budget, campaign settings, platform rules, competition, and audience availability. Results are not guaranteed.',
        },
        'linkedin_ads': {
            'platform_name': 'LinkedIn Ads',
            'setup_fee': 89,
            'budget_presets': [15, 25, 50, 100],
            'duration_presets': [7, 14, 30],
            'radius_presets': [10, 20, 30, 50, 100],
            'default_budget': 15,
            'default_duration': 14,
            'default_radius': 30,
            'heading': 'Estimate your first campaign cost',
            'intro': 'Choose a daily budget, campaign length, and local targeting radius to see a simple estimate before you contact us.',
            'budget_label': 'Daily ad budget',
            'custom_budget_label': 'Custom daily budget',
            'duration_label': 'Campaign duration',
            'radius_label': 'Targeting radius',
            'radius_suffix': 'km',
            'duration_suffix': 'days',
            'daily_budget_suffix': '/day',
            'setup_fee_label': 'Setup fee',
            'daily_budget_label': 'Daily ad budget',
            'campaign_duration_label': 'Campaign duration',
            'estimated_budget_label': 'Estimated ad budget',
            'estimated_total_label': 'Estimated first campaign total',
            'radius_result_label': 'Selected targeting radius',
            'radius_result_suffix': 'around your selected service area',
            'disclaimer': 'This simulator is only an estimate. The selected radius is an estimated targeting area, not a guarantee that ads will show to every person inside it. Final cost and delivery depend on the selected budget, campaign settings, platform rules, competition, and audience availability. Results are not guaranteed.',
        },
    },
    'nl': {
        'meta_ads': {
            'platform_name': 'Facebook & Instagram Ads',
            'setup_fee': 49,
            'budget_presets': [5, 10, 15, 20],
            'duration_presets': [7, 14, 30],
            'radius_presets': [5, 10, 20, 30, 50],
            'default_budget': 5,
            'default_duration': 7,
            'default_radius': 20,
            'heading': 'Bereken een eenvoudige eerste campagneprijs',
            'intro': 'Kies een dagbudget, campagneduur en lokale targeting-straal om eerst een eenvoudige schatting te zien voordat je contact opneemt.',
            'budget_label': 'Dagelijks advertentiebudget',
            'custom_budget_label': 'Aangepast dagbudget',
            'duration_label': 'Campagneduur',
            'radius_label': 'Targeting-straal',
            'radius_suffix': 'km',
            'duration_suffix': 'dagen',
            'daily_budget_suffix': '/dag',
            'setup_fee_label': 'Setup fee',
            'daily_budget_label': 'Dagelijks advertentiebudget',
            'campaign_duration_label': 'Campagneduur',
            'estimated_budget_label': 'Geschat advertentiebudget',
            'estimated_total_label': 'Geschatte totale eerste campagne',
            'radius_result_label': 'Geselecteerde targeting-straal',
            'radius_result_suffix': 'rond je gekozen servicegebied',
            'disclaimer': 'Deze simulator is alleen een schatting. De gekozen straal is een geschat targeting-gebied en geen garantie dat advertenties aan iedere persoon binnen die straal worden getoond. De uiteindelijke kosten en levering hangen af van het gekozen budget, campagne-instellingen, platformregels, concurrentie en beschikbaarheid van doelgroepen. Resultaten zijn niet gegarandeerd.',
        },
        'google_ads': {
            'platform_name': 'Google Ads',
            'setup_fee': 69,
            'budget_presets': [10, 15, 25, 50],
            'duration_presets': [7, 14, 30],
            'radius_presets': [5, 10, 20, 30, 50],
            'default_budget': 10,
            'default_duration': 14,
            'default_radius': 20,
            'heading': 'Bereken een eenvoudige eerste campagneprijs',
            'intro': 'Kies een dagbudget, campagneduur en lokale targeting-straal om eerst een eenvoudige schatting te zien voordat je contact opneemt.',
            'budget_label': 'Dagelijks advertentiebudget',
            'custom_budget_label': 'Aangepast dagbudget',
            'duration_label': 'Campagneduur',
            'radius_label': 'Targeting-straal',
            'radius_suffix': 'km',
            'duration_suffix': 'dagen',
            'daily_budget_suffix': '/dag',
            'setup_fee_label': 'Setup fee',
            'daily_budget_label': 'Dagelijks advertentiebudget',
            'campaign_duration_label': 'Campagneduur',
            'estimated_budget_label': 'Geschat advertentiebudget',
            'estimated_total_label': 'Geschatte totale eerste campagne',
            'radius_result_label': 'Geselecteerde targeting-straal',
            'radius_result_suffix': 'rond je gekozen servicegebied',
            'disclaimer': 'Deze simulator is alleen een schatting. De gekozen straal is een geschat targeting-gebied en geen garantie dat advertenties aan iedere persoon binnen die straal worden getoond. De uiteindelijke kosten en levering hangen af van het gekozen budget, campagne-instellingen, platformregels, concurrentie en beschikbaarheid van doelgroepen. Resultaten zijn niet gegarandeerd.',
        },
        'linkedin_ads': {
            'platform_name': 'LinkedIn Ads',
            'setup_fee': 89,
            'budget_presets': [15, 25, 50, 100],
            'duration_presets': [7, 14, 30],
            'radius_presets': [10, 20, 30, 50, 100],
            'default_budget': 15,
            'default_duration': 14,
            'default_radius': 30,
            'heading': 'Bereken een eenvoudige eerste campagneprijs',
            'intro': 'Kies een dagbudget, campagneduur en lokale targeting-straal om eerst een eenvoudige schatting te zien voordat je contact opneemt.',
            'budget_label': 'Dagelijks advertentiebudget',
            'custom_budget_label': 'Aangepast dagbudget',
            'duration_label': 'Campagneduur',
            'radius_label': 'Targeting-straal',
            'radius_suffix': 'km',
            'duration_suffix': 'dagen',
            'daily_budget_suffix': '/dag',
            'setup_fee_label': 'Setup fee',
            'daily_budget_label': 'Dagelijks advertentiebudget',
            'campaign_duration_label': 'Campagneduur',
            'estimated_budget_label': 'Geschat advertentiebudget',
            'estimated_total_label': 'Geschatte totale eerste campagne',
            'radius_result_label': 'Geselecteerde targeting-straal',
            'radius_result_suffix': 'rond je gekozen servicegebied',
            'disclaimer': 'Deze simulator is alleen een schatting. De gekozen straal is een geschat targeting-gebied en geen garantie dat advertenties aan iedere persoon binnen die straal worden getoond. De uiteindelijke kosten en levering hangen af van het gekozen budget, campagne-instellingen, platformregels, concurrentie en beschikbaarheid van doelgroepen. Resultaten zijn niet gegarandeerd.',
        },
    },
}

ASSISTANT_PUBLIC_KNOWLEDGE = {
    'en': {
        'greeting': (
            'Hi! I\'m the Get Online Fast helper. I can help with websites, plans, support, payment, and how the platform works. '
            'What would you like to know?'
        ),
        'fallback': (
            'I can help with Starter Page, business websites, monthly website plans, online shop options, promotion, payment, and support. '
            'Try asking "What kind of website can I build here?" or "Which plan fits my business?"'
        ),
        'website_options': (
            'You can start with a Starter Page for a quick generated page, a One-Time Website for a full business website, '
            'or a Monthly Website if you want hosting, support, and ongoing care included. If you need products, you can also '
            'start with a product catalog or move to an online shop with checkout later. For most small local businesses, a clear '
            'business website is the best default unless you only need a quick page first.'
        ),
        'promotion_guarantee': (
            'No. Promotion can increase visibility, but it cannot guarantee customers, sales, bookings, leads, rankings, results, or revenue. '
            'Get Online Fast can help with launch Facebook posts, Meta ads, Google Ads support, and LinkedIn ads, but results depend on your offer, '
            'location, competition, budget, message, and how people respond.'
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
            'The right setup depends on your products, payments, shipping, languages, and how much structure you need. '
            'The best current overview is on the online shop page.'
        ),
        'promotion': (
            'Yes. Get Online Fast can also help promote your website after launch with Facebook posts, Meta ads, Google Ads support, '
            'or LinkedIn ads for B2B offers. A simple starting point is usually Facebook Posts or Google Ads, depending on your business. '
            'Promotion can help more people find you, but it cannot guarantee customers, sales, or rankings.'
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
            'Ik kan helpen met Starter Page, bedrijfswebsites, maandelijkse websiteplannen, webshopopties, promotie, betaling en support. '
            'Probeer bijvoorbeeld: "Welk soort website kan ik hier starten?" of "Welk pakket past bij mijn bedrijf?"'
        ),
        'website_options': (
            'Je kunt beginnen met een Starter Page voor een snelle gegenereerde pagina, een One-Time Website voor een volledige bedrijfswebsite, '
            'of een Monthly Website als je hosting, support en doorlopende zorg inbegrepen wilt hebben. Als je producten wilt tonen, kun je ook '
            'starten met een productcatalogus en later doorgroeien naar een online shop met checkout. Voor de meeste kleine lokale bedrijven is '
            'een duidelijke bedrijfswebsite de beste start, tenzij je eerst alleen een snelle pagina nodig hebt.'
        ),
        'promotion_guarantee': (
            'Nee. Promotie kan de zichtbaarheid vergroten, maar het kan geen klanten, verkopen, boekingen, leads, rankings, resultaten of omzet garanderen. '
            'Get Online Fast kan helpen met launch Facebook posts, Meta ads, Google Ads-ondersteuning en LinkedIn ads, maar de uitkomst hangt af van je aanbod, '
            'locatie, concurrentie, budget, boodschap en hoe mensen reageren.'
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
            'De juiste opzet hangt af van je producten, betalingen, verzending, talen en hoeveel structuur je nodig hebt. '
            'Het beste huidige overzicht staat op de online-shop pagina.'
        ),
        'promotion': (
            'Ja. Get Online Fast kan ook helpen om je website na livegang te promoten met Facebook posts, Meta ads, Google Ads-ondersteuning '
            'of LinkedIn ads voor B2B-aanbiedingen. Voor veel kleine lokale bedrijven zijn Facebook Posts of Google Ads meestal de eenvoudigste eerste stap. '
            'Promotie kan helpen om meer mensen te bereiken, maar het garandeert geen klanten, verkopen of rankings.'
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
    'fr': {
        'greeting': (
            'Bonjour. Je suis l’assistant public de Get Online Fast. Je peux vous aider pour les sites web, les plans, le support, le paiement '
            'et la meilleure première étape. Que voulez-vous savoir ?'
        ),
        'fallback': (
            'Je peux surtout aider pour la Starter Page, les sites professionnels, les plans mensuels, les boutiques en ligne, la promotion, le paiement et le support. '
            'Essayez par exemple : "Quel type de site puis-je créer ici ?" ou "Quel plan convient à mon entreprise ?"'
        ),
        'website_options': (
            'Vous pouvez commencer avec une Starter Page pour une page rapide générée, un site en paiement unique pour un vrai site professionnel, '
            'ou un site mensuel si vous voulez l’hébergement, le support et le suivi inclus. Si vous avez des produits, vous pouvez aussi commencer '
            'avec un catalogue puis ajouter une boutique en ligne avec paiement plus tard. Pour la plupart des petites entreprises locales, un site '
            'professionnel clair est le meilleur point de départ, sauf si vous avez seulement besoin d’une page rapide.'
        ),
        'promotion_guarantee': (
            'Non. La promotion peut améliorer la visibilité, mais elle ne peut pas garantir des clients, des ventes, des réservations, des leads, '
            'des classements, des résultats ou du chiffre d’affaires. Get Online Fast peut aider avec des posts Facebook de lancement, des publicités Meta, '
            'un accompagnement Google Ads et LinkedIn Ads, mais les résultats dépendent de votre offre, de votre zone, de la concurrence, du budget, du message '
            'et de la réaction du public.'
        ),
        'plans': (
            'Get Online Fast propose des options de site pratiques pour les petites entreprises, y compris la Starter Page, un site en paiement unique, '
            'un site mensuel et des options de catalogue ou boutique en ligne. Le meilleur aperçu de départ se trouve sur {plans_url}.'
        ),
        'preview': (
            'La création publique d’aperçu n’est pas disponible pour le moment. Contactez Get Online Fast et nous vous aiderons à choisir la bonne configuration.'
        ),
        'ecommerce': (
            'Oui. Get Online Fast peut aider avec les catalogues de produits, les catalogues de commande via WhatsApp et les boutiques WordPress/WooCommerce. '
            'La bonne configuration dépend de vos produits, des paiements, de la livraison, des langues et du niveau de structure nécessaire. '
            'Le meilleur aperçu actuel se trouve sur la page boutique en ligne.'
        ),
        'promotion': (
            'Oui. Get Online Fast peut aussi aider à promouvoir votre site après le lancement avec des posts Facebook, des publicités Meta, Google Ads '
            'ou LinkedIn Ads. Pour beaucoup de petites entreprises locales, les posts de lancement ou Google Ads sont le point de départ le plus simple.'
        ),
        'activation': (
            'Quand votre site est prêt pour l’activation, Get Online Fast envoie la bonne page d’activation ou le bon lien de paiement. '
            'Le paiement est traité en toute sécurité par Stripe. Après paiement, l’activation et la remise sont vérifiées manuellement.'
        ),
        'payment': (
            'Le paiement est traité en toute sécurité par Stripe. Si vous souhaitez activer un site, Get Online Fast fournit le bon lien de paiement '
            'ou la bonne page d’activation. Vous pouvez aussi consulter les informations de paiement sur {payment_url}.'
        ),
        'included': (
            'Get Online Fast propose des services pratiques pour les petites entreprises, avec configuration WordPress, support '
            'et options de croissance. Le meilleur aperçu se trouve sur {included_url}.'
        ),
        'support': (
            'Le support passe par Get Online Fast. Utilisez {support_url} pour une aide pratique et {contact_url} si vous avez besoin d’un contact direct '
            'au sujet de la configuration, du paiement, du support ou de travaux supplémentaires.'
        ),
        'dashboard': (
            'Le tableau de bord WordPress sert aux mises à jour pratiques comme le contenu, les images, les services et les projets quand cela fait partie de votre configuration.'
        ),
        'email': (
            'L’e-mail professionnel ou l’e-mail de domaine peut être demandé séparément. Si vous avez besoin d’aide pour les boîtes mail ou l’adresse d’entreprise, '
            'utilisez {contact_url} afin que Get Online Fast confirme le périmètre.'
        ),
        'changes': (
            'Oui. Des changements, ajustements ou travaux supplémentaires peuvent être demandés séparément. Ce n’est pas inclus de façon illimitée par défaut, '
            'donc le mieux est de demander via {contact_url}.'
        ),
        'company_legal': (
            'Get Online Fast est exploité par Just Code Works, basé à Amsterdam, aux Pays-Bas. Vous pouvez consulter les Conditions sur {terms_url}, '
            'la Politique de confidentialité sur {privacy_url}, la Politique de cookies sur {cookies_url} et les informations de paiement sur {payment_url}. '
            'Cet assistant ne donne pas de conseil juridique.'
        ),
    },
    'pt': {
        'greeting': (
            'Olá. Sou o assistente público do Get Online Fast. Posso ajudar com websites, planos, suporte, pagamento '
            'e o melhor próximo passo. Sobre o que quer saber?'
        ),
        'fallback': (
            'Posso ajudar sobretudo com Starter Page, websites empresariais, planos mensais, loja online, promoção, pagamento e suporte. '
            'Pode perguntar, por exemplo: "Que tipo de website posso criar aqui?" ou "Que website devo escolher?"'
        ),
        'website_options': (
            'Pode começar com uma Starter Page para uma página rápida gerada, um One-Time Website para um website empresarial completo, '
            'ou um Monthly Website se quiser alojamento, suporte e acompanhamento incluídos. Se precisar de produtos, também pode começar '
            'com um catálogo e mais tarde avançar para uma loja online com checkout. Para a maioria dos pequenos negócios locais, um website '
            'empresarial claro é o melhor ponto de partida, a menos que precise apenas de uma página rápida.'
        ),
        'promotion_guarantee': (
            'Não. Promoção pode aumentar a visibilidade, mas não pode garantir clientes, vendas, marcações, leads, rankings, resultados ou receita. '
            'O Get Online Fast pode ajudar com posts de lançamento no Facebook, anúncios Meta, apoio com Google Ads e LinkedIn Ads, mas os resultados '
            'dependem da sua oferta, localização, concorrência, orçamento, mensagem e da resposta do público.'
        ),
        'plans': (
            'O Get Online Fast oferece opções práticas para pequenas empresas, incluindo Starter Page, website de pagamento único, '
            'website mensal e opções de catálogo ou loja online. A melhor visão geral inicial está em {plans_url}.'
        ),
        'preview': (
            'A criação pública de pré-visualizações não está disponível neste momento. Contacte o Get Online Fast e ajudamos a escolher a configuração certa.'
        ),
        'ecommerce': (
            'Sim. O Get Online Fast pode ajudar com catálogos de produtos, catálogos de encomenda por WhatsApp e lojas WordPress/WooCommerce. '
            'A configuração certa depende dos seus produtos, pagamentos, envios, idiomas e do nível de estrutura necessário. '
            'A melhor visão geral neste momento está na página da loja online.'
        ),
        'promotion': (
            'Sim. O Get Online Fast também pode ajudar a promover o seu website depois do lançamento com posts de Facebook, anúncios Meta, Google Ads '
            'ou LinkedIn Ads. Para muitas pequenas empresas locais, posts de lançamento ou Google Ads são o ponto de partida mais simples.'
        ),
        'activation': (
            'Quando o seu website estiver pronto para ativação, o Get Online Fast envia a página de ativação ou link de pagamento correto. '
            'O pagamento é tratado com segurança pela Stripe. Depois do pagamento, a ativação e a entrega são verificadas manualmente.'
        ),
        'payment': (
            'O pagamento é tratado com segurança pela Stripe. Se quiser ativar um website, o Get Online Fast fornece o link de pagamento '
            'ou página de ativação correta. Também pode consultar a informação de pagamento em {payment_url}.'
        ),
        'included': (
            'O Get Online Fast oferece serviços práticos de website para pequenas empresas, incluindo configuração WordPress, suporte '
            'e opções de crescimento. A melhor visão geral está em {included_url}.'
        ),
        'support': (
            'O suporte é tratado através do Get Online Fast. Use {support_url} para ajuda prática e {contact_url} se precisar de contacto direto '
            'sobre configuração, pagamento, suporte ou trabalho adicional.'
        ),
        'dashboard': (
            'O painel WordPress serve para atualizações práticas como conteúdo, imagens, serviços e projetos quando isso faz parte da configuração do seu website.'
        ),
        'email': (
            'O email profissional ou email de domínio pode ser pedido em separado. Se precisar de ajuda com caixas de correio ou endereço empresarial, '
            'use {contact_url} para que o Get Online Fast confirme o âmbito.'
        ),
        'changes': (
            'Sim. Alterações, edições ou trabalho extra podem ser pedidos em separado. Isso não é ilimitado por defeito, '
            'por isso o melhor é pedir através de {contact_url}.'
        ),
        'company_legal': (
            'O Get Online Fast é operado pela Just Code Works, com base em Amesterdão, Países Baixos. Pode consultar os Termos em {terms_url}, '
            'a Política de Privacidade em {privacy_url}, a Política de Cookies em {cookies_url} e a informação de pagamento em {payment_url}. '
            'Este assistente não dá aconselhamento jurídico.'
        ),
    },
}

ASSISTANT_INTENT_KEYWORDS = {
    'greeting': {
        'en': ['hi', 'hello', 'hey'],
        'nl': ['hallo', 'hoi', 'goedemorgen', 'goedemiddag', 'goedenavond'],
        'fr': ['bonjour', 'salut', 'bonsoir', 'coucou'],
        'pt': ['ola', 'olá', 'bom dia', 'boa tarde', 'boa noite'],
    },
    'activation': {
        'en': ['activation', 'activate', 'go live', 'handoff', 'launch'],
        'nl': ['activatie', 'activeren', 'website activeren', 'live zetten', 'online zetten', 'oplevering'],
    },
    'preview': {
        'en': ['preview', 'start', 'create preview', 'start preview', 'ai preview', 'starter page generator'],
        'nl': ['preview', 'voorbeeld', 'start', 'preview maken', 'start preview', 'ai preview', 'starterpagina generator'],
        'fr': ['apercu', 'aperçu', 'starter page', 'page de depart', 'page de départ', 'commencer'],
        'pt': ['pre-visualizacao', 'pré-visualização', 'starter page', 'pagina inicial', 'página inicial', 'comecar', 'começar'],
    },
    'website_options': {
        'en': [
            'what kind of website',
            'what website can i make',
            'what website can i build',
            'what can i build here',
            'what kind of site',
            'which website should i start',
            'can i build a shop',
            'do i need a full website',
            'website options',
            'business website',
            'full business website',
            'monthly website',
            'one-time website',
            'starter page',
        ],
        'nl': [
            'welk soort website',
            'wat voor website',
            'welke website kan ik hier',
            'welke website moet ik starten',
            'welke website moet ik kiezen',
            'kan ik een webshop bouwen',
            'heb ik een volledige website nodig',
            'website opties',
            'bedrijfswebsite',
            'maandelijkse website',
            'one-time website',
            'starter page',
        ],
        'fr': [
            'quel type de site',
            'quel site puis-je creer',
            'quel site puis-je créer',
            'quel site puis-je faire',
            'puis-je creer une boutique',
            'puis-je créer une boutique',
            'quelles options de site',
            'site professionnel',
            'starter page',
            'site mensuel',
        ],
        'pt': [
            'que tipo de website',
            'que website posso criar',
            'que site posso criar',
            'que tipo de site posso fazer aqui',
            'que website posso fazer aqui',
            'que website posso fazer',
            'posso criar uma loja',
            'preciso de um website completo',
            'opcoes de website',
            'opções de website',
            'website empresarial',
            'monthly website',
            'one-time website',
            'starter page',
        ],
    },
    'promotion_guarantee': {
        'en': [
            'do ads guarantee',
            'can ads guarantee',
            'google ads guarantee',
            'meta ads guarantee',
            'facebook ads guarantee',
            'linkedin ads guarantee',
            'marketing guarantee',
            'do you guarantee rankings',
            'guarantee rankings',
            'guaranteed rankings',
            'seo guarantee',
            'seo guarantees',
            'guarantee customers',
            'guarantee sales',
            'guarantee leads',
            'guarantee results',
        ],
        'nl': [
            'garanderen ads',
            'garanderen advertenties',
            'garandeert google ads',
            'garanderen google ads',
            'garanderen meta ads',
            'garanderen facebook ads',
            'garanderen linkedin ads',
            'garanderen rankings',
            'gegarandeerde rankings',
            'seo garantie',
            'seo garanties',
            'garandeert klanten',
            'garandeert verkopen',
            'garandeert leads',
            'garandeert resultaten',
        ],
        'fr': [
            'garantissent les publicites',
            'garantissent les publicités',
            'google ads garantit',
            'garantissez les classements',
            'garantie seo',
            'garantit des clients',
            'garantit des ventes',
            'garantit des resultats',
            'garantit des résultats',
        ],
        'pt': [
            'anuncios garantem',
            'anúncios garantem',
            'google ads garante',
            'meta ads garante',
            'facebook ads garante',
            'linkedin ads garante',
            'garante rankings',
            'garantia seo',
            'garante clientes',
            'garante vendas',
            'garante leads',
            'garante resultados',
        ],
    },
    'ecommerce': {
        'en': ['catalog', 'catalogs', 'catalogue', 'shop', 'online shop', 'online shops', 'ecommerce', 'woo commerce', 'woocommerce', 'webshop', 'products', 'reseller'],
        'nl': ['catalogus', 'catalogussen', 'webshop', 'webshops', 'online shop', 'online shops', 'woocommerce', 'producten', 'reseller', 'bestellen via whatsapp'],
        'fr': ['catalogue', 'boutique', 'boutique en ligne', 'ecommerce', 'woocommerce', 'produits'],
        'pt': ['catalogo', 'catálogo', 'loja online', 'ecommerce', 'woocommerce', 'produtos'],
    },
    'promotion': {
        'en': ['promotion', 'promote', 'ads', 'google ads', 'facebook posts', 'facebook ads', 'instagram ads', 'linkedin ads', 'meta ads', 'marketing'],
        'nl': ['promotie', 'promoten', 'ads', 'google ads', 'facebook posts', 'facebook ads', 'instagram ads', 'linkedin ads', 'meta ads', 'marketing'],
        'fr': ['promotion', 'publicite', 'publicité', 'annonces', 'google ads', 'facebook posts', 'facebook ads', 'instagram ads', 'linkedin ads', 'meta ads'],
        'pt': ['promocao', 'promoção', 'anuncios', 'anúncios', 'google ads', 'facebook posts', 'facebook ads', 'instagram ads', 'linkedin ads', 'meta ads'],
    },
    'payment': {
        'en': ['pay', 'payment', 'stripe', 'invoice'],
        'nl': ['betalen', 'betaling', 'betaallink', 'stripe', 'factuur'],
        'fr': ['paiement', 'payer', 'stripe', 'facture'],
        'pt': ['pagamento', 'pagar', 'stripe', 'fatura', 'factura'],
    },
    'plans': {
        'en': ['plan', 'plans', 'package', 'packages', 'pricing', 'website prices', 'view prices', 'price', 'prices', 'cost', 'costs', 'start a website'],
        'nl': ['pakket', 'pakketten', 'pricing', 'prijzen', 'website prijzen', 'prijs', 'kosten', 'website starten', 'website beginnen'],
        'fr': ['plan', 'plans', 'tarif', 'tarifs', 'prix', 'cout', 'coût', 'site web'],
        'pt': ['plano', 'planos', 'preco', 'preço', 'precos', 'preços', 'custo', 'custos', 'website'],
    },
    'included': {
        'en': ['included', 'what do i get', 'package', 'website setup'],
        'nl': ['inbegrepen', 'wat krijg ik', 'pakket', 'website setup'],
        'fr': ['inclus', 'ce que je recois', 'ce que je reçois', 'configuration du site'],
        'pt': ['incluido', 'incluído', 'o que recebo', 'configuracao do website', 'configuração do website'],
    },
    'support': {
        'en': ['support', 'help', 'contact'],
        'nl': ['support', 'hulp', 'ondersteuning', 'vraag', 'contact'],
        'fr': ['support', 'aide', 'contact'],
        'pt': ['suporte', 'ajuda', 'contacto', 'contato'],
    },
    'dashboard': {
        'en': ['dashboard', 'edit', 'content', 'images', 'services', 'projects'],
        'nl': ['dashboard', 'aanpassen', 'teksten', 'afbeeldingen', 'diensten', 'projecten'],
        'fr': ['dashboard', 'modifier', 'contenu', 'images', 'services', 'projets'],
        'pt': ['dashboard', 'editar', 'conteudo', 'conteúdo', 'imagens', 'servicos', 'serviços', 'projetos'],
    },
    'email': {
        'en': ['email', 'mailbox', 'business email', 'domain email'],
        'nl': ['email', 'e-mail', 'mailbox', 'info@', 'domeinmail'],
        'fr': ['email', 'e-mail', 'boite mail', 'boîte mail', 'adresse professionnelle'],
        'pt': ['email', 'e-mail', 'caixa de correio', 'email profissional', 'email de dominio', 'email de domínio'],
    },
    'changes': {
        'en': ['changes', 'extra work', 'edits', 'updates'],
        'nl': ['wijziging', 'wijzigingen', 'extra werk', 'aanpassing', 'meerwerk'],
        'fr': ['modification', 'modifications', 'travail supplementaire', 'travail supplémentaire', 'mise a jour', 'mise à jour'],
        'pt': ['alteracao', 'alteração', 'alteracoes', 'alterações', 'trabalho extra', 'edicoes', 'edições', 'atualizacoes', 'atualizações'],
    },
    'company_legal': {
        'en': ['terms', 'privacy', 'cookies', 'company', 'just code works', 'amsterdam'],
        'nl': ['voorwaarden', 'privacy', 'cookies', 'bedrijf', 'just code works', 'amsterdam'],
        'fr': ['conditions', 'confidentialite', 'confidentialité', 'cookies', 'entreprise', 'amsterdam'],
        'pt': ['termos', 'privacidade', 'cookies', 'empresa', 'amesterdao', 'amesterdão', 'amsterdam'],
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
        'eyebrow': 'Online Shop',
        'title': 'Online shop and product catalog',
        'meta_description': 'See how Get Online Fast can prepare a small online shop or product catalog for your business.',
        'intro': (
            'Start simple with a product catalog or a small online shop, then grow into payments, checkout, and a stronger store structure when your business is ready.'
        ),
        'promotion_layout': True,
        'sections': [],
        'related_links': ['pricing', 'contact'],
        'sidebar_title': 'Online shop links',
        'cta_block_title': 'Need a small online shop or product catalog?',
        'cta_block_text': 'Contact Get Online Fast and we can help you choose the right shop setup for your business.',
        'cta_block_primary_label': 'Contact Get Online Fast',
        'cta_block_primary_url_name': 'core:contact',
        'cta_block_secondary_label': 'View pricing',
        'cta_block_secondary_url_name': 'core:pricing',
    },
    'websites': {
        'eyebrow': 'Websites',
        'title': 'Simple professional websites for small businesses',
        'meta_description': 'Get Online Fast builds simple professional websites for small businesses. Send your details, review the first version, and go live after approval.',
        'intro': (
            'Send your business details, services, photos, and contact information. Get Online Fast prepares the first version for you, you review it, and your website can be published after approval and payment.'
        ),
        'promotion_layout': True,
        'cta_label': 'View pricing',
        'cta_url_name': 'core:pricing',
        'cta_secondary_label': 'Contact us',
        'cta_secondary_url_name': 'core:contact',
        'highlights': [
            {'title': 'Built for small businesses', 'text': 'Clear service pages, contact details, local information, and simple calls to action so customers understand what you do.'},
            {'title': 'Prepared for you', 'text': 'You do not need to write the whole website alone. Send the basics and we prepare the first version.'},
            {'title': 'Ready to grow later', 'text': 'Add extra pages, product options, images, posts, ads, email, or support when your business needs them.'},
        ],
        'sections': [
            {
                'layout': 'feature',
                'title': 'A practical website start',
                'paragraphs': [
                    'This is for freelancers, local services, trades, garages, restaurants, salons, shops, cleaning companies, moving services, transport, consultants, and other small businesses that need a clear public website without a long project.',
                    'Your first version is prepared around your business type, services, location, and contact details, so visitors can quickly understand what you offer and how to reach you.',
                ],
                'image_label': 'Website example',
            },
            {
                'layout': 'included_grid',
                'title': 'What your first website can include',
                'paragraphs': [
                    'A first business website can stay simple while still covering the pages and contact details customers expect.',
                ],
                'items': [
                    'Home page',
                    'Services page',
                    'About section',
                    'Contact page',
                    'Local service area',
                    'Phone, email, and WhatsApp buttons',
                    'Mobile-friendly layout',
                    'Basic search-friendly structure',
                    'Dashboard access',
                    'Room for future upgrades',
                ],
            },
            {
                'layout': 'dashboard_band',
                'title': 'Your dashboard is your online business office',
                'paragraphs': [
                    'After your website is prepared, you get a simple dashboard where your business can manage important website details, request help, check useful information, and improve your content over time.',
                    'It is not only a website launch. It becomes a practical place where your online business can grow step by step.',
                ],
                'items': [
                    'Business details',
                    'Contact details',
                    'Services',
                    'Images',
                    'Support',
                    'Content suggestions',
                    'Helpful guides',
                    'Upgrade options',
                    'Promotion options',
                ],
            },
            {
                'layout': 'steps_grid',
                'title': 'How it works',
                'paragraphs': [
                    'The process is practical and built for business owners who want to get online without writing every page from zero.',
                ],
                'steps': [
                    {
                        'title': 'You send the basics',
                        'text': 'Business name, services, location, contact details, and photos if available.',
                    },
                    {
                        'title': 'We prepare the first version',
                        'text': 'We structure the website so customers can understand what you do.',
                    },
                    {
                        'title': 'You review it',
                        'text': 'You check the text, services, contact details, and general direction.',
                    },
                    {
                        'title': 'We publish after approval and payment',
                        'text': 'The website goes live only when the setup is ready.',
                    },
                    {
                        'title': 'You improve over time',
                        'text': 'Add pages, products, content, posts, ads, email, or support later.',
                    },
                ],
            },
            {
                'layout': 'upgrade_band',
                'title': 'Start simple. Upgrade later.',
                'paragraphs': [
                    'You do not need to know everything on day one. Start with the essential website, then add more when your business needs it.',
                    'If your business changes later, you do not need to start again with a completely new website. A Get Online Fast website can grow with your business.',
                ],
                'items': [
                    'Extra pages',
                    'Product catalog',
                    'Online shop',
                    'Business email',
                    'Launch posts',
                    'Facebook and Instagram Ads',
                    'Google Ads',
                    'LinkedIn Ads',
                    'Support',
                ],
            },
            {
                'layout': 'writing_help',
                'title': 'Not sure what to write?',
                'paragraphs': [
                    'You do not need to write every page alone. Send rough notes, services, business details, photos, or examples, and Get Online Fast can help turn them into clearer website text.',
                    'You can also use helpful guides and content suggestions to improve your website after launch.',
                ],
                'actions': [
                    {'label': 'Contact us', 'url_name': 'core:contact'},
                    {'label': 'View helpful guides', 'url_name': 'blog:index'},
                ],
            },
        ],
        'related_links': ['pricing', 'online_shop', 'ads', 'contact'],
        'sidebar_title': 'Useful next steps',
        'cta_block_title': 'Ready to start your website?',
        'cta_block_text': 'Send your business details and Get Online Fast can help you choose the right website setup for your business.',
        'cta_block_primary_label': 'Contact Get Online Fast',
        'cta_block_primary_url_name': 'core:contact',
        'cta_block_secondary_label': 'View pricing',
        'cta_block_secondary_url_name': 'core:pricing',
    },
    'ads': {
        'eyebrow': 'Ads',
        'title': 'Simple local promotion for small businesses',
        'meta_description': 'Learn how Get Online Fast handles launch posts, Facebook content, and local ads for small businesses after a website goes live.',
        'intro': (
            'Your website gives customers a place to understand your business and contact you. Promotion helps more people discover that website through launch posts, social media content, and local advertising options.'
        ),
        'promotion_layout': True,
        'cta_label': 'View promotion options',
        'cta_url': '#promotion-options',
        'cta_secondary_label': 'Contact us',
        'cta_secondary_url_name': 'core:contact',
        'highlights': [
            {'title': 'Website first', 'text': 'Your website is the base where people can read about your business, services, location, and contact options.'},
            {'title': 'Posts after launch', 'text': 'When a customer registers or activates a website, Get Online Fast can help with initial Facebook posts so there is something ready to share and send people to the new website from day one.'},
            {'title': 'Ads when ready', 'text': 'When you are ready to spend on visibility, local ads can help more people see your business in your chosen area.'},
        ],
        'sections': [
            {
                'layout': 'feature',
                'title': 'Your website is the base for promotion',
                'paragraphs': [
                    'Before spending money on ads, your business needs a clear place to send people. A Get Online Fast website gives visitors your services, contact details, location, photos, and next steps.',
                    'Promotion works better when people arrive on a page that explains what you do and makes it easy to call, message, or request more information.',
                ],
                'image_label': 'Promotion base',
            },
            {
                'layout': 'facebook_posts',
                'title': 'Start with Facebook posts',
                'paragraphs': [
                    'When your website is ready, Facebook posts can help announce the launch, explain what your business offers, and point people back to your website.',
                    'These posts are useful because they give you something practical to share with customers, local groups, friends, and business pages. They can help your new website start receiving attention from day one, without needing to begin with a paid ad campaign immediately.',
                ],
                'items': [
                    'Launch announcement',
                    'Service explanation posts',
                    'Contact / website link posts',
                    'Local visibility posts',
                ],
            },
            {
                'layout': 'options_grid',
                'anchor': 'promotion-options',
                'title': 'Promotion options',
                'paragraphs': [
                    'Start with simple launch content or move into paid visibility when the business is ready. The best option depends on your offer, audience, and how quickly you want to test reach.',
                ],
                'options': [
                    {
                        'title': 'Facebook posts',
                        'text': 'Simple content that keeps your business active and sends people back to your website.',
                    },
                    {
                        'title': 'Facebook and Instagram Ads',
                        'text': 'Useful for local visibility, offers, visual services, and reaching people in a chosen area.',
                    },
                    {
                        'title': 'Google Ads',
                        'text': 'Useful when people are already searching for a service and you want to appear for relevant searches.',
                    },
                    {
                        'title': 'LinkedIn Ads',
                        'text': 'Useful for professional, B2B, or business-focused offers when the audience fits.',
                    },
                ],
            },
            {
                'layout': 'cost_band',
                'title': 'How ad costs usually work',
                'paragraphs': [
                    'Ads usually have two parts: a setup or service fee, and the advertising budget spent through the platform.',
                    'The setup fee covers campaign structure, guidance, basic preparation, and launch support. The ad budget is separate and is spent through platforms such as Meta, Google, or LinkedIn during the campaign.',
                    'Results are not guaranteed. Delivery and results can change based on budget, location, targeting radius, audience size, competition, creative quality, your offer, your website, and platform rules.',
                ],
            },
            {
                'layout': 'fit_grid',
                'title': 'Which option fits your business?',
                'paragraphs': [
                    'Different promotion tools fit different businesses. Start with the one that matches how your customers discover your service.',
                ],
                'options': [
                    {
                        'title': 'Choose Facebook posts if:',
                        'text': 'You want to announce your website, stay active, and share updates without starting ads yet.',
                    },
                    {
                        'title': 'Choose Facebook and Instagram Ads if:',
                        'text': 'You want local visibility for a service, offer, event, shop, or visual business.',
                    },
                    {
                        'title': 'Choose Google Ads if:',
                        'text': 'People already search for your type of service and you want to test search visibility.',
                    },
                    {
                        'title': 'Choose LinkedIn Ads if:',
                        'text': 'Your offer is business-focused, professional, or aimed at companies.',
                    },
                ],
            },
            {
                'layout': 'steps_grid',
                'title': 'How it works',
                'paragraphs': [
                    'Promotion works best when the website, launch content, and the first platform choice all support the same business goal.',
                ],
                'steps': [
                    {
                        'title': 'Your website goes live',
                        'text': 'Your website becomes the place where people can learn about your business and contact you.',
                    },
                    {
                        'title': 'We prepare launch content',
                        'text': 'Facebook posts or launch content can help point people to your website.',
                    },
                    {
                        'title': 'You choose a promotion direction',
                        'text': 'Start with posts, Facebook and Instagram Ads, Google Ads, LinkedIn Ads, or a combination.',
                    },
                    {
                        'title': 'Budget and targeting are agreed',
                        'text': 'The campaign area, budget, platform, and goal are chosen before launch.',
                    },
                    {
                        'title': 'You improve over time',
                        'text': 'Promotion can be adjusted based on what you learn from the first results.',
                    },
                ],
            },
            {
                'layout': 'expectations_band',
                'title': 'What promotion can and cannot do',
                'paragraphs': [
                    'Promotion can help more people see your business, visit your website, and contact you. It cannot guarantee customers, sales, or rankings.',
                    'The best results usually come when your offer is clear, your website is easy to understand, your contact options are visible, and your budget matches the audience you want to reach.',
                ],
            },
        ],
        'related_links': ['facebook_posts', 'facebook_instagram_ads', 'google_ads', 'linkedin_ads', 'pricing', 'contact'],
        'sidebar_title': 'Useful next steps',
        'cta_block_title': 'Need help choosing the right promotion option?',
        'cta_block_text': 'Contact Get Online Fast and we can help you choose the right first campaign direction for your business.',
        'cta_block_primary_label': 'Contact Get Online Fast',
        'cta_block_primary_url_name': 'core:contact',
        'cta_block_secondary_label': 'View pricing',
        'cta_block_secondary_url_name': 'core:pricing',
    },
    'online_shop': {
        'eyebrow': 'Online Shop',
        'title': 'Start with a small online shop',
        'meta_description': 'Learn how Get Online Fast can prepare a small online shop, product catalog, and payment-ready store structure for your business.',
        'intro': (
            'Get Online Fast can help small businesses start with a practical online shop, one product page, or product catalog. You can begin with a smaller setup, then expand later as your products, payments, and store needs grow.'
        ),
        'promotion_layout': True,
        'cta_label': 'View pricing',
        'cta_url_name': 'core:pricing',
        'cta_secondary_label': 'Contact us',
        'cta_secondary_url_name': 'core:contact',
        'highlights': [
            {'title': 'Start small', 'text': 'Begin with one product page, a small shop, or a product catalog instead of a large store from day one.'},
            {'title': 'Products first', 'text': 'Products, images, prices, and contact or payment details are the key starting information.'},
            {'title': 'Expand later', 'text': 'You can add more products, payments, categories, delivery details, and features later when the business is ready.'},
        ],
        'sections': [
            {
                'layout': 'shop_options_summary',
                'title': 'Start simple and grow later',
                'paragraphs': [
                    'Not every business needs a full online shop immediately. Some businesses only need one product page, some need a catalog, and others need checkout and online payments.',
                    'Get Online Fast websites can be upgraded step by step, so you can start smaller and grow into a shop when your business is ready.',
                ],
                'options': [
                    {
                        'title': 'One product page',
                        'text': 'A focused page for one product, package, offer, event, course, promotion, or campaign. Useful when you want to explain one offer clearly and send customers to contact you or pay through a simple link.',
                    },
                    {
                        'title': 'Micro shop',
                        'text': 'A small shop for roughly 1 to 4-6 products. Useful for businesses that want to test selling online without starting with a large catalog.',
                    },
                    {
                        'title': 'Product catalog',
                        'text': 'Show products, images, prices, categories, or stock examples without a full checkout. Customers can browse and contact you to order.',
                    },
                    {
                        'title': 'Small online shop',
                        'text': 'Sell a limited number of products with product pages, cart, checkout, and payment options.',
                    },
                    {
                        'title': 'Larger shop',
                        'text': 'For more products, categories, delivery details, suppliers, reseller items, or future growth.',
                    },
                ],
                'note': 'More detailed pages for each shop type will be added later.',
            },
            {
                'layout': 'comparison_table',
                'title': 'Choose the shop setup that fits now',
                'intro': 'You can start with one product, a small generated shop page, a catalog, or a manual online shop with checkout. Start simple and upgrade later when your business is ready.',
                'columns': ['Option', 'Best for', 'Products', 'Payments', 'Setup type', 'Status'],
                'rows': [
                    {
                        'option': 'One product page',
                        'best_for': 'One offer, product, package, course, event, or campaign',
                        'products': '1',
                        'payments': 'Contact, payment link, or checkout later',
                        'setup_type': 'Quick-start page',
                        'status': 'Coming soon',
                    },
                    {
                        'option': 'Micro shop',
                        'best_for': 'A very small product range',
                        'products': 'Up to 4-6',
                        'payments': 'Contact, WhatsApp, payment link, or checkout later',
                        'setup_type': 'Generated shop page',
                        'status': 'Coming soon',
                    },
                    {
                        'option': 'Product catalog',
                        'best_for': 'Showing products without full checkout',
                        'products': 'Small to medium catalog',
                        'payments': 'No checkout needed',
                        'setup_type': 'Quick-start or manual depending on size',
                        'status': 'Coming soon',
                    },
                    {
                        'option': 'Small online shop',
                        'best_for': 'Selling online with checkout',
                        'products': 'Small shop',
                        'payments': 'Checkout and payment provider',
                        'setup_type': 'Manual setup',
                        'status': 'Coming soon',
                    },
                    {
                        'option': 'Larger online shop',
                        'best_for': 'More products, categories, delivery, suppliers, reseller items, or future growth',
                        'products': 'Larger catalog',
                        'payments': 'Checkout and payment provider',
                        'setup_type': 'Manual project',
                        'status': 'Coming soon',
                    },
                ],
                'note': 'A catalog is useful when customers only need to view products and contact you. A full online shop is better when customers need cart, checkout, payment handling, delivery options, and order management.',
            },
            {
                'layout': 'feature',
                'title': 'A simple online shop for small businesses',
                'paragraphs': [
                    'This page is for small businesses that want to sell products online, show a product catalog, or prepare a small shop with product pages, images, prices, and online payment options.',
                    'You do not need to launch a large complex store immediately. A small shop can be a practical first step.',
                ],
                'image_label': 'Online shop example',
            },
            {
                'layout': 'requirements_grid',
                'title': 'What we need to start',
                'paragraphs': [
                    'If you do not have everything ready yet, you can start with the essentials and improve product information later.',
                ],
                'items': [
                    'Product names',
                    'Product images',
                    'Prices',
                    'Short product descriptions',
                    'Product categories if needed',
                    'Delivery or pickup information if relevant',
                    'Business contact details',
                    'Payment preference or checkout needs',
                    'VAT/invoice details if relevant',
                ],
            },
            {
                'layout': 'payment_band',
                'title': 'Payment options can be added when you are ready',
                'paragraphs': [
                    'Some businesses start with contact-based orders or payment links. Others need a checkout with online payment methods. The right setup depends on your products, country, business type, and payment provider availability.',
                ],
                'actions': [
                    {'label': 'Read about payment methods', 'url_name': 'core:payment_methods'},
                ],
            },
            {
                'layout': 'steps_grid',
                'title': 'How it works',
                'paragraphs': [
                    'The shop setup is prepared in practical stages so you can review the structure before launch.',
                ],
                'steps': [
                    {
                        'title': 'You send product details',
                        'text': 'Product names, images, prices, categories, and contact or payment details.',
                    },
                    {
                        'title': 'We prepare the shop structure',
                        'text': 'We prepare the product pages, catalog, or shop layout.',
                    },
                    {
                        'title': 'Products and pages are added',
                        'text': 'Your products, descriptions, images, and key information are added.',
                    },
                    {
                        'title': 'You review the shop',
                        'text': 'You check products, text, prices, contact details, and checkout direction.',
                    },
                    {
                        'title': 'We publish after approval and payment',
                        'text': 'The shop goes live only when the setup is ready.',
                    },
                ],
            },
            {
                'layout': 'upgrade_band',
                'title': 'Start with a website. Upgrade to a shop later.',
                'paragraphs': [
                    'If you already have or start with a Get Online Fast website, you do not need to buy a completely new website when you begin selling products. Your website can grow into a product page, catalog, micro shop, or full online shop later.',
                    'This is important for businesses that are not ready to sell online today but may want to add products in the future.',
                ],
            },
        ],
        'related_links': ['pricing', 'websites', 'payment_methods', 'contact'],
        'sidebar_title': 'Online shop links',
        'cta_block_title': 'Need a small online shop or product catalog?',
        'cta_block_text': 'Contact Get Online Fast and we can help you choose the right starting shop structure for your business.',
        'cta_block_primary_label': 'Contact Get Online Fast',
        'cta_block_primary_url_name': 'core:contact',
        'cta_block_secondary_label': 'View pricing',
        'cta_block_secondary_url_name': 'core:pricing',
    },
    'payment_methods': {
        'eyebrow': 'Payment Methods',
        'title': 'Payment methods for Get Online Fast services',
        'meta_description': 'Learn how payment methods work for Get Online Fast websites, online shops, promotion services, and add-ons.',
        'intro': (
            'Get Online Fast offers practical payment options for websites, online shops, promotion services, and add-ons. Available payment methods can depend on your country, the selected service, and the payment provider settings shown at checkout.'
        ),
        'promotion_layout': True,
        'cta_label': 'Contact us',
        'cta_url_name': 'core:contact',
        'sections': [
            {
                'title': 'Common online payments',
                'paragraphs': [
                    'For many EU customers, online payments may include card payments and selected local payment methods supported by the payment provider. The exact options available are shown during checkout or payment confirmation.',
                ],
            },
            {
                'title': 'Dutch and EU customers',
                'paragraphs': [
                    'Get Online Fast is built for small businesses across Europe. Some payment methods may be available in most EU countries, while local methods can depend on the customer country and the payment provider.',
                ],
            },
            {
                'title': 'Payment links and invoices',
                'paragraphs': [
                    'For some services, payment may be completed through a payment link, invoice, or manual arrangement when needed.',
                ],
            },
            {
                'title': 'VAT and confirmation',
                'paragraphs': [
                    'Prices may include or exclude VAT depending on the page or offer. Payment confirmation and next steps are provided after payment or manual confirmation.',
                ],
            },
            {
                'title': 'Online shop payments',
                'paragraphs': [
                    'Online shop payment methods for customer shops depend on the selected shop setup, country, payment provider, and business requirements. You can start with a catalog or payment links first, then add checkout later when ready.',
                ],
            },
        ],
        'related_links': ['online_shop', 'pricing', 'contact'],
        'sidebar_title': 'Useful next steps',
        'cta_block_title': 'Questions about payment?',
        'cta_block_text': 'Contact Get Online Fast and we can help explain the practical payment direction for your service or shop setup.',
        'cta_block_primary_label': 'Contact us',
        'cta_block_primary_url_name': 'core:contact',
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


def _public_info_page_context(request, key):
    language = (getattr(request, 'LANGUAGE_CODE', 'en') or 'en').split('-', 1)[0]
    page = copy.deepcopy(PUBLIC_INFO_PAGES[key])
    page_sections = page['sections']
    extra_context = {}

    if key == 'catalog_and_ecommerce':
        service_options = _service_options_context(language)
        page['title'] = service_options['section_title']
        page['intro'] = service_options['section_intro']
        page_sections = _catalog_ecommerce_detail_sections(language)
        extra_context['service_options'] = service_options['options']
        extra_context['service_pricing_note'] = service_options['pricing_note']

    for section in page_sections:
        actions = section.get('actions', [])
        if not actions:
            continue
        resolved_actions = []
        for action in actions:
            resolved = dict(action)
            url_name = resolved.pop('url_name', '')
            direct_url = resolved.get('url', '')
            if url_name:
                resolved['url'] = reverse(url_name)
            elif direct_url:
                resolved['url'] = direct_url
            resolved_actions.append(resolved)
        section['actions'] = resolved_actions

    return {
        'page_key': key,
        'site_noindex': page.get('site_noindex', False),
        'force_indexable': page.get('force_indexable', True),
        'promotion_layout': page.get('promotion_layout', False),
        'page_eyebrow': page['eyebrow'],
        'page_title': page['title'],
        'page_subtitle': page.get('subtitle', ''),
        'page_intro': page['intro'],
        'page_meta_description': page['meta_description'],
        'page_sections': page_sections,
        'page_highlights': page.get('highlights', []),
        'page_faq_title': page.get('faq_title', ''),
        'page_faqs': page.get('faqs', []),
        'page_sidebar_title': page.get('sidebar_title', 'More ways to grow'),
        'page_cta_block_title': page.get('cta_block_title', ''),
        'page_cta_block_text': page.get('cta_block_text', ''),
        'page_cta_block_primary_label': page.get('cta_block_primary_label', ''),
        'page_cta_block_primary_url': reverse(page.get('cta_block_primary_url_name', 'core:contact')) if page.get('cta_block_primary_label') else '',
        'page_cta_block_secondary_label': page.get('cta_block_secondary_label', ''),
        'page_cta_block_secondary_url': reverse(page.get('cta_block_secondary_url_name', 'core:contact')) if page.get('cta_block_secondary_label') else '',
        'page_primary_cta_label': page.get('cta_label', ''),
        'page_primary_cta_url': page.get('cta_url', '') or (reverse(page.get('cta_url_name', 'core:contact')) if page.get('cta_label') else ''),
        'page_secondary_cta_label': page.get('cta_secondary_label', ''),
        'page_secondary_cta_url': reverse(page.get('cta_secondary_url_name', 'core:contact')) if page.get('cta_secondary_label') else '',
        'related_links': _public_info_link_items(page.get('related_links', [])),
        'contact_email': 'info@getonlinefast.eu',
        **extra_context,
    }


def _render_public_info_page(request, key):
    return render(
        request,
        'core/public_info_page.html',
        _public_info_page_context(request, key),
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
    public_catalog_price_labels = {
        'en': {
            'starter_catalog': 'Ask for setup guidance',
            'full_ecommerce': 'Manual setup required',
            'reseller_ecommerce': 'Larger custom setup',
        },
        'nl': {
            'starter_catalog': 'Vraag naar opzetadvies',
            'full_ecommerce': 'Handmatige setup nodig',
            'reseller_ecommerce': 'Grotere maatwerk setup',
        },
    }
    for row in rows:
        price_label = row.price_label
        if section_key == 'catalog_ecommerce':
            price_label = public_catalog_price_labels.get(language_code, {}).get(row.option_key, price_label)
        options.append(
            _normalized_service_option(
                {
                    'option_key': row.option_key,
                    'eyebrow': row.eyebrow,
                    'title': row.title,
                    'price_label': price_label,
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
    if language_code == 'fr':
        return [
            {'label': 'Pages produit', 'values': ['check', 'check', 'check']},
            {'label': 'Commande WhatsApp/contact', 'values': ['check', 'Optionnel', 'Flux de demande']},
            {'label': 'Panier et checkout', 'values': ['dash', 'check', 'Possible plus tard']},
            {'label': 'Accompagnement paiement', 'values': ['dash', 'check', 'Sur mesure']},
            {'label': 'Structure livraison/taxes', 'values': ['dash', 'check', 'Sur mesure']},
            {'label': 'Structure catalogue/filtres plus large', 'values': ['Base', 'Boutique standard', 'check']},
            {'label': 'Tableau de bord WooCommerce', 'values': ['dash', 'check', 'Dépend de la configuration']},
        ]
    if language_code == 'pt':
        return [
            {'label': 'Páginas de produto', 'values': ['check', 'check', 'check']},
            {'label': 'Encomenda por WhatsApp/contacto', 'values': ['check', 'Opcional', 'Fluxo de pedido']},
            {'label': 'Carrinho e checkout', 'values': ['dash', 'check', 'Possível mais tarde']},
            {'label': 'Apoio à configuração de pagamentos', 'values': ['dash', 'check', 'Escopo personalizado']},
            {'label': 'Estrutura de envio/impostos', 'values': ['dash', 'check', 'Escopo personalizado']},
            {'label': 'Estrutura maior de catálogo/filtros', 'values': ['Básico', 'Loja standard', 'check']},
            {'label': 'Painel WooCommerce', 'values': ['dash', 'check', 'Depende da configuração']},
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
    if language_code == 'fr':
        return ['SSL', 'Commandes WhatsApp', 'Accompagnement paiement UE', 'WooCommerce', 'Structure de catalogue']
    if language_code == 'pt':
        return ['SSL', 'Encomendas por WhatsApp', 'Apoio à configuração de pagamentos UE', 'WooCommerce', 'Estrutura de catálogo']
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


def _ads_simulator_context(language_code, option_key):
    language_configs = ADS_SIMULATOR_CONFIGS.get(language_code, ADS_SIMULATOR_CONFIGS['en'])
    return language_configs.get(option_key)


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
        'promotion_layout': True,
        'page_option_key': option_key,
        'page_eyebrow': page['eyebrow'],
        'page_title': page['title'],
        'page_subtitle': page.get('subtitle', ''),
        'page_intro': page['intro'],
        'page_price_label': page['price_label'],
        'page_meta_description': page['intro'],
        'page_highlights': page.get('highlights', []),
        'page_sections': page['sections'],
        'page_faq_title': page.get('faq_title', ''),
        'page_faqs': page.get('faqs', []),
        'page_sidebar_title': page.get('sidebar_title', 'More ways to grow'),
        'page_cta_block_title': page.get('cta_block_title', ''),
        'page_cta_block_text': page.get('cta_block_text', ''),
        'page_cta_block_primary_label': page.get('cta_block_primary_label', ''),
        'page_cta_block_primary_url': reverse(page.get('cta_block_primary_url_name', 'core:contact')),
        'page_cta_block_secondary_label': page.get('cta_block_secondary_label', ''),
        'page_cta_block_secondary_url': reverse(page.get('cta_block_secondary_url_name', 'core:contact')),
        'related_links': _public_info_link_items(_promotion_related_links(option_key)),
        'ads_simulator': _ads_simulator_context(language_code, option_key),
        'page_primary_cta_label': page['cta_label'],
        'page_primary_cta_url': reverse('core:contact'),
        'advice_title': advice['advice_title'],
        'advice_text': advice['advice_text'],
        'advice_button_label': advice['advice_button_label'],
        'advice_button_url': reverse('core:contact'),
        'contact_email': 'info@getonlinefast.eu',
    }


def _assistant_language(request):
    request_data = request.POST if request.method == 'POST' else request.GET
    page_path_language = ''
    path_candidates = [
        str(request_data.get('page_path', '') or ''),
        str(request.path or ''),
    ]
    for raw_path in path_candidates:
        normalized_path = str(raw_path or '').strip()
        if not normalized_path:
            continue
        first_segment = normalized_path.lstrip('/').split('/', 1)[0].split('-', 1)[0].lower()
        if first_segment in ASSISTANT_PUBLIC_KNOWLEDGE:
            page_path_language = first_segment
            break

    if page_path_language:
        return page_path_language

    candidate_language = str(request_data.get('lang', '') or '').split('-', 1)[0].lower()
    if candidate_language in ASSISTANT_PUBLIC_KNOWLEDGE:
        return candidate_language

    request_language = str(getattr(request, 'LANGUAGE_CODE', '') or '').split('-', 1)[0].lower()
    if request_language in ASSISTANT_PUBLIC_KNOWLEDGE:
        return request_language

    return 'en'


def _assistant_links(language):
    catalog_url_name = 'core:catalog_and_ecommerce_nl' if language == 'nl' else 'core:catalog_and_ecommerce'
    with override(language):
        return {
            'websites_url': reverse('core:websites'),
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


def _assistant_page_context(language, current_path):
    normalized_path = f"/{str(current_path or '').strip().strip('/')}/"
    context_rules = {
        'en': [
            ('/websites/', 'Websites page'),
            ('/pricing/', 'Pricing page'),
            ('/plans/', 'Pricing page'),
            ('/online-shop/', 'Online shop page'),
            ('/payment-methods/', 'Payment methods page'),
            ('/ads/', 'Ads page'),
            ('/facebook-posts/', 'Facebook launch posts page'),
            ('/facebook-instagram-ads/', 'Facebook and Instagram ads page'),
            ('/google-ads/', 'Google Ads page'),
            ('/linkedin-ads/', 'LinkedIn Ads page'),
            ('/contact/', 'Contact page'),
            ('/support/', 'Support page'),
            ('/start/', 'Starter Page'),
        ],
        'nl': [
            ('/websites/', 'Websites-pagina'),
            ('/pricing/', 'Prijzen-pagina'),
            ('/plans/', 'Prijzen-pagina'),
            ('/online-shop/', 'Online-shop pagina'),
            ('/payment-methods/', 'Betaalmethoden-pagina'),
            ('/ads/', 'Ads-pagina'),
            ('/facebook-posts/', 'Facebook Posts-pagina'),
            ('/facebook-instagram-ads/', 'Facebook en Instagram Ads-pagina'),
            ('/google-ads/', 'Google Ads-pagina'),
            ('/linkedin-ads/', 'LinkedIn Ads-pagina'),
            ('/contact/', 'Contactpagina'),
            ('/support/', 'Supportpagina'),
            ('/start/', 'Starter Page'),
        ],
        'fr': [
            ('/websites/', 'Page sites web'),
            ('/pricing/', 'Page tarifs'),
            ('/plans/', 'Page tarifs'),
            ('/online-shop/', 'Page boutique en ligne'),
            ('/payment-methods/', 'Page moyens de paiement'),
            ('/ads/', 'Page publicités'),
            ('/facebook-posts/', 'Page posts Facebook'),
            ('/facebook-instagram-ads/', 'Page publicités Facebook et Instagram'),
            ('/google-ads/', 'Page Google Ads'),
            ('/linkedin-ads/', 'Page LinkedIn Ads'),
            ('/contact/', 'Page contact'),
            ('/support/', 'Page support'),
            ('/start/', 'Starter Page'),
        ],
        'pt': [
            ('/websites/', 'Página websites'),
            ('/pricing/', 'Página preços'),
            ('/plans/', 'Página preços'),
            ('/online-shop/', 'Página loja online'),
            ('/payment-methods/', 'Página métodos de pagamento'),
            ('/ads/', 'Página anúncios'),
            ('/facebook-posts/', 'Página posts de Facebook'),
            ('/facebook-instagram-ads/', 'Página anúncios Facebook e Instagram'),
            ('/google-ads/', 'Página Google Ads'),
            ('/linkedin-ads/', 'Página LinkedIn Ads'),
            ('/contact/', 'Página contacto'),
            ('/support/', 'Página suporte'),
            ('/start/', 'Starter Page'),
        ],
    }
    for slug, label in context_rules.get(language, context_rules['en']):
        if normalized_path.endswith(slug):
            return label
    return ''


def _assistant_normalize_question(question):
    question_text = (question or '').strip().lower()
    return ' '.join(question_text.replace('?', ' ').replace('!', ' ').replace('.', ' ').replace(',', ' ').split())


def _assistant_token_similarity(left_token, right_token):
    left = str(left_token or '').strip()
    right = str(right_token or '').strip()
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    return SequenceMatcher(None, left, right).ratio()


def _assistant_keyword_matches_question(normalized_question, normalized_tokens, normalized_keyword):
    if not normalized_keyword:
        return False

    keyword_tokens = normalized_keyword.split()
    if not keyword_tokens:
        return False

    if len(keyword_tokens) == 1:
        keyword_token = keyword_tokens[0]
        if keyword_token in normalized_tokens:
            return True
        if len(keyword_token) < 4:
            return False
        return any(
            len(candidate) >= 4 and _assistant_token_similarity(keyword_token, candidate) >= 0.86
            for candidate in normalized_tokens
        )

    question_tokens = normalized_question.split()
    if len(question_tokens) < len(keyword_tokens):
        return False

    for start_index in range(len(question_tokens) - len(keyword_tokens) + 1):
        window = question_tokens[start_index:start_index + len(keyword_tokens)]
        if all(
            keyword_token == question_token
            or (
                len(keyword_token) >= 4
                and len(question_token) >= 4
                and _assistant_token_similarity(keyword_token, question_token) >= 0.84
            )
            for keyword_token, question_token in zip(keyword_tokens, window)
        ):
            return True
    return False


def _assistant_detect_intent(question, language):
    normalized_question = _assistant_normalize_question(question)
    if not normalized_question:
        return 'fallback'
    normalized_tokens = set(normalized_question.split())

    for intent, language_keywords in ASSISTANT_INTENT_KEYWORDS.items():
        keywords = list(language_keywords.get(language, [])) + list(language_keywords.get('en', [])) + list(language_keywords.get('nl', []))
        for keyword in keywords:
            if not keyword:
                continue
            normalized_keyword = _assistant_normalize_question(keyword)
            if not normalized_keyword:
                continue
            if _assistant_keyword_matches_question(normalized_question, normalized_tokens, normalized_keyword):
                return intent
    return 'fallback'


def _assistant_link_items(intent, language, links):
    labels = {
        'en': {
            'activation': 'Activation page',
            'websites': 'Websites',
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
            'websites': 'Websites',
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
            {'label': 'Pricing' if language == 'en' else 'Prijzen', 'url': links['plans_url']},
            {'label': copy['contact'], 'url': links['contact_url']},
        ]
    if intent == 'website_options':
        with override(language):
            online_shop_url = reverse('core:online_shop')
        return [
            {'label': copy['websites'], 'url': links['websites_url']},
            {'label': 'Pricing' if language == 'en' else 'Prijzen', 'url': links['plans_url']},
            {'label': copy['catalog_ecommerce'], 'url': online_shop_url},
        ]
    if intent == 'ecommerce':
        with override(language):
            online_shop_url = reverse('core:online_shop')
        return [
            {'label': copy['catalog_ecommerce'], 'url': online_shop_url},
            {'label': copy['contact'], 'url': links['contact_url']},
        ]
    if intent in {'promotion', 'promotion_guarantee'}:
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
    request_data = request.POST if request.method == 'POST' else request.GET
    question = request_data.get('message', '') or request_data.get('q', '')
    link_urls = _assistant_links(language)
    current_path = request_data.get('page_path', '') or request_data.get('path', '') or ''
    context = {
        'current_path': current_path,
        'current_page': _assistant_page_context(language, current_path),
    }
    assistant_response = build_public_assistant_response(
        request=request,
        question=question,
        language=language,
        fallback_response=_assistant_answer(question, language),
        links=link_urls,
        context=context,
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
    if current_path:
        payload['current_path'] = current_path
        payload['current_page'] = context['current_page']
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
            'page_meta_description': _(
                'Get Online Fast helps small businesses launch practical WordPress websites with clear structure, support, and room to grow.'
            ),
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
            'page_title': _('Pricing'),
            'page_meta_description': _(
                'Compare pricing for websites, online shops, ads, and practical add-ons from Get Online Fast.'
            ),
            'pricing_sections': pricing_overview_sections(),
            'pricing_faqs': pricing_overview_faqs(),
            'website_plans': website_plans_overview_cards(),
            'online_shop_plans': online_shop_pricing_cards(),
            'marketing_services': marketing_pricing_cards(),
            'addons': addon_pricing_cards(),
        },
    )


def faq(request):
    return render(
        request,
        'core/faq.html',
        {
            'force_indexable': True,
            'site_noindex': False,
            'page_meta_description': 'Read practical answers about website delivery time, promotion, online shops, payments, support, and getting online with Get Online Fast.',
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


def websites(request):
    return render(
        request,
        'core/websites.html',
        _public_info_page_context(request, 'websites'),
    )


def ads(request):
    return _render_public_info_page(request, 'ads')


def online_shop(request):
    return _render_public_info_page(request, 'online_shop')


def payment_methods(request):
    return _render_public_info_page(request, 'payment_methods')


def catalog_and_ecommerce(request):
    return redirect('core:online_shop')


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


def online_shop_pricing_cards():
    return [
        {
            'title': _('Small Online Shop'),
            'price': _('Coming soon'),
            'text': _('A simple product catalog or small shop structure for businesses that want to start selling online without a large store build.'),
            'items': [
                _('Product pages'),
                _('Images and prices'),
                _('Simple ordering or payment direction'),
            ],
            'cta': _('Ask for setup price'),
            'url_name': 'core:online_shop',
        },
        {
            'title': _('Online Shop Pro'),
            'price': _('Coming soon'),
            'text': _('A stronger online shop setup with checkout, payments, and a larger store structure for businesses that need more.'),
            'items': [
                _('Checkout-ready shop structure'),
                _('Product categories'),
                _('Payment and store setup guidance'),
            ],
            'cta': _('Discuss online shop setup'),
            'url_name': 'core:online_shop',
        },
    ]


def marketing_pricing_cards():
    return [
        {
            'title': _('Facebook & Instagram Ads'),
            'price': _('From €49 + ad budget'),
            'text': _('Local ads for services, offers, and launch campaigns on Facebook and Instagram.'),
            'items': [
                _('Setup fee'),
                _('Ad budget chosen by you'),
                _('Local targeting options'),
            ],
            'cta': _('View Facebook & Instagram Ads'),
            'url_name': 'core:facebook_instagram_ads',
        },
        {
            'title': _('Google Ads'),
            'price': _('From €69 + ad budget'),
            'text': _('Search ads for businesses that want to appear when people are already looking for a service.'),
            'items': [
                _('Setup fee'),
                _('Ad budget chosen by you'),
                _('Keyword and local targeting direction'),
            ],
            'cta': _('View Google Ads'),
            'url_name': 'core:google_ads',
        },
        {
            'title': _('LinkedIn Ads'),
            'price': _('From €89 + ad budget'),
            'text': _('Professional and B2B ads for services that need business-focused targeting.'),
            'items': [
                _('Setup fee'),
                _('Ad budget chosen by you'),
                _('Business audience targeting'),
            ],
            'cta': _('View LinkedIn Ads'),
            'url_name': 'core:linkedin_ads',
        },
        {
            'title': _('Facebook Launch Posts'),
            'price': _('Free with some new website setups'),
            'text': _('Prepared launch posts that help a new website and Facebook page look active from day one.'),
            'items': [
                _('Launch posts and stories'),
                _('Facebook page support'),
                _('Clear links back to your website'),
            ],
            'cta': _('View Facebook Launch Posts'),
            'url_name': 'core:facebook_posts',
        },
    ]


def addon_pricing_cards():
    return [
        {
            'title': _('Business Email Setup'),
            'price': _('Ask for setup price'),
            'text': _('Set up a business email address that matches your domain and website.'),
            'items': [
                _('Mailbox setup'),
                _('Domain-based business email'),
            ],
            'cta': _('Ask about business email'),
            'url_name': 'core:contact',
        },
        {
            'title': _('Extra Page'),
            'price': _('Ask for setup price'),
            'text': _('Add another service page, area page, or supporting information page later.'),
            'items': [
                _('Extra content page'),
                _('Fits future growth'),
            ],
            'cta': _('Ask about extra pages'),
            'url_name': 'core:contact',
        },
        {
            'title': _('Logo Starter Pack'),
            'price': _('Ask for setup price'),
            'text': _('A simple starter logo direction for businesses that need a cleaner first visual identity.'),
            'items': [
                _('Starter logo direction'),
                _('Basic branding support'),
            ],
            'cta': _('Ask about logo help'),
            'url_name': 'core:contact',
        },
        {
            'title': _('Website Support'),
            'price': _('Ask for setup price'),
            'text': _('Get practical help with small changes, support questions, or follow-up website work.'),
            'items': [
                _('Practical support'),
                _('Small follow-up changes'),
            ],
            'cta': _('Contact support'),
            'url_name': 'core:contact',
        },
    ]


def pricing_overview_sections():
    return [
        {
            'title': _('Quick-start tools'),
            'intro': _(
                'Simple starter options for businesses that want to get online fast, test an idea, or show a small offer without starting a large project.'
            ),
            'note': _(
                'Quick-start pages are prepared from your details. They are useful when you want to start small and improve later.'
            ),
            'rows': [
                {
                    'title': _('Starter Page'),
                    'good_for': _('A simple generated page to get online fast. Own domain possible.'),
                    'price': _('€20/month'),
                    'status': _('Available'),
                    'actions': [
                        {'label': _('Buy now'), 'href': reverse('ai_starter:start'), 'variant': 'primary'},
                    ],
                },
                {
                    'title': _('Generated Catalog up to 6 products'),
                    'good_for': _('Show products, prices, images, and categories without full checkout. Own domain possible.'),
                    'price': _('€20/month'),
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
                {
                    'title': _('Generated Shop Page up to 6 products'),
                    'good_for': _('A small product/shop page for testing sales without a full manual shop setup. Own domain possible.'),
                    'price': _('€20/month'),
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
            ],
        },
        {
            'title': _('Websites'),
            'intro': _(
                'For businesses that need a clear public website with services, location, contact details, and room to grow.'
            ),
            'rows': [
                {
                    'title': _('One-Time Website'),
                    'good_for': _('A full small business website prepared around your services, location, contact details, and future upgrades.'),
                    'price': _('€325 + VAT'),
                    'status': _('Available'),
                    'actions': [
                        {'label': _('Buy now'), 'href': reverse('core:website_package_payment'), 'variant': 'primary'},
                    ],
                },
                {
                    'title': _('Monthly Website'),
                    'good_for': _('A website with hosting, support, and ongoing website care included.'),
                    'price': _('From €49.90/month'),
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
            ],
        },
        {
            'title': _('Online shops and catalogs'),
            'intro': _(
                'Start with a product page or catalog first, then move to checkout and payment options when your business is ready.'
            ),
            'lead': _(
                'If payments are needed, the setup is manual. If you only need to show products first, you can start with a generated catalog or generated shop page.'
            ),
            'rows': [
                {
                    'title': _('Product Catalog Setup'),
                    'good_for': _('A more complete product catalog with categories, images, product details, and room to grow.'),
                    'price': _('Coming soon'),
                    'coming_soon': True,
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
                {
                    'title': _('Online Shop with Payments'),
                    'good_for': _('A manual shop setup with checkout and payment options.'),
                    'price': _('Coming soon'),
                    'coming_soon': True,
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
                {
                    'title': _('Larger Shop'),
                    'good_for': _('More products, categories, delivery details, suppliers, reseller items, or future growth.'),
                    'price': _('Coming soon'),
                    'coming_soon': True,
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
            ],
        },
        {
            'title': _('Promotion'),
            'intro': _(
                'Promotion helps more people discover your website after launch. Your website is the base; posts and ads can send people back to it.'
            ),
            'note': _('Ad budget is separate and is spent through the ad platform.'),
            'rows': [
                {
                    'title': _('Launch Facebook Posts'),
                    'good_for': _('Announce your new website and send people to it after activation.'),
                    'price': _('Included with website activation'),
                    'included': True,
                    'status': _('Included'),
                    'actions': [
                        {'label': _('Read more'), 'href': reverse('core:facebook_posts'), 'variant': 'secondary'},
                    ],
                },
                {
                    'title': _('Facebook Posts'),
                    'good_for': _('Keep your business active with simple posts that point people back to your website.'),
                    'price': _('Coming soon'),
                    'coming_soon': True,
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
                {
                    'title': _('Facebook & Instagram Ads Setup'),
                    'good_for': _('Local visibility campaigns for services, offers, shops, and visual businesses. Ad budget is separate.'),
                    'price': _('€49 setup'),
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
                {
                    'title': _('Google Ads Setup'),
                    'good_for': _('Campaign setup for people already searching for your service. Ad budget is separate.'),
                    'price': _('€69 setup'),
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
                {
                    'title': _('LinkedIn Ads Setup'),
                    'good_for': _('Business-focused ads for professional or B2B offers. Ad budget is separate.'),
                    'price': _('€89 setup'),
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
            ],
        },
        {
            'title': _('Add-ons and business tools'),
            'intro': _(
                'Extra tools can be added when your business needs them.'
            ),
            'rows': [
                {
                    'title': _('Business Email Setup'),
                    'good_for': _('Professional email for your domain.'),
                    'price': _('Coming soon'),
                    'coming_soon': True,
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Available soon'), 'disabled': True, 'variant': 'primary'},
                    ],
                },
                {
                    'title': _('Payment Methods / Checkout Setup'),
                    'good_for': _('Help choosing the right payment setup for your website or shop.'),
                    'price': _('Coming soon'),
                    'coming_soon': True,
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Read more'), 'href': reverse('core:payment_methods'), 'variant': 'secondary'},
                    ],
                },
                {
                    'title': _('Extra Page'),
                    'good_for': _('Add an extra service, landing, product, or information page.'),
                    'price': _('Coming soon'),
                    'coming_soon': True,
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Contact us'), 'href': reverse('core:contact'), 'variant': 'secondary'},
                    ],
                },
                {
                    'title': _('Website Support'),
                    'good_for': _('Help with updates, small fixes, and improvements.'),
                    'price': _('Coming soon'),
                    'coming_soon': True,
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Contact us'), 'href': reverse('core:contact'), 'variant': 'secondary'},
                    ],
                },
                {
                    'title': _('Content Help'),
                    'good_for': _('Help turning rough notes into clearer website text.'),
                    'price': _('Coming soon'),
                    'coming_soon': True,
                    'status': _('Coming soon'),
                    'actions': [
                        {'label': _('Contact us'), 'href': reverse('core:contact'), 'variant': 'secondary'},
                    ],
                },
            ],
        },
    ]


def pricing_overview_faqs():
    return [
        {
            'question': _('Can I start small and upgrade later?'),
            'answer': _('Yes. You can start with a simple page, website, catalog, or generated shop page and add more later.'),
        },
        {
            'question': _('Do I need an online shop immediately?'),
            'answer': _('No. Many businesses start with a website or catalog first, then add checkout and payments later.'),
        },
        {
            'question': _('Are ad budgets included?'),
            'answer': _('No. Ads setup and ad budget are separate. The setup fee covers preparation and launch support. The ad budget is spent through the advertising platform.'),
        },
        {
            'question': _('Why are some prices marked Coming soon?'),
            'answer': _('Some services need more setup, payment provider details, or manual handling before a fixed public price is shown.'),
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
