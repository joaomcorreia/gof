from django.contrib.admin.sites import site as admin_site
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ServiceOption


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

    def test_homepage_does_not_link_to_public_preview_flow(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '/start/')
        self.assertNotContains(response, reverse('ai_starter:start'))

    def test_public_pages_do_not_link_to_preview_start_flow(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '#start')
        self.assertNotContains(response, reverse('ai_starter:start'))
        self.assertContains(response, reverse('core:contact'))

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

    def test_public_start_route_is_not_accessible(self):
        response = self.client.get(reverse('ai_starter:start'))
        self.assertEqual(response.status_code, 404)

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
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catalogs and online shops')

        dutch_response = self.client.get('/nl/catalogus-en-webshop/')
        self.assertEqual(dutch_response.status_code, 200)
        self.assertContains(dutch_response, 'Catalogs and online shops')

    def test_plans_and_faq_do_not_use_coming_soon_ecommerce_wording(self):
        for route_name in ['core:plans', 'core:faq']:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'coming soon')
                self.assertNotContains(response, 'Coming soon')
                self.assertNotContains(response, 'Coming Soon')

    def test_homepage_has_catalog_and_ecommerce_section(self):
        response = self.client.get('/en/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catalogs and online shops')
        self.assertContains(response, 'Starter Catalog / WhatsApp Orders')
        self.assertContains(response, 'WooCommerce dashboard')
        self.assertContains(response, 'From €149 + VAT')
        self.assertContains(response, 'From €595 + VAT')
        self.assertContains(response, 'From €1,250 + VAT')

        dutch_response = self.client.get('/nl/')
        self.assertEqual(dutch_response.status_code, 200)
        self.assertContains(dutch_response, 'Vanaf €149 + btw')

    def test_plans_page_uses_short_catalog_teaser_only(self):
        response = self.client.get(reverse('core:plans'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Need a catalog or online shop?')
        self.assertTrue(
            reverse('core:catalog_and_ecommerce') in response.content.decode('utf-8')
            or reverse('core:catalog_and_ecommerce_nl') in response.content.decode('utf-8')
        )
        self.assertNotContains(response, 'Starter Catalog / WhatsApp Orders')
        self.assertNotContains(response, 'WooCommerce dashboard')

    def test_public_pages_do_not_contain_catalog_placeholder_copy(self):
        for route_name in ['core:home', 'core:plans', 'core:catalog_and_ecommerce']:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'Free Hero Pricing Page')
                self.assertNotContains(response, 'Available by request')

    def test_catalog_and_ecommerce_fallback_works_without_admin_rows(self):
        ServiceOption.objects.all().delete()

        homepage_response = self.client.get(reverse('core:home'))
        self.assertEqual(homepage_response.status_code, 200)
        self.assertContains(homepage_response, 'From €149 + VAT')
        self.assertContains(homepage_response, 'Prices are starting prices and exclude VAT.')

        detail_response = self.client.get(reverse('core:catalog_and_ecommerce'))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'From €595 + VAT')
        self.assertContains(detail_response, 'From €1,250 + VAT')

    def test_service_option_model_is_registered_in_admin(self):
        self.assertIn(ServiceOption, admin_site._registry)

    def test_service_option_seed_rows_exist(self):
        self.assertEqual(ServiceOption.objects.filter(section_key='catalog_ecommerce', language='en').count(), 3)
        self.assertEqual(ServiceOption.objects.filter(section_key='catalog_ecommerce', language='nl').count(), 3)


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
    def test_assistant_greeting_returns_friendly_greeting(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'hi'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['mode'], 'rule_based')
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
        self.assertContains(response, 'Which plan fits my business?')
        self.assertContains(response, 'Can I create a preview right now?')
        self.assertContains(response, 'How can I pay?')
        self.assertContains(response, 'Hello. I can help with websites, plans, payment, support, business email, and the WordPress dashboard.')

    def test_assistant_widget_shows_dutch_labels_on_dutch_page(self):
        response = self.client.get('/nl/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hulp nodig?')
        self.assertContains(response, 'Vraag stellen')
        self.assertContains(response, 'Bijv. Welk pakket past bij mijn bedrijf?')

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
        self.assertIn('€149 + VAT', payload['answer'])
        self.assertIn('€595 + VAT', payload['answer'])
        self.assertIn('€1,250 + VAT', payload['answer'])
        self.assertIn(reverse('core:catalog_and_ecommerce'), payload['suggested_links'][0]['url'])
        self.assertNotIn('coming soon', payload['answer'].lower())
        self.assertNotIn('HMD', payload['answer'])
        for link in payload['suggested_links']:
            self.assertNotIn('/examples/', link['url'])

    def test_assistant_online_shop_answer_links_to_dutch_catalog_page(self):
        response = self.client.get(reverse('core:assistant_help'), {'q': 'Kunnen jullie helpen met webshops?', 'lang': 'nl'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['intent'], 'ecommerce')
        self.assertIn('€149 + btw', payload['answer'])
        self.assertIn('€595 + btw', payload['answer'])
        self.assertIn('€1.250 + btw', payload['answer'])
        self.assertNotIn('HMD', payload['answer'])
        self.assertIn('/nl/catalogus-en-webshop/', payload['suggested_links'][0]['url'])

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
