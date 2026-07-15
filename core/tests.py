from unittest.mock import patch

from django.contrib.admin.sites import site as admin_site
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ServiceOption
from .services_public_assistant import PUBLIC_ASSISTANT_SYSTEM_PROMPT, _prompt_context


@override_settings(SITE_NOINDEX=False)
class PublicPagesTests(TestCase):
    def test_legal_pages_return_200(self):
        route_names = [
            'core:terms',
            'core:privacy_policy',
            'core:cookie_policy',
            'core:payment_and_cancellation',
            'core:domain_hosting_and_dashboard',
            'core:addons_and_upgrades',
            'core:preview_licence',
        ]
        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_public_legal_page_is_indexable_when_site_noindex_disabled(self):
        response = self.client.get(reverse('core:terms'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'noindex, nofollow')

    def test_footer_contains_public_legal_links(self):
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, reverse('core:contact'))
        self.assertContains(response, reverse('core:privacy_policy'))
        self.assertContains(response, reverse('core:terms'))
        self.assertContains(response, reverse('core:cookie_policy'))

    def test_header_contains_mobile_nav_toggle_and_public_links(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-mobile-nav-toggle')
        self.assertContains(response, reverse('core:home'))
        self.assertContains(response, reverse('core:websites'))
        self.assertContains(response, reverse('core:ads'))
        self.assertContains(response, reverse('core:online_shop'))
        self.assertContains(response, reverse('core:pricing'))
        self.assertContains(response, reverse('core:faq'))
        self.assertContains(response, reverse('core:contact'))

    def test_mobile_nav_toggle_is_present_on_localized_start_page(self):
        response = self.client.get('/nl/start/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-mobile-nav-toggle')
        self.assertContains(response, '/nl/contact/')

    def test_homepage_links_to_public_start_flow(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('ai_starter:start'))

    def test_homepage_uses_public_start_flow_instead_of_old_start_anchor(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '#start')
        self.assertContains(response, reverse('ai_starter:start'))

    def test_general_public_pages_do_not_mention_hmd(self):
        route_names = [
            'core:home',
            'core:how_it_works',
            'core:plans',
            'core:faq',
            'core:contact',
            'core:support',
            'core:terms',
            'core:privacy_policy',
            'core:cookie_policy',
            'core:payment_and_cancellation',
        ]
        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'HMD')
                self.assertNotContains(response, 'hmd-klusbedrijf')

    def test_public_pages_do_not_contain_localhost_links(self):
        route_names = [
            'core:home',
            'core:contact',
            'core:hmd_activation',
        ]
        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'localhost')
                self.assertNotContains(response, '127.0.0.1')

    def test_public_start_route_is_accessible(self):
        response = self.client.get(reverse('ai_starter:start'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Start je website')
        self.assertContains(response, 'Start je bedrijfswebsite | Get Online Fast', html=False)
        self.assertContains(
            response,
            'Start je bedrijfswebsite in enkele minuten. Voeg je bedrijfstype, diensten en stijl toe en ga daarna verder met Get Online Fast.',
        )
        self.assertNotContains(response, 'noindex, nofollow')

    @patch('ai_starter.views.ensure_default_templates')
    def test_public_start_route_does_not_attempt_template_db_setup_on_get(self, mocked_ensure_default_templates):
        response = self.client.get(reverse('ai_starter:start'))

        self.assertEqual(response.status_code, 200)
        mocked_ensure_default_templates.assert_not_called()
        self.assertContains(response, 'Start je website')

    @override_settings(SITE_NOINDEX=True)
    def test_key_public_pages_remain_indexable_when_global_noindex_flag_is_enabled(self):
        route_names = [
            'core:home',
            'ai_starter:start',
            'core:plans',
            'core:contact',
            'core:privacy_policy',
            'core:terms',
            'core:faq',
            'core:support',
        ]
        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'noindex, nofollow')

    @override_settings(SITE_NOINDEX=True)
    def test_robots_and_sitemap_expose_public_start_flow(self):
        robots_response = self.client.get(reverse('robots_txt'))
        sitemap_response = self.client.get(reverse('sitemap_xml'))

        self.assertEqual(robots_response.status_code, 200)
        self.assertEqual(sitemap_response.status_code, 200)
        self.assertContains(robots_response, 'Sitemap:')
        self.assertNotContains(robots_response, '/en/start/')
        self.assertContains(sitemap_response, reverse('ai_starter:start'))
        self.assertContains(sitemap_response, reverse('core:home'))
        self.assertContains(sitemap_response, reverse('core:plans'))
        self.assertContains(sitemap_response, reverse('core:contact'))

    def test_public_examples_routes_are_not_accessible(self):
        for route_name in ['core:examples', 'core:templates']:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 404)

    def test_public_pages_do_not_link_to_examples(self):
        route_names = ['core:home', 'core:how_it_works', 'core:plans', 'core:faq', 'core:contact']
        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, reverse('core:examples'))
                self.assertNotContains(response, reverse('core:templates'))

    def test_catalog_and_ecommerce_info_pages_are_public(self):
        response = self.client.get(reverse('core:catalog_and_ecommerce'))
        self.assertRedirects(response, reverse('core:online_shop'))

        dutch_response = self.client.get('/nl/catalogus-en-webshop/')
        self.assertRedirects(dutch_response, reverse('core:online_shop'))

    def test_promotion_pages_are_public(self):
        promotion_routes = [
            ('core:facebook_posts', 'Facebook Posts'),
            ('core:facebook_instagram_ads', 'Facebook & Instagram Ads'),
            ('core:google_ads', 'Google Ads'),
            ('core:linkedin_ads', 'LinkedIn Ads'),
        ]
        for route_name, title in promotion_routes:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, title)
                self.assertContains(response, reverse('core:contact'))
                self.assertContains(response, reverse('core:plans'))
                self.assertContains(response, 'Ask for advice')

    def test_faq_does_not_use_coming_soon_ecommerce_wording(self):
        response = self.client.get(reverse('core:faq'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'coming soon')
        self.assertNotContains(response, 'Coming soon')
        self.assertNotContains(response, 'Coming Soon')

    def test_homepage_has_catalog_and_ecommerce_section(self):
        response = self.client.get('/en/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catalogs and online shops')
        self.assertContains(response, 'Starter Catalog / WhatsApp Orders')
        self.assertContains(response, 'Ask for setup guidance')
        self.assertContains(response, 'Manual setup required')
        self.assertContains(response, 'Larger custom setup')
        self.assertNotContains(response, 'From ?149 + VAT')
        self.assertNotContains(response, 'From ?595 + VAT')
        self.assertNotContains(response, 'From ?1,250 + VAT')

        dutch_response = self.client.get('/nl/')
        self.assertEqual(dutch_response.status_code, 200)
        self.assertContains(dutch_response, 'Vraag naar opzetadvies')

    def test_homepage_has_promotion_section_below_ecommerce(self):
        response = self.client.get('/en/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Promote your website', content)
        self.assertIn('View Facebook Posts', content)
        self.assertIn('View Meta Ads', content)
        self.assertIn(reverse('core:facebook_posts'), content)
        self.assertIn(reverse('core:facebook_instagram_ads'), content)
        self.assertIn(reverse('core:google_ads'), content)
        self.assertIn(reverse('core:linkedin_ads'), content)
        self.assertLess(content.index('id=\"catalog-ecommerce\"'), content.index('id=\"promotion\"'))
        self.assertIn('Ad budget is not included.', content)

    def test_plans_page_uses_short_catalog_teaser_only(self):
        response = self.client.get(reverse('core:plans'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Need a catalog or online shop?')
        self.assertNotContains(response, 'View catalog and eCommerce options')
        self.assertNotContains(response, 'Starter Catalog / WhatsApp Orders')
        self.assertNotContains(response, 'WooCommerce dashboard')

    def test_public_pages_do_not_contain_catalog_placeholder_copy(self):
        for route_name in ['core:home', 'core:plans', 'core:online_shop']:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'Free Hero Pricing Page')
                self.assertNotContains(response, 'Available by request')

    def test_catalog_and_ecommerce_fallback_works_without_admin_rows(self):
        ServiceOption.objects.all().delete()

        homepage_response = self.client.get(reverse('core:home'))
        self.assertEqual(homepage_response.status_code, 200)
        self.assertContains(homepage_response, 'Ask for setup guidance')
        self.assertContains(homepage_response, 'Prices are starting prices and exclude VAT.')

        detail_response = self.client.get(reverse('core:catalog_and_ecommerce'))
        self.assertRedirects(detail_response, reverse('core:online_shop'))

    def test_promotion_fallback_works_without_admin_rows(self):
        ServiceOption.objects.all().delete()

        homepage_response = self.client.get(reverse('core:home'))
        self.assertEqual(homepage_response.status_code, 200)
        self.assertContains(homepage_response, 'Promote your website')
        self.assertContains(homepage_response, 'EUR 79 / month')
        self.assertContains(homepage_response, 'From EUR 70')

        promotion_response = self.client.get(reverse('core:facebook_posts'))
        self.assertEqual(promotion_response.status_code, 200)
        self.assertContains(promotion_response, 'EUR 79 / month')

    def test_service_option_model_is_registered_in_admin(self):
        self.assertIn(ServiceOption, admin_site._registry)

    def test_service_option_seed_rows_exist(self):
        self.assertEqual(ServiceOption.objects.filter(section_key='catalog_ecommerce', language='en').count(), 3)
        self.assertEqual(ServiceOption.objects.filter(section_key='catalog_ecommerce', language='nl').count(), 3)
        self.assertEqual(ServiceOption.objects.filter(section_key='promotion', language='en').count(), 4)
        self.assertEqual(ServiceOption.objects.filter(section_key='promotion', language='nl').count(), 4)

    def test_footer_contains_promotion_links(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('core:facebook_posts'))
        self.assertContains(response, reverse('core:facebook_instagram_ads'))
        self.assertContains(response, reverse('core:google_ads'))
        self.assertContains(response, reverse('core:linkedin_ads'))


@override_settings(SITE_NOINDEX=False)
class PublicLanguageEntryRedirectTests(TestCase):
    def test_root_redirects_to_dutch_for_dutch_browser_language(self):
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='nl-NL,nl;q=0.9,en;q=0.8')
        self.assertRedirects(response, '/nl/')

    def test_root_redirects_to_portuguese_for_portuguese_browser_language(self):
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='pt-PT,pt;q=0.9,en;q=0.8')
        self.assertRedirects(response, '/pt/')

    def test_root_redirects_to_english_for_unsupported_browser_language(self):
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='de-DE,de;q=0.9')
        self.assertRedirects(response, '/en/')

    def test_language_cookie_takes_priority_over_browser_language(self):
        self.client.cookies['django_language'] = 'fr'
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='nl-NL,nl;q=0.9,en;q=0.8')
        self.assertRedirects(response, '/fr/')

    def test_prefixed_url_does_not_redirect_away(self):
        response = self.client.get('/fr/')
        self.assertEqual(response.status_code, 200)

    def test_query_strings_are_preserved(self):
        response = self.client.get('/pricing/?source=google&utm=test', HTTP_ACCEPT_LANGUAGE='nl-NL,nl;q=0.9,en;q=0.8')
        self.assertRedirects(response, '/nl/pricing/?source=google&utm=test')

    def test_safe_public_entry_routes_redirect_to_preferred_language(self):
        cases = [
            ('/start/', '/pt/start/'),
            ('/contact/', '/pt/contact/'),
            ('/help/', '/pt/help/'),
            ('/blog/', '/pt/blog/'),
        ]
        for source, destination in cases:
            with self.subTest(source=source):
                response = self.client.get(source, HTTP_ACCEPT_LANGUAGE='pt-BR,pt;q=0.9,en;q=0.8')
                self.assertRedirects(response, destination)

    def test_admin_static_media_and_staff_routes_do_not_redirect_to_language_prefix(self):
        cases = [
            '/admin/',
            '/static/core/css/style.css',
            '/media/example.jpg',
            '/staff/',
        ]
        for path in cases:
            with self.subTest(path=path):
                response = self.client.get(path, HTTP_ACCEPT_LANGUAGE='nl-NL,nl;q=0.9,en;q=0.8')
                if response.has_header('Location'):
                    self.assertNotIn('/nl/', response['Location'])
                    self.assertNotIn('/fr/', response['Location'])
                    self.assertNotIn('/pt/', response['Location'])


@override_settings(SITE_NOINDEX=True)
class SoftLaunchIndexingTests(TestCase):
    def test_homepage_is_noindex_when_soft_launch_mode_is_enabled(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'noindex, nofollow')

    def test_sitemap_is_empty_when_soft_launch_mode_is_enabled(self):
        response = self.client.get(reverse('sitemap_xml'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('core:home'))


@override_settings(SITE_NOINDEX=False, GOF_AI_ENABLED=False, OPENAI_API_KEY='')
class AssistantTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_assistant_greeting_returns_friendly_greeting(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'hi'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'disabled')
        self.assertEqual(payload['fallback_reason'], 'gof_ai_disabled')
        self.assertFalse(payload['ai_enabled'])
        self.assertFalse(payload['has_openai_key'])
        self.assertEqual(payload['language'], 'en')
        self.assertEqual(payload['intent'], 'greeting')
        self.assertIn("I'm the Get Online Fast helper", payload['answer'])

    def test_assistant_endpoint_supports_dutch_greeting(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'hoi', 'lang': 'nl'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['language'], 'nl')
        self.assertEqual(payload['intent'], 'greeting')
        self.assertIn('Ik ben de Get Online Fast hulp', payload['answer'])

    def test_assistant_payment_intent_matches_english(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'How can I pay?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'payment')
        self.assertIn('Stripe', payload['answer'])
        self.assertIn(reverse('core:payment_and_cancellation'), payload['answer'])

    def test_assistant_payment_intent_matches_dutch(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'betaling', 'lang': 'nl'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['language'], 'nl')
        self.assertEqual(payload['intent'], 'payment')
        self.assertIn('Stripe', payload['answer'])
        self.assertIn('betaallink of activatiepagina van Get Online Fast', payload['answer'])
        self.assertIn('Betaling en annulering', payload['answer'])
        self.assertNotIn('HMD', payload['answer'])
        self.assertNotIn('hmd-klusbedrijf', payload['answer'])

    def test_assistant_activation_intent_matches_english(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'How does activation work?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'activation')
        self.assertIn('checks the activation and handoff manually', payload['answer'])
        self.assertNotIn('HMD', payload['answer'])
        self.assertNotIn('hmd-klusbedrijf', payload['answer'])

    def test_assistant_activation_intent_matches_dutch(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'website activeren', 'lang': 'nl'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'activation')
        self.assertIn('juiste activatiepagina of betaallink', payload['answer'])
        self.assertNotIn('HMD', payload['answer'])
        self.assertNotIn('hmd-klusbedrijf', payload['answer'])

    def test_assistant_unknown_question_uses_better_fallback(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'banana'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'fallback')
        self.assertIn('Which plan fits my business?', payload['answer'])

    def test_assistant_widget_uses_general_public_copy(self):
        response = self.client.get('/en/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Need help?')
        self.assertContains(response, 'Quick help for websites, shops, ads, and support.')
        self.assertContains(response, 'e.g. I need a website')
        self.assertContains(response, reverse('core:websites'))
        self.assertContains(response, reverse('core:ads'))
        self.assertContains(response, reverse('core:pricing'))
        self.assertContains(response, reverse('core:assistant_help'))
        self.assertContains(response, 'data-assistant-version="v2"')
        self.assertContains(response, 'data-assistant-site-key="getonlinefast-public"')
        self.assertContains(response, 'data-assistant-reset')
        self.assertNotContains(response, 'Which plan fits my business?')
        self.assertNotContains(response, 'How does the dashboard work?')

    def test_assistant_widget_shows_dutch_labels_on_dutch_page(self):
        response = self.client.get('/nl/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hulp nodig?')
        self.assertContains(response, 'Snelle hulp bij websites, webshops, advertenties en support.')
        self.assertContains(response, 'Bijv. ik heb een website nodig')
        self.assertContains(response, 'Versturen')
        self.assertContains(response, '/nl/websites/')
        self.assertContains(response, '/nl/pricing/')
        self.assertNotContains(response, 'Welk pakket past bij mijn bedrijf?')

    def test_assistant_pricing_question_uses_plans_answer(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'What are your prices?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'plans')
        self.assertIn(reverse('core:plans'), payload['answer'])
        self.assertIn(reverse('core:plans'), payload['suggested_links'][0]['url'])

    def test_assistant_preview_question_does_not_return_start_link(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Can I create a preview right now?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'preview')
        self.assertIn('Preview creation is not publicly available right now.', payload['answer'])
        self.assertNotIn('/start/', payload['answer'])
        for link in payload['suggested_links']:
            self.assertNotIn('/start/', link['url'])

    def test_assistant_online_shop_answer_is_general(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Can you help with online shops?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'ecommerce')
        self.assertIn('product catalogs', payload['answer'])
        self.assertIn('online shop page', payload['answer'])
        self.assertIn(reverse('core:online_shop'), payload['suggested_links'][0]['url'])
        self.assertNotIn('coming soon', payload['answer'].lower())
        self.assertNotIn('HMD', payload['answer'])
        for link in payload['suggested_links']:
            self.assertNotIn('/examples/', link['url'])

    def test_assistant_online_shop_answer_links_to_dutch_online_shop_page(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Kunnen jullie helpen met webshops?', 'lang': 'nl'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'ecommerce')
        self.assertIn('online-shop pagina', payload['answer'])
        self.assertNotIn('HMD', payload['answer'])
        self.assertIn('/nl/online-shop/', payload['suggested_links'][0]['url'])

    def test_assistant_promotion_answer_is_general(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Can you help with Google Ads?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'promotion')
        self.assertIn('Facebook Posts', payload['answer'])
        self.assertIn(reverse('core:facebook_posts'), payload['suggested_links'][0]['url'])

    def test_assistant_responses_do_not_expose_localhost_links(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'support', 'lang': 'nl'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn('localhost', payload['answer'])
        self.assertNotIn('127.0.0.1', payload['answer'])
        self.assertNotIn('hmd-klusbedrijf', payload['answer'])
        for link in payload['suggested_links']:
            self.assertNotIn('localhost', link['url'])
            self.assertNotIn('127.0.0.1', link['url'])
            self.assertNotIn('hmd-klusbedrijf', link['url'])

    @override_settings(GOF_PUBLIC_AI_ASSISTANT_ENABLED=True)
    def test_public_ai_disabled_returns_disabled_mode(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'How can I pay?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'disabled')
        self.assertEqual(payload['fallback_reason'], 'gof_ai_disabled')
        self.assertEqual(payload['intent'], 'payment')
        self.assertIn('Stripe', payload['answer'])

    @override_settings(GOF_AI_ENABLED=True, GOF_PUBLIC_AI_ASSISTANT_ENABLED=True, OPENAI_API_KEY='')
    def test_missing_openai_key_returns_disabled_mode(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'How can I pay?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'disabled')
        self.assertEqual(payload['fallback_reason'], 'missing_openai_key')
        self.assertFalse(payload['has_openai_key'])

    @override_settings(DEBUG=True)
    def test_assistant_proof_page_is_available_in_debug(self):
        response = self.client.get(reverse('core:assistant_proof'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('core:assistant_help'))

    @override_settings(GOF_SITE_STATUS='open')
    def test_public_assistant_prompt_context_includes_site_identity_and_launch_status(self):
        context = _prompt_context(
            'en',
            {
                'contact_url': '/en/contact/',
                'support_url': '/en/support/',
                'plans_url': '/en/plans/',
                'payment_url': '/en/payment-and-cancellation/',
                'catalog_url': '/en/catalog-and-ecommerce/',
                'promotion_url': '/en/facebook-posts/',
            },
            {
                'current_path': '/en/websites/',
                'current_page': 'Websites page',
            },
        )
        self.assertIn('The visitor is currently on the Get Online Fast website.', context)
        self.assertIn('"this site" usually means the Get Online Fast website itself.', context)
        self.assertIn('"my site", "my website", or "our website"', context)
        self.assertIn('Get Online Fast status: open', context)
        self.assertIn('Get Online Fast is already open', context)
        self.assertIn('Current path: /en/websites/', context)
        self.assertIn('Current page context: Websites page', context)

    def test_opening_question_has_authoritative_fallback_when_ai_is_unavailable(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'When does this open?', 'lang': 'en'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'site_availability')
        self.assertIn('already open', payload['answer'])
        self.assertIn('website', payload['answer'])

    def test_dutch_opening_question_has_authoritative_fallback(self):
        response = self.client.post(
            reverse('core:assistant_help'),
            {'message': 'Wanneer gaan jullie open?', 'lang': 'nl', 'page_path': '/nl/'},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'site_availability')
        self.assertIn('al open', payload['answer'])

    def test_new_company_question_does_not_fall_into_legal_links(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'I just opened a company', 'lang': 'en'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'business_start')
        self.assertIn('new business', payload['answer'])
        self.assertEqual([item['label'] for item in payload['suggested_links']], ['Websites', 'Plans', 'Contact'])

    def test_assistant_endpoint_returns_current_page_context(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'What website should I start with?', 'lang': 'en', 'page_path': '/en/websites/'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['current_path'], '/en/websites/')
        self.assertEqual(payload['current_page'], 'Websites page')

    def test_assistant_website_discovery_answer_lists_main_public_website_options(self):
        question = 'what kind of website can i build here?'
        response = self.client.get(reverse('core:assistant_help'), {'q': question, 'lang': 'en'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'website_options')
        if 'diagnostics' in payload:
            self.assertEqual(payload['diagnostics']['received_message'], question)
        elif 'received_message' in payload:
            self.assertEqual(payload['received_message'], question)
        self.assertIn('Starter Page', payload['answer'])
        self.assertIn('One-Time Website', payload['answer'])
        self.assertIn('Monthly Website', payload['answer'])
        self.assertIn('product catalog', payload['answer'])
        self.assertIn('online shop', payload['answer'])
        self.assertIn('small local businesses', payload['answer'])

    def test_assistant_website_discovery_answer_handles_simple_english_typo(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'what kiind of website can i build here?', 'lang': 'en'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('Starter Page', payload['answer'])
        self.assertIn('One-Time Website', payload['answer'])
        self.assertIn('Monthly Website', payload['answer'])
        self.assertIn('product catalog', payload['answer'])
        self.assertIn('online shop', payload['answer'])

    def test_assistant_posted_dutch_message_returns_dutch_website_options(self):
        response = self.client.post(
            reverse('core:assistant_help'),
            {
                'message': 'welke website moet ik kiezen?',
                'lang': 'nl',
                'page_path': '/nl/',
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['language'], 'nl')
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('Starter Page', payload['answer'])
        self.assertIn('bedrijfswebsite', payload['answer'])
        self.assertIn('productcatalogus', payload['answer'])

    def test_assistant_page_path_beats_wrong_posted_language_for_dutch(self):
        response = self.client.post(
            reverse('core:assistant_help'),
            {
                'message': 'welke website moet ik kiezen?',
                'lang': 'en',
                'page_path': '/nl/',
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['language'], 'nl')
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('bedrijfswebsite', payload['answer'])

    def test_assistant_posted_portuguese_message_returns_portuguese_website_options(self):
        response = self.client.post(
            reverse('core:assistant_help'),
            {
                'message': 'que tipo de site posso fazer aqui?',
                'lang': 'pt',
                'page_path': '/pt/',
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['language'], 'pt')
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('Starter Page', payload['answer'])
        self.assertIn('website empresarial', payload['answer'])
        self.assertIn('catálogo', payload['answer'])

    def test_assistant_page_path_beats_wrong_posted_language_for_portuguese(self):
        response = self.client.post(
            reverse('core:assistant_help'),
            {
                'message': 'que tipo de site posso fazer aqui?',
                'lang': 'en',
                'page_path': '/pt/',
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['language'], 'pt')
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('website empresarial', payload['answer'])

    def test_assistant_website_discovery_answer_is_in_dutch(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'welk soort website kan ik hier starten?', 'lang': 'nl'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('Je kunt beginnen met een Starter Page', payload['answer'])
        self.assertIn('volledige bedrijfswebsite', payload['answer'])
        self.assertIn('productcatalogus', payload['answer'])
        self.assertIn('kleine lokale bedrijven', payload['answer'])

    def test_assistant_website_discovery_answer_handles_natural_dutch_question(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'heb ik een volledige website nodig?', 'lang': 'nl'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('Starter Page', payload['answer'])
        self.assertIn('bedrijfswebsite', payload['answer'])

    def test_assistant_website_discovery_answer_is_in_portuguese(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'que tipo de website posso criar aqui?', 'lang': 'pt'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('Pode começar com uma Starter Page', payload['answer'])
        self.assertIn('website empresarial completo', payload['answer'])
        self.assertIn('catálogo', payload['answer'])
        self.assertIn('pequenos negócios locais', payload['answer'])

    def test_assistant_website_discovery_answer_handles_natural_portuguese_question(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'que website posso fazer?', 'lang': 'pt'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('Starter Page', payload['answer'])
        self.assertIn('website empresarial', payload['answer'])

    def test_assistant_path_only_dutch_fallback_returns_dutch(self):
        response = self.client.post(
            reverse('core:assistant_help'),
            {
                'message': 'welke website moet ik kiezen?',
                'page_path': '/nl/',
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['language'], 'nl')
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('bedrijfswebsite', payload['answer'])

    def test_assistant_path_only_portuguese_fallback_returns_portuguese(self):
        response = self.client.post(
            reverse('core:assistant_help'),
            {
                'message': 'que tipo de site posso fazer aqui?',
                'page_path': '/pt/',
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['language'], 'pt')
        self.assertEqual(payload['intent'], 'website_options')
        self.assertIn('website empresarial', payload['answer'])

    def test_assistant_ads_do_not_guarantee_customers(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Do ads guarantee customers?', 'lang': 'en'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'promotion_guarantee')
        self.assertTrue(payload['answer'].startswith('No.'))
        self.assertIn('cannot guarantee customers', payload['answer'])
        self.assertIn('Meta ads', payload['answer'])

    def test_assistant_google_ads_do_not_guarantee_sales(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Can Google Ads guarantee sales?', 'lang': 'en'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'promotion_guarantee')
        self.assertTrue(payload['answer'].startswith('No.'))
        self.assertIn('sales', payload['answer'])
        self.assertIn('Google Ads support', payload['answer'])

    def test_assistant_does_not_guarantee_rankings(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Do you guarantee rankings?', 'lang': 'en'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'promotion_guarantee')
        self.assertTrue(payload['answer'].startswith('No.'))
        self.assertIn('rankings', payload['answer'])
        self.assertIn('results', payload['answer'])

    def test_assistant_dutch_ads_do_not_guarantee_results(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Garanderen Google Ads klanten?', 'lang': 'nl'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'promotion_guarantee')
        self.assertTrue(payload['answer'].startswith('Nee.'))
        self.assertIn('geen klanten', payload['answer'])
        self.assertIn('Google Ads-ondersteuning', payload['answer'])


@override_settings(
    SITE_NOINDEX=False,
    GOF_AI_ENABLED=True,
    OPENAI_API_KEY='test-key',
    GOF_PUBLIC_AI_ASSISTANT_ENABLED=True,
    GOF_PUBLIC_AI_ASSISTANT_MAX_MESSAGES_PER_IP_PER_HOUR=5,
    GOF_PUBLIC_AI_ASSISTANT_MAX_MESSAGES_PER_IP_PER_DAY=20,
)
class PublicAiAssistantTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_public_assistant_prompt_requires_short_conversational_replies(self):
        self.assertIn('2 or 3 short sentences', PUBLIC_ASSISTANT_SYSTEM_PROMPT)
        self.assertIn('preferably under 60 words', PUBLIC_ASSISTANT_SYSTEM_PROMPT)
        self.assertIn('Do not list every product or service at once', PUBLIC_ASSISTANT_SYSTEM_PROMPT)

    @patch('core.services_public_assistant.generate_public_assistant_answer_with_ai', return_value='Get Online Fast can show your website options, expected pricing direction, and the right next step.')
    def test_public_ai_enabled_can_return_ai_mode(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'What are your prices?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertEqual(payload['fallback_reason'], '')
        self.assertTrue(payload['ai_enabled'])
        self.assertTrue(payload['public_ai_enabled'])
        self.assertTrue(payload['has_openai_key'])
        self.assertEqual(payload['model_used'], 'gpt-4.1-mini')
        self.assertIn('pricing direction', payload['answer'])
        mocked_answer.assert_called_once()

    @patch('core.services_public_assistant.generate_public_assistant_answer_with_ai', side_effect=Exception('boom'))
    def test_openai_error_returns_error_mode_with_fallback_answer(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'How can I pay?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'error')
        self.assertEqual(payload['fallback_reason'], 'openai_error')
        self.assertEqual(payload['intent'], 'payment')
        self.assertIn('Stripe', payload['answer'])
        mocked_answer.assert_called_once()

    @patch(
        'core.services_public_assistant.generate_public_assistant_answer_with_ai',
        return_value='I only help with Get Online Fast questions. I can explain website pricing, previews, domains, Google visibility, or the best next step for your business.',
    )
    def test_unrelated_question_gets_safe_refusal(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'What is the weather in Paris?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertEqual(payload['intent'], 'ai_answer')
        self.assertIn('Get Online Fast questions', payload['answer'])
        mocked_answer.assert_called_once()

    @patch(
        'core.services_public_assistant.generate_public_assistant_answer_with_ai',
        return_value='Get Online Fast is already open. We can help you choose and set up the right website, online shop, or promotion for your business.',
    )
    def test_this_site_open_question_answers_about_get_online_fast(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'When does this site open?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertIn('Get Online Fast is already open', payload['answer'])
        mocked_answer.assert_called_once()

    @patch(
        'core.services_public_assistant.generate_public_assistant_answer_with_ai',
        return_value='Yes. Get Online Fast is already open, and we can help you choose a website, online shop, or promotion for your business.',
    )
    def test_this_site_open_now_question_answers_about_get_online_fast(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Is this site open now?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertIn('Get Online Fast is already open', payload['answer'])
        mocked_answer.assert_called_once()

    @patch(
        'core.services_public_assistant.generate_public_assistant_answer_with_ai',
        return_value='Yes. Get Online Fast is already open. You can use the website now to explore website, online shop, promotion, and support options.',
    )
    def test_can_i_use_this_site_now_answers_about_get_online_fast(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Can I use this site now?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertIn('Get Online Fast is already open', payload['answer'])
        mocked_answer.assert_called_once()

    @patch(
        'core.services_public_assistant.generate_public_assistant_answer_with_ai',
        return_value='Your website timeline depends on your business details, content, and review rounds. Get Online Fast can prepare a private preview first, then confirm the next steps once the scope is clear.',
    )
    def test_my_site_ready_question_answers_about_customer_project(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'When will my site be ready?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertIn('Your website timeline depends on your business details', payload['answer'])
        mocked_answer.assert_called_once()

    @patch(
        'core.services_public_assistant.generate_public_assistant_answer_with_ai',
        return_value='Your website would normally be prepared on WordPress, with a private preview before activation or handoff where relevant. The exact build depends on your business needs and scope.',
    )
    def test_my_website_built_question_answers_about_customer_project(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'How will my website be built?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertIn('prepared on WordPress', payload['answer'])
        mocked_answer.assert_called_once()

    @patch(
        'core.services_public_assistant.generate_public_assistant_answer_with_ai',
        return_value='Get Online Fast is already open. We can help you choose a website setup and guide you through the next steps now.',
    )
    def test_get_online_fast_launch_question_answers_about_service_launch(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'When does Get Online Fast launch?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertIn('Get Online Fast is already open', payload['answer'])
        mocked_answer.assert_called_once()

    @patch(
        'core.services_public_assistant.generate_public_assistant_answer_with_ai',
        return_value='For a taxi business, the timeline depends on your business details, service area, and how quickly we can prepare and review your private preview. Get Online Fast can guide you through the next steps once your scope is clear.',
    )
    def test_business_specific_my_site_question_answers_about_customer_project(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'I need a website for my taxi business, when can it be ready?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertIn('For a taxi business, the timeline depends on your business details', payload['answer'])
        mocked_answer.assert_called_once()

    @patch(
        'core.services_public_assistant.generate_public_assistant_answer_with_ai',
        return_value='I focus on Get Online Fast questions. I can help with website pricing, previews, domains, Google visibility, email setup, support, or how to start.',
    )
    def test_scope_check_question_still_uses_ai_first(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'can you chat about anything else?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertEqual(payload['fallback_reason'], '')
        self.assertIn('Get Online Fast questions', payload['answer'])
        mocked_answer.assert_called_once()

    @patch(
        'core.services_public_assistant.generate_public_assistant_answer_with_ai',
        return_value='I only help with Get Online Fast questions, but I can help with website pricing, previews, domains, Google visibility, and getting started.',
    )
    def test_poem_request_still_uses_ai_first(self, mocked_answer):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Can you write me a poem about cats?'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'ai')
        self.assertEqual(payload['fallback_reason'], '')
        self.assertIn('Get Online Fast questions', payload['answer'])
        mocked_answer.assert_called_once()

    @override_settings(
        GOF_PUBLIC_AI_ASSISTANT_MAX_MESSAGES_PER_IP_PER_HOUR=1,
        GOF_PUBLIC_AI_ASSISTANT_MAX_MESSAGES_PER_IP_PER_DAY=2,
    )
    @patch('core.services_public_assistant.generate_public_assistant_answer_with_ai', return_value='A short GOF answer.')
    def test_rate_limit_blocks_after_limit(self, mocked_answer):
        first = self.client.get(reverse('core:assistant_help'), {'q': 'Which plan fits my business?'})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['mode'], 'ai')

        second = self.client.get(reverse('core:assistant_help'), {'q': 'Which plan fits my business?'})
        self.assertEqual(second.status_code, 200)
        payload = second.json()
        self.assertEqual(payload['mode'], 'fallback')
        self.assertEqual(payload['fallback_reason'], 'rate_limit_hour')
        self.assertEqual(payload['intent'], 'rate_limited')
        self.assertIn('You can use the start form or contact support.', payload['answer'])
        self.assertEqual(mocked_answer.call_count, 1)

    def test_input_too_long_falls_back_safely(self):
        long_question = ('How can I pay? ' * 80).strip()
        response = self.client.get(reverse('core:assistant_help'), {'q': long_question})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'fallback')
        self.assertEqual(payload['fallback_reason'], 'too_long')
        self.assertEqual(payload['intent'], 'payment')
        self.assertIn('Stripe', payload['answer'])


@override_settings(SITE_NOINDEX=False)
class HmdActivationFlowTests(TestCase):
    def test_hmd_activation_page_returns_200_with_hmd_copy(self):
        response = self.client.get(reverse('core:hmd_activation'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Website activatie voor HMD Klusbedrijf')
        self.assertContains(response, 'Betaling verloopt veilig via Stripe.')
        self.assertContains(response, reverse('core:terms'))
        self.assertContains(response, reverse('core:privacy_policy'))
        self.assertContains(response, reverse('core:cookie_policy'))
        self.assertContains(response, reverse('core:payment_and_cancellation'))
        self.assertContains(response, reverse('core:contact'))
        self.assertNotContains(response, 'localhost')
        self.assertNotContains(response, '127.0.0.1')

    @override_settings(GETONLINEFAST_HMD_KLUSBEDRIJF_PAYMENT_URL='')
    def test_hmd_activation_page_handles_missing_payment_link(self):
        response = self.client.get(reverse('core:hmd_activation'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'De betaallink is tijdelijk niet beschikbaar. Neem contact met ons op om de activatie af te ronden.',
        )

    def test_hmd_activation_page_is_noindex_even_when_public_pages_are_indexable(self):
        response = self.client.get(reverse('core:hmd_activation'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'noindex, nofollow')

    def test_hmd_activation_post_requires_all_confirmations(self):
        response = self.client.post(reverse('core:hmd_activation'), {})
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            'Bevestig eerst alle verplichte punten voordat je doorgaat naar de beveiligde betaling.',
            status_code=400,
        )

    def test_hmd_thank_you_page_returns_200(self):
        response = self.client.get(reverse('core:hmd_activation_thank_you'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bedankt voor je betaling')
        self.assertContains(response, 'De betaling is afgehandeld via Stripe.')
        self.assertContains(response, 'Ga niet uit van automatische activatie')
        self.assertContains(response, 'noindex, nofollow')

    def test_activation_and_thank_you_are_excluded_from_robots_and_sitemap(self):
        robots_response = self.client.get(reverse('robots_txt'))
        self.assertEqual(robots_response.status_code, 200)
        self.assertContains(robots_response, '/en/activate/hmd-klusbedrijf/')
        self.assertContains(robots_response, '/en/activate/hmd-klusbedrijf/thank-you/')

        sitemap_response = self.client.get(reverse('sitemap_xml'))
        self.assertEqual(sitemap_response.status_code, 200)
        self.assertNotContains(sitemap_response, reverse('core:hmd_activation'))
        self.assertNotContains(sitemap_response, reverse('core:hmd_activation_thank_you'))
