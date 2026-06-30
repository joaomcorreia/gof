import os
import shutil
import stat
import tempfile
from unittest.mock import patch
from pathlib import Path
from django.core import mail
from django.http import QueryDict
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .admin import SiteAdmin, SiteHandoffAdmin
from .image_catalog import (
    get_alternate_image_for_business_type,
    get_default_image_for_business_type,
    get_image_by_key,
    get_image_choices,
)
from .models import Site, SiteContent, SiteHandoff, WebsiteRequest
from . import project_assets as project_assets_module
from .project_assets import (
    PROJECT_ASSET_ROOT,
    get_first_project_asset,
    get_project_asset_url,
    list_project_assets,
    normalize_project_slug,
)
from .services_ai import clean_assistant_output, generate_handoff_brief, infer_recommended_website_setup
from .services_handoff import build_site_handoff_payload
from .services import (
    build_generic_profile,
    get_onboarding_business_profile,
    get_onboarding_intro_variants,
    get_onboarding_service_suggestions,
    infer_business_family,
    normalize_business_type,
    resolve_business_profile,
)
from .template_catalog import (
    available_template_cards,
    default_template_slug,
    get_template_layout_class,
    normalize_template_slug,
)


class SiteHandoffTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.site = Site.objects.create(
            business_name='Northline Plumbing',
            service_type='Plumber',
            city='Breda',
            template_slug='local_service',
            color_palette=Site.ColorPalette.BLUE_DARK,
        )
        SiteContent.objects.create(
            site=self.site,
            section_key='hero',
            field_key='title',
            value='Reliable plumber in Breda',
            language='en',
        )
        SiteContent.objects.create(
            site=self.site,
            section_key='contact',
            field_key='cta_text',
            value='Contact us',
            language='en',
        )
        self.website_request = WebsiteRequest.objects.create(
            business_name='Northline Plumbing',
            business_type='Plumber',
            contact_name='Jane Owner',
            contact_email='jane@example.com',
            contact_phone='+31600000000',
            contact_whatsapp='+31611111111',
            current_domain='northline.example.com',
            needs_domain_help=True,
            main_language='en',
            extra_languages='nl',
            main_services='Repairs and installations',
            business_description='Trusted local plumbing support.',
            preferred_colors='Blue and white',
            style_notes='Keep it practical and clean.',
            social_links='https://facebook.example.com/northline',
            opening_hours='Mon-Fri 09:00-17:00',
            special_requests='Add WhatsApp contact option.',
            source_code='GEMEENTE50',
            normal_price='325.00',
            offer_price='275.00',
            status=WebsiteRequest.Status.NEW,
        )
        self.staff_user = self.user_model.objects.create_superuser(
            username='staff-admin',
            email='staff@example.com',
            password='test-pass-123',
        )
        self.regular_user = self.user_model.objects.create_user(
            username='regular-user',
            email='regular@example.com',
            password='test-pass-123',
        )

    def test_build_site_handoff_payload_creates_expected_structure(self):
        payload = build_site_handoff_payload(self.site, website_request=self.website_request)

        self.assertEqual(payload['schema_version'], 1)
        self.assertEqual(payload['source']['system'], 'django_getonlinefast')
        self.assertEqual(payload['source']['site_id'], self.site.id)
        self.assertEqual(payload['source']['public_id'], str(self.site.public_id))
        self.assertEqual(payload['business']['business_name'], self.site.business_name)
        self.assertEqual(payload['design']['template_slug'], self.site.template_slug)
        self.assertEqual(payload['design']['color_palette'], self.site.color_palette)
        self.assertEqual(payload['website_request']['contact_email'], 'jane@example.com')
        self.assertEqual(payload['website_request']['contact_name'], 'Jane Owner')
        self.assertEqual(payload['website_request']['main_language'], 'en')
        self.assertEqual(payload['website_request']['source_code'], 'GEMEENTE50')
        self.assertEqual(payload['wordpress_target']['site_url'], '')
        self.assertIn('does not mutate WordPress', payload['notes'])

    def test_template_registry_returns_four_options(self):
        templates = available_template_cards()

        self.assertEqual(len(templates), 4)
        self.assertEqual(templates[0]['slug'], 'classic_service')
        self.assertEqual(templates[1]['slug'], 'visual_hero')
        self.assertEqual(templates[2]['slug'], 'card_grid')
        self.assertEqual(templates[3]['slug'], 'gof-canva-layout-test-v1')
        self.assertEqual(str(templates[3]['category']), 'Professional & Practical')
        self.assertEqual(str(templates[3]['style']), 'Editorial / Sharp')
        self.assertEqual(str(templates[3]['layout_label']), 'Full-width rows')

    def test_image_catalog_returns_choices(self):
        choices = get_image_choices()

        self.assertGreaterEqual(len(choices), 7)
        self.assertEqual(choices[0]['key'], 'generic_service_01')
        self.assertEqual(choices[0]['style_type'], 'photo')
        self.assertTrue(choices[0]['path_exists'])

    def test_unknown_image_key_falls_back_safely(self):
        fallback = get_image_by_key('not-real')

        self.assertEqual(fallback['key'], 'generic_service_01')
        self.assertIn('core/img/', fallback['static_path'])
        self.assertEqual(fallback['style_type'], 'photo')

    def test_alternate_image_helper_returns_different_key_when_possible(self):
        alternate = get_alternate_image_for_business_type('Garage', current_key='garage_01')

        self.assertEqual(alternate['category'], 'garage')
        self.assertEqual(alternate['key'], 'garage_02')
        self.assertNotEqual(alternate['static_path'], get_image_by_key('garage_01')['static_path'])

    def test_alternate_image_helper_prefers_photo_entries_over_placeholder(self):
        alternate = get_alternate_image_for_business_type('Garage', current_key='placeholder_garage_01')

        self.assertEqual(alternate['style_type'], 'photo')

    def test_alternate_image_helper_returns_current_when_no_distinct_alternate_exists(self):
        alternate = get_alternate_image_for_business_type('Unknown service', current_key='generic_service_01')

        self.assertNotEqual(alternate['key'], 'placeholder_clean_01')
        self.assertEqual(alternate['style_type'], 'photo')

    def test_template_registry_exposes_layout_family_for_all_templates(self):
        templates = available_template_cards()

        self.assertEqual(templates[0]['layout_family'], 'boxed')
        self.assertEqual(templates[0]['layout_class'], 'layout-boxed')
        self.assertEqual(templates[1]['layout_family'], 'full_width')
        self.assertEqual(templates[1]['layout_class'], 'layout-full-width')
        self.assertEqual(templates[2]['layout_family'], 'mixed')
        self.assertEqual(templates[2]['layout_class'], 'layout-mixed')
        self.assertEqual(templates[3]['layout_family'], 'full_width')
        self.assertEqual(templates[3]['layout_class'], 'layout-full-width')

    def test_start_page_renders_template_cards(self):
        response = self.client.get(reverse('ai_starter:start'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Start your website preview')
        self.assertContains(response, 'What is your website for?')
        self.assertContains(response, 'Your intro section')
        self.assertContains(response, 'data-onboarding-step="1"', html=False)
        self.assertContains(response, 'Live preview')

    def test_start_page_includes_progress_ui(self):
        response = self.client.get(reverse('ai_starter:start'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Onboarding progress')
        self.assertContains(response, 'Step 1 of 8')
        self.assertContains(response, 'Choose how you want to start')
        self.assertContains(response, 'Your private preview is ready to prepare')

    def test_business_type_suggestions_are_available_for_makeup_artist(self):
        profile = get_onboarding_business_profile('Makeup artist')
        services = get_onboarding_service_suggestions('Makeup artist')
        intro_variants = get_onboarding_intro_variants('Makeup artist')

        self.assertIn('Makeup for special moments', str(profile['hero_title']))
        self.assertIn('Professional makeup services for weddings, events, photoshoots, and personal appointments.', str(profile['hero_description']))
        self.assertIn('Request appointment', str(profile['hero_cta']))
        self.assertIn(
            'Create a confident look for weddings, events, photoshoots, or personal appointments with makeup tailored to your style and occasion.',
            str(profile['intro_text']),
        )
        self.assertIn('Bridal makeup', [str(item) for item in services])
        self.assertEqual(len(intro_variants), 3)
        self.assertIn('A polished first impression', str(intro_variants[0]['title']))
        self.assertIn('Makeup tailored to your occasion', str(intro_variants[1]['title']))
        self.assertIn('Feel ready for every moment', str(intro_variants[2]['title']))

    def test_business_type_suggestions_are_available_for_garage(self):
        profile = get_onboarding_business_profile('Garage')
        services = get_onboarding_service_suggestions('Garage')

        self.assertIn('Reliable car care and repair', str(profile['hero_title']))
        self.assertIn('Diagnostics', [str(item) for item in services])

    def test_normalize_business_type_safely_normalizes_input(self):
        self.assertEqual(normalize_business_type('Technology and computer parts'), 'technology and computer parts')
        self.assertEqual(normalize_business_type('Electronics-Shop'), 'electronics shop')

    def test_resolve_business_profile_for_technology_and_computer_parts_uses_shop_family(self):
        profile = resolve_business_profile('Technology and computer parts')

        self.assertEqual(profile['family'], 'shop_catalog')
        self.assertEqual(profile['recommended_template_slug'], 'card_grid')
        self.assertIn('Technology products and computer parts', profile['hero_title'])
        self.assertIn('View products', profile['hero_cta'])
        self.assertIn('Computer parts', profile['suggested_services'])

    def test_computer_parts_and_electronics_shop_resolve_to_shop_catalog(self):
        profile_one = resolve_business_profile('Computer parts')
        profile_two = resolve_business_profile('electronics shop')

        self.assertEqual(profile_one['family'], 'shop_catalog')
        self.assertEqual(profile_two['family'], 'shop_catalog')
        self.assertEqual(profile_one['recommended_template_slug'], 'card_grid')
        self.assertEqual(profile_two['recommended_template_slug'], 'card_grid')

    def test_unknown_business_type_preserves_entered_value_in_generic_fallback(self):
        profile = resolve_business_profile('Dragon candle repair')

        self.assertEqual(profile['family'], 'generic')
        self.assertEqual(profile['display_business_type'], 'Dragon candle repair')
        self.assertIn('Website preview for Dragon candle repair', profile['hero_title'])
        self.assertNotIn('Your business type', profile['hero_title'])
        self.assertEqual(profile['recommended_template_slug'], 'classic_service')

    def test_infer_business_family_returns_none_for_unknown_value(self):
        self.assertIsNone(infer_business_family('Dragon candle repair'))

    def test_build_generic_profile_uses_family_template_when_provided(self):
        family = infer_business_family('technology and computer parts')
        profile = build_generic_profile('Technology and computer parts', family=family)

        self.assertEqual(profile['recommended_template_slug'], 'card_grid')
        self.assertEqual(profile['display_business_type'], 'Technology and computer parts')

    def test_start_page_shows_makeup_suggestions_after_step_one_submit(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '1',
                'wizard_action': 'next',
                'business_type': 'Makeup artist',
                'hero_title': 'Professional website preview for your business',
                'hero_description': 'A clear starting website with your services, contact details, and next steps ready to review.',
                'hero_cta': 'Request information',
                'intro_title': 'A simple introduction section',
                'intro_text': 'Use this section to explain what your business does, who you help, and why customers should contact you.',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Step 2 of 8')
        self.assertContains(response, 'Makeup for special moments')
        self.assertContains(response, 'Professional makeup services for weddings, events, photoshoots, and personal appointments.')
        self.assertContains(response, 'Request appointment')
        self.assertContains(response, 'Create a confident look for weddings, events, photoshoots, or personal appointments with makeup tailored to your style and occasion.')

    def test_step_one_hydration_prefers_visible_field_over_hidden_fallback_values(self):
        post_data = QueryDict('', mutable=True)
        post_data.update(
            {
                'current_step': '1',
                'wizard_action': 'next',
                'template_slug': 'classic_service',
                'previous_business_type': '',
            }
        )
        post_data.appendlist('business_type', '')
        post_data.appendlist('business_type', 'Makeup artist')
        post_data.appendlist('hero_title', 'Professional website preview for your business')
        post_data.appendlist('hero_title', 'Professional website preview for your business')
        post_data.appendlist('hero_description', 'A clear starting website with your services, contact details, and next steps ready to review.')
        post_data.appendlist('hero_description', 'A clear starting website with your services, contact details, and next steps ready to review.')
        post_data.appendlist('hero_cta', 'Request information')
        post_data.appendlist('hero_cta', 'Request information')
        post_data.appendlist('intro_title', 'A simple introduction section')
        post_data.appendlist('intro_title', 'A simple introduction section')
        post_data.appendlist('intro_text', 'Use this section to explain what your business does, who you help, and why customers should contact you.')
        post_data.appendlist('intro_text', 'Use this section to explain what your business does, who you help, and why customers should contact you.')

        response = self.client.post(reverse('ai_starter:start'), post_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Makeup artist')
        self.assertContains(response, 'Makeup for special moments')
        self.assertNotContains(response, 'Professional website preview for your business')
        self.assertContains(response, 'Request appointment')

    def test_update_suggestion_keeps_user_on_step_one_and_refreshes_hero(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '1',
                'wizard_action': 'update_hero',
                'business_type': 'Makeup artist',
                'hero_title': 'Professional website preview for your business',
                'hero_description': 'A clear starting website with your services, contact details, and next steps ready to review.',
                'hero_cta': 'Request information',
                'intro_title': 'A simple introduction section',
                'intro_text': 'Use this section to explain what your business does, who you help, and why customers should contact you.',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-onboarding-step="1"', html=False)
        self.assertContains(response, 'Makeup for special moments')
        self.assertContains(response, 'Professional makeup services for weddings, events, photoshoots, and personal appointments.')
        self.assertContains(response, 'Request appointment')
        self.assertContains(response, '<h2>Makeup for special moments</h2>', html=False)

    def test_update_suggestion_for_technology_and_computer_parts_uses_shop_profile(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '1',
                'wizard_action': 'update_hero',
                'business_type': 'Technology and computer parts',
                'hero_title': 'Professional website preview for your business',
                'hero_description': 'A clear starting website with your services, contact details, and next steps ready to review.',
                'hero_cta': 'Request information',
                'intro_title': 'A simple introduction section',
                'intro_text': 'Use this section to explain what your business does, who you help, and why customers should contact you.',
                'template_slug': 'classic_service',
                'template_locked': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Technology products and computer parts')
        self.assertContains(response, 'Browse computer parts, accessories, electronics, and tech products with a clear way to request information or order.')
        self.assertContains(response, 'View products')
        self.assertContains(response, 'Computer parts')
        self.assertContains(response, 'Laptop accessories')
        self.assertContains(response, 'Phone accessories')
        self.assertContains(response, 'value="card_grid"', html=False)

    def test_normal_next_for_technology_and_computer_parts_uses_family_intro_on_step_two(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '1',
                'wizard_action': 'next',
                'business_type': 'Technology and computer parts',
                'hero_title': 'Professional website preview for your business',
                'hero_description': 'A clear starting website with your services, contact details, and next steps ready to review.',
                'hero_cta': 'Request information',
                'intro_title': 'A simple introduction section',
                'intro_text': 'Use this section to explain what your business does, who you help, and why customers should contact you.',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Step 2 of 8')
        self.assertContains(response, 'Technology products and computer parts')
        self.assertContains(response, 'Products organised clearly')
        self.assertContains(response, 'Help visitors browse categories, compare products, and ask for information with a clearer catalog-style introduction.')
        self.assertContains(response, 'value="card_grid"', html=False)

    def test_start_page_step_one_renders_suggested_hero_panel(self):
        response = self.client.get(reverse('ai_starter:start'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Suggested hero')
        self.assertContains(response, 'Suggested title')
        self.assertContains(response, 'Suggested description')
        self.assertContains(response, 'Suggested CTA')
        self.assertContains(response, 'Update suggestion')

    def test_start_page_step_two_renders_suggested_intro_panel(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '1',
                'wizard_action': 'next',
                'business_type': 'Makeup artist',
                'hero_title': 'Professional website preview for your business',
                'hero_description': 'A clear starting website with your services, contact details, and next steps ready to review.',
                'hero_cta': 'Request information',
                'intro_title': 'A simple introduction section',
                'intro_text': 'Use this section to explain what your business does, who you help, and why customers should contact you.',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Suggested intro')
        self.assertContains(response, 'Suggested intro heading')
        self.assertContains(response, 'Suggested intro text')
        self.assertContains(response, 'Regenerate intro suggestion')
        self.assertContains(response, 'Preview content. Final content is reviewed and completed after activation.')

    def test_manual_hero_edit_is_preserved_on_normal_next(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '1',
                'wizard_action': 'next',
                'business_type': 'Makeup artist',
                'hero_title': 'Custom hero title',
                'hero_description': 'Custom hero description.',
                'hero_cta': 'Custom CTA',
                'intro_title': 'A simple introduction section',
                'intro_text': 'Use this section to explain what your business does, who you help, and why customers should contact you.',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Step 2 of 8')
        self.assertContains(response, 'Custom hero title')
        self.assertContains(response, 'Custom hero description.')
        self.assertContains(response, 'Custom CTA')

    def test_unknown_business_type_does_not_render_placeholder_business_type_after_update(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '1',
                'wizard_action': 'update_hero',
                'business_type': 'Dragon candle repair',
                'hero_title': 'Professional website preview for your business',
                'hero_description': 'A clear starting website with your services, contact details, and next steps ready to review.',
                'hero_cta': 'Request information',
                'intro_title': 'A simple introduction section',
                'intro_text': 'Use this section to explain what your business does, who you help, and why customers should contact you.',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dragon candle repair')
        self.assertContains(response, 'Website preview for Dragon candle repair')
        self.assertNotContains(response, 'Your business type')

    def test_regenerate_intro_suggestion_changes_intro_deterministically(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '2',
                'wizard_action': 'regenerate_intro',
                'business_type': 'Makeup artist',
                'previous_business_type': 'Makeup artist',
                'hero_title': 'Makeup for special moments',
                'hero_description': 'Professional makeup services for weddings, events, photoshoots, and personal appointments.',
                'hero_cta': 'Request appointment',
                'intro_title': 'A polished first impression',
                'intro_text': 'Create a confident look for weddings, events, photoshoots, or personal appointments with makeup tailored to your style and occasion.',
                'template_slug': 'classic_service',
                'selected_services_csv': 'Bridal makeup||Event makeup||Photoshoot makeup',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Makeup tailored to your occasion')
        self.assertContains(response, 'From bridal makeup to photoshoots and events, your preview can show customers how your services help them feel prepared and confident.')

    def test_manual_intro_edit_is_preserved_on_normal_next(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '2',
                'wizard_action': 'next',
                'business_type': 'Makeup artist',
                'previous_business_type': 'Makeup artist',
                'hero_title': 'Makeup for special moments',
                'hero_description': 'Professional makeup services for weddings, events, photoshoots, and personal appointments.',
                'hero_cta': 'Request appointment',
                'intro_title': 'Custom intro heading',
                'intro_text': 'Custom intro copy for this makeup business.',
                'template_slug': 'classic_service',
                'selected_services_csv': 'Bridal makeup||Event makeup||Photoshoot makeup',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Custom intro heading')
        self.assertContains(response, 'Custom intro copy for this makeup business.')

    def test_service_chips_render_for_makeup_artist(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '2',
                'wizard_action': 'next',
                'business_type': 'Makeup artist',
                'previous_business_type': 'Makeup artist',
                'hero_title': 'Makeup for special moments',
                'hero_description': 'Professional makeup services for weddings, events, photoshoots, and personal appointments.',
                'hero_cta': 'Request appointment',
                'intro_title': 'A polished first impression',
                'intro_text': 'Create a confident look for weddings, events, photoshoots, or personal appointments with makeup tailored to your style and occasion.',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Suggested services for Makeup artist')
        self.assertContains(response, 'Bridal makeup')
        self.assertContains(response, 'Event makeup')
        self.assertContains(response, 'Makeup trial')

    def test_selected_services_persist_to_confirmation_summary(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '8',
                'wizard_action': 'next',
                'business_type': 'Makeup artist',
                'previous_business_type': 'Makeup artist',
                'hero_title': 'Makeup for special moments',
                'hero_description': 'Professional makeup services for weddings, events, photoshoots, and personal appointments.',
                'hero_cta': 'Request appointment',
                'intro_title': 'A polished first impression',
                'intro_text': 'Create a confident look for weddings, events, photoshoots, or personal appointments with makeup tailored to your style and occasion.',
                'selected_services_csv': 'Bridal makeup||Event makeup||Photoshoot makeup',
                'gallery_choice': 'example_layout',
                'reviews_choice': 'trust_section',
                'business_name': 'Glow Studio',
                'city': 'Rotterdam',
                'template_slug': 'visual_hero',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your selected preview direction')
        self.assertContains(response, 'Bridal makeup, Event makeup, Photoshoot makeup')

    def test_final_submit_saves_intro_heading_and_text(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '8',
                'wizard_action': 'create_preview',
                'business_type': 'Makeup artist',
                'previous_business_type': 'Makeup artist',
                'hero_title': 'Makeup for special moments',
                'hero_description': 'Professional makeup services for weddings, events, photoshoots, and personal appointments.',
                'hero_cta': 'Request appointment',
                'intro_title': 'Custom intro heading',
                'intro_text': 'Custom intro copy for this makeup business.',
                'selected_services_csv': 'Bridal makeup||Event makeup||Photoshoot makeup',
                'gallery_choice': 'example_layout',
                'reviews_choice': 'trust_section',
                'business_name': 'Glow Studio',
                'city': 'Rotterdam',
                'template_slug': 'visual_hero',
            },
        )

        self.assertEqual(response.status_code, 302)
        site = Site.objects.latest('created_at')
        intro_field = SiteContent.objects.get(
            site=site,
            section_key='services',
            field_key='intro',
            language='en',
        )
        heading_field = SiteContent.objects.get(
            site=site,
            section_key='services',
            field_key='title',
            language='en',
        )
        self.assertEqual(heading_field.value, 'Custom intro heading')
        self.assertEqual(intro_field.value, 'Custom intro copy for this makeup business.')

    def test_start_submission_saves_selected_template_slug(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'business_name': 'Template Test Co',
                'service_type': 'Electrician',
                'city': 'Rotterdam',
                'template_slug': 'visual_hero',
            },
        )

        self.assertEqual(response.status_code, 302)
        site = Site.objects.latest('created_at')
        self.assertEqual(site.template_slug, 'visual_hero')

    def test_start_flow_creates_default_hero_image_for_business_type(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'business_name': 'Garage Prime',
                'service_type': 'Garage',
                'city': 'Rotterdam',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 302)
        site = Site.objects.latest('created_at')
        hero_image = SiteContent.objects.get(
            site=site,
            section_key='hero',
            field_key='hero_image',
            language='en',
        )
        self.assertEqual(hero_image.value, get_default_image_for_business_type('Garage')['key'])

    def test_start_submission_saves_classic_service_template_slug(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'business_name': 'Classic Template Co',
                'service_type': 'Garage',
                'city': 'Breda',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 302)
        site = Site.objects.latest('created_at')
        self.assertEqual(site.template_slug, 'classic_service')

    def test_start_submission_saves_card_grid_template_slug(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'business_name': 'Grid Template Co',
                'service_type': 'Print Shop',
                'city': 'Eindhoven',
                'template_slug': 'card_grid',
            },
        )

        self.assertEqual(response.status_code, 302)
        site = Site.objects.latest('created_at')
        self.assertEqual(site.template_slug, 'card_grid')

    def test_start_submission_with_invalid_or_missing_template_falls_back_safely(self):
        invalid_response = self.client.post(
            reverse('ai_starter:start'),
            {
                'business_name': 'Fallback Co',
                'service_type': 'Plumber',
                'city': 'Utrecht',
                'template_slug': 'not-a-real-template',
            },
        )

        self.assertEqual(invalid_response.status_code, 302)
        invalid_site = Site.objects.latest('created_at')
        self.assertEqual(invalid_site.template_slug, default_template_slug())

        missing_response = self.client.post(
            reverse('ai_starter:start'),
            {
                'business_name': 'Fallback Two',
                'service_type': 'Painter',
                'city': 'Tilburg',
            },
        )

        self.assertEqual(missing_response.status_code, 302)
        missing_site = Site.objects.latest('created_at')
        self.assertEqual(missing_site.template_slug, default_template_slug())

    def test_start_page_can_post_selected_services_gallery_trust_and_create_preview(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '8',
                'wizard_action': 'create_preview',
                'business_type': 'Makeup artist',
                'hero_title': 'Makeup for special moments',
                'hero_description': 'Professional makeup services for weddings, events, photoshoots, and personal appointments.',
                'hero_cta': 'Request appointment',
                'intro_title': 'A polished first impression',
                'intro_text': 'Preview content. Final content is reviewed and completed after activation.',
                'selected_services': ['Bridal makeup', 'Event makeup', 'Photoshoot makeup'],
                'selected_services_csv': 'Bridal makeup||Event makeup||Photoshoot makeup',
                'gallery_choice': 'template_assets',
                'reviews_choice': 'trust_section',
                'business_name': 'Glow Studio',
                'city': 'Rotterdam',
                'contact_email': 'hello@glowstudio.test',
                'contact_phone': '+31010020030',
                'contact_whatsapp': '+31612345678',
                'template_slug': 'visual_hero',
            },
        )

        self.assertEqual(response.status_code, 302)
        site = Site.objects.latest('created_at')
        self.assertEqual(site.business_name, 'Glow Studio')
        self.assertEqual(site.service_type, 'Makeup artist')
        self.assertEqual(site.template_slug, 'visual_hero')
        service_items = list(
            SiteContent.objects.filter(site=site, section_key='services', language='en').order_by('field_key')
        )
        self.assertTrue(any(item.value == 'Bridal makeup' for item in service_items))
        self.assertTrue(any(item.value == 'Event makeup' for item in service_items))
        self.assertTrue(any(item.value == 'Photoshoot makeup' for item in service_items))

    def test_final_submit_preserves_explicit_template_choice_for_shop_family(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '8',
                'wizard_action': 'create_preview',
                'business_type': 'Technology and computer parts',
                'previous_business_type': 'Technology and computer parts',
                'hero_title': 'Custom shop title',
                'hero_description': 'Custom shop description.',
                'hero_cta': 'View products',
                'intro_title': 'Products organised clearly',
                'intro_text': 'Custom intro for the catalog preview.',
                'selected_services_csv': 'Computer parts||Laptop accessories||Gaming accessories',
                'gallery_choice': 'example_layout',
                'reviews_choice': 'trust_section',
                'business_name': 'Tech Parts Hub',
                'city': 'Rotterdam',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 302)
        site = Site.objects.latest('created_at')
        self.assertEqual(site.template_slug, 'classic_service')

    def test_final_submit_for_unknown_business_type_uses_safe_generic_fallback(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '8',
                'wizard_action': 'create_preview',
                'business_type': 'Dragon candle repair',
                'previous_business_type': 'Dragon candle repair',
                'hero_title': 'Website preview for Dragon candle repair',
                'hero_description': 'A clear starting website to explain your services, contact details, and next steps.',
                'hero_cta': 'Request information',
                'intro_title': 'A simple introduction section',
                'intro_text': 'Use this section to explain what dragon candle repair offers, how customers can contact you, and what they should do next.',
                'selected_services_csv': 'Main service||Popular option||Customer support',
                'gallery_choice': 'example_layout',
                'reviews_choice': 'trust_section',
                'business_name': 'Dragon Candle Repair',
                'city': 'Rotterdam',
            },
        )

        self.assertEqual(response.status_code, 302)
        site = Site.objects.latest('created_at')
        self.assertEqual(site.template_slug, 'classic_service')
        hero_title = SiteContent.objects.get(
            site=site,
            section_key='hero',
            field_key='title',
            language='en',
        )
        self.assertEqual(hero_title.value, 'Website preview for Dragon candle repair')

    def test_partial_wizard_state_does_not_500_and_regenerates_defaults(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'current_step': '2',
                'wizard_action': 'next',
                'business_type': 'Garage',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reliable car care and repair')
        self.assertContains(response, 'Explain your workshop clearly')

    def test_start_page_template_step_shows_basic_growth_shop(self):
        response = self.client.get(f"{reverse('ai_starter:start')}?step=7")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose how you want to start')
        self.assertContains(response, 'Basic')
        self.assertContains(response, 'Growth')
        self.assertContains(response, 'Shop')

    def test_preview_frame_includes_selected_template_class_context(self):
        self.site.template_slug = 'card_grid'
        self.site.save(update_fields=['template_slug', 'updated_at'])

        response = self.client.get(
            reverse('ai_starter:preview_frame', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'template-card-grid')
        self.assertContains(response, 'layout-mixed')
        self.assertContains(response, 'section-container--full')
        self.assertContains(response, 'data-template-slug="card_grid"', html=False)

    def test_preview_frame_renders_selected_hero_image_static_path(self):
        SiteContent.objects.create(
            site=self.site,
            section_key='hero',
            field_key='hero_image',
            value='garage_01',
            language='en',
        )

        response = self.client.get(
            reverse('ai_starter:preview_frame', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'core/img/hero-library/garage/garage-01.png')
        self.assertContains(response, 'Garage or car repair hero photo')

    def test_preview_frame_maps_legacy_template_slug_to_classic_service_class(self):
        self.site.template_slug = 'local_service'
        self.site.save(update_fields=['template_slug', 'updated_at'])

        response = self.client.get(
            reverse('ai_starter:preview_frame', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'template-classic-service')
        self.assertContains(response, 'layout-boxed')
        self.assertEqual(normalize_template_slug(self.site.template_slug), 'classic_service')

    def test_preview_frame_renders_new_gof_canva_layout_sections(self):
        self.site.template_slug = 'gof-canva-layout-test-v1'
        self.site.save(update_fields=['template_slug', 'updated_at'])

        response = self.client.get(
            reverse('ai_starter:preview_frame', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'template-gof-canva-layout-test-v1')
        self.assertContains(response, 'id="portfolio"', html=False)
        self.assertContains(response, 'id="process"', html=False)
        self.assertContains(response, 'site-section-contact-details', html=False)
        self.assertContains(response, 'site-section-showcase', html=False)
        self.assertContains(response, 'site-section-footer', html=False)
        self.assertContains(response, 'site-floating-action--contact', html=False)
        self.assertContains(response, 'aria-label="Back to top"', html=False)

    def test_staff_template_preview_route_renders_gof_canva_template(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:template_preview', kwargs={'template_slug': 'gof-canva-layout-test-v1'}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'template-gof-canva-layout-test-v1')
        self.assertContains(response, 'site-section-showcase', html=False)
        self.assertContains(response, 'Website prepared with Get Online Fast')
        self.assertContains(response, 'noindex, nofollow')
        self.assertContains(response, 'href="#contact"', html=False)

    def test_staff_template_preview_route_returns_404_for_invalid_slug(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:template_preview', kwargs={'template_slug': 'not-a-real-template'}))

        self.assertEqual(response.status_code, 404)

    def test_staff_template_preview_route_is_noindex(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:template_preview', kwargs={'template_slug': 'gof-canva-layout-test-v1'}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">', html=False)

    def test_selected_template_returns_expected_layout_class(self):
        self.assertEqual(get_template_layout_class('classic_service'), 'layout-boxed')
        self.assertEqual(get_template_layout_class('visual_hero'), 'layout-full-width')
        self.assertEqual(get_template_layout_class('card_grid'), 'layout-mixed')
        self.assertEqual(get_template_layout_class('gof-canva-layout-test-v1'), 'layout-full-width')

    def test_invalid_template_falls_back_to_boxed_layout_class(self):
        self.assertEqual(get_template_layout_class('not-a-real-template'), 'layout-boxed')

    def test_build_site_handoff_payload_works_without_website_request(self):
        payload = build_site_handoff_payload(self.site)

        self.assertEqual(payload['source']['site_id'], self.site.id)
        self.assertNotIn('website_request', payload)

    def test_payload_includes_site_content_rows(self):
        payload = build_site_handoff_payload(self.site)

        self.assertEqual(len(payload['content']), 2)
        self.assertEqual(payload['content'][0]['section_key'], 'contact')
        self.assertEqual(payload['content'][0]['field_key'], 'cta_text')
        self.assertEqual(payload['content'][1]['section_key'], 'hero')
        self.assertEqual(payload['content'][1]['value'], 'Reliable plumber in Breda')

    def test_site_handoff_refresh_payload_updates_payload(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            website_request=self.website_request,
            status=SiteHandoff.Status.DRAFT,
        )

        SiteContent.objects.filter(site=self.site, section_key='hero', field_key='title').update(
            value='Updated hero title'
        )
        payload = handoff.refresh_payload()
        handoff.refresh_from_db()

        hero_entry = next(
            item for item in payload['content']
            if item['section_key'] == 'hero' and item['field_key'] == 'title'
        )
        self.assertEqual(hero_entry['value'], 'Updated hero title')
        self.assertEqual(handoff.handoff_payload['source']['site_id'], self.site.id)

    def test_admin_action_creates_prepared_handoff_for_site(self):
        request = RequestFactory().post('/admin/ai_starter/site/')
        request.user = self.staff_user

        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))

        plugin_file = Path(self.site._meta.apps.get_app_config('ai_starter').path).parent / (
            'jcw-wp-current/wp-content/plugins/jcw-ai-assistant/jcw-ai-assistant.php'
        )
        plugin_mtime_before = plugin_file.stat().st_mtime

        model_admin = SiteAdmin(Site, AdminSite())
        model_admin.prepare_wordpress_handoff(request, Site.objects.filter(pk=self.site.pk))

        handoff = SiteHandoff.objects.get(site=self.site, target_system='wordpress_jcw')
        self.assertEqual(handoff.status, SiteHandoff.Status.PREPARED)
        self.assertEqual(handoff.prepared_by, self.staff_user)
        self.assertEqual(handoff.handoff_payload['source']['site_id'], self.site.id)
        self.assertEqual(plugin_file.stat().st_mtime, plugin_mtime_before)

    def test_mark_completed_sets_status_and_timestamp(self):
        handoff = SiteHandoff.objects.create(site=self.site)

        handoff.mark_completed()
        handoff.refresh_from_db()

        self.assertEqual(handoff.status, SiteHandoff.Status.COMPLETED)
        self.assertIsNotNone(handoff.completed_at)

    def test_public_user_cannot_prepare_handoff(self):
        response = self.client.post(
            reverse('ai_starter:prepare_handoff', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(SiteHandoff.objects.filter(site=self.site).exists())

    def test_non_staff_authenticated_user_cannot_prepare_handoff(self):
        self.client.force_login(self.regular_user)

        response = self.client.post(
            reverse('ai_starter:prepare_handoff', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(SiteHandoff.objects.filter(site=self.site).exists())

    def test_staff_post_creates_or_refreshes_handoff(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('ai_starter:prepare_handoff', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 302)
        handoff = SiteHandoff.objects.get(site=self.site, target_system='wordpress_jcw')
        self.assertEqual(handoff.status, SiteHandoff.Status.PREPARED)
        self.assertEqual(handoff.prepared_by, self.staff_user)
        self.assertEqual(handoff.handoff_payload['source']['site_id'], self.site.id)

    def test_preview_page_does_not_show_handoff_panel_for_public_user(self):
        response = self.client.get(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'WordPress handoff')

    def test_preview_page_shows_handoff_panel_for_staff_user(self):
        SiteHandoff.objects.create(
            site=self.site,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        ).refresh_payload()
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WordPress handoff')
        self.assertContains(response, 'Prepare / refresh handoff')
        self.assertContains(response, 'Open handoff in admin')

    def test_staff_preview_shows_staff_only_image_regenerate_button(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Try another hero photo')
        self.assertContains(response, 'Uses the built-in photo library. Add more images to the hero library for better choices.')

    def test_public_preview_hides_staff_only_image_regenerate_button(self):
        response = self.client.get(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Try another hero photo')

    def test_preview_page_renders_template_cards_instead_of_template_dropdown(self):
        response = self.client.get(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Classic Service Website')
        self.assertContains(response, 'Visual Hero Website')
        self.assertContains(response, 'Catalog / Multi-Service Website')
        self.assertNotContains(response, '<select id="template_slug"', html=False)

    def test_preview_editor_shows_image_selection_control(self):
        response = self.client.get(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hero image')
        self.assertContains(response, '<select id="content_', html=False)
        self.assertContains(response, 'Photo: Local service business photo')
        self.assertContains(response, 'site-editor-image-thumb')

    def test_saving_image_choice_persists_to_site_content(self):
        self.client.get(reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}))
        hero_image = SiteContent.objects.get(
            site=self.site,
            section_key='hero',
            field_key='hero_image',
            language='en',
        )

        response = self.client.post(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}),
            {
                f'content__{hero_image.id}': 'construction_01',
                'action': 'save',
            },
        )

        self.assertEqual(response.status_code, 302)
        hero_image.refresh_from_db()
        self.assertEqual(hero_image.value, 'construction_01')

    def test_regenerate_suggestions_does_not_overwrite_existing_selected_image(self):
        self.client.get(reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}))
        hero_image = SiteContent.objects.get(
            site=self.site,
            section_key='hero',
            field_key='hero_image',
            language='en',
        )
        hero_image.value = 'restaurant_01'
        hero_image.save(update_fields=['value', 'updated_at'])

        response = self.client.post(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}),
            {'action': 'regenerate'},
        )

        self.assertEqual(response.status_code, 302)
        hero_image.refresh_from_db()
        self.assertEqual(hero_image.value, 'restaurant_01')

    def test_text_regenerate_changes_at_least_one_text_value(self):
        self.client.get(reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}))
        hero_title = SiteContent.objects.get(
            site=self.site,
            section_key='hero',
            field_key='title',
            language='en',
        )
        original_title = hero_title.value

        response = self.client.post(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}),
            {'action': 'regenerate'},
        )

        self.assertEqual(response.status_code, 302)
        hero_title.refresh_from_db()
        self.assertNotEqual(hero_title.value, original_title)

    def test_text_regenerate_preserves_template_slug(self):
        self.site.template_slug = 'visual_hero'
        self.site.save(update_fields=['template_slug', 'updated_at'])

        response = self.client.post(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}),
            {'action': 'regenerate'},
        )

        self.assertEqual(response.status_code, 302)
        self.site.refresh_from_db()
        self.assertEqual(self.site.template_slug, 'visual_hero')

    def test_staff_only_regenerate_hero_image_changes_image_without_changing_text(self):
        self.client.get(reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}))
        self.client.force_login(self.staff_user)
        hero_image = SiteContent.objects.get(
            site=self.site,
            section_key='hero',
            field_key='hero_image',
            language='en',
        )
        hero_title = SiteContent.objects.get(
            site=self.site,
            section_key='hero',
            field_key='title',
            language='en',
        )
        original_title = hero_title.value
        original_image = hero_image.value

        response = self.client.post(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}),
            {'action': 'regenerate_hero_image'},
        )

        self.assertEqual(response.status_code, 302)
        hero_image.refresh_from_db()
        hero_title.refresh_from_db()
        self.assertNotEqual(hero_image.value, original_image)
        self.assertEqual(hero_title.value, original_title)

    def test_anonymous_cannot_use_staff_only_image_regeneration(self):
        self.client.get(reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}))

        response = self.client.post(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}),
            {'action': 'regenerate_hero_image'},
        )

        self.assertEqual(response.status_code, 403)

    def test_non_staff_cannot_use_staff_only_image_regeneration(self):
        self.client.get(reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}))
        self.client.force_login(self.regular_user)

        response = self.client.post(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id}),
            {'action': 'regenerate_hero_image'},
        )

        self.assertEqual(response.status_code, 403)

    def test_homepage_preview_path_shows_template_cards_and_start_links(self):
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Built to help customers find and contact you')
        self.assertNotContains(response, 'home-start-teaser-section', html=False)
        self.assertContains(response, reverse('ai_starter:start'))
        self.assertContains(response, 'Choose how you want to start')
        self.assertContains(response, 'Basic')
        self.assertContains(response, 'Growth')
        self.assertContains(response, 'Shop')
        self.assertContains(response, 'section-band', html=False)
        self.assertContains(response, 'section-inner', html=False)
        self.assertNotContains(response, 'preview-shell home-preview-workspace', html=False)
        self.assertNotContains(response, 'id="bizName"', html=False)

    def test_start_page_can_preselect_template_from_query_string(self):
        response = self.client.get(f"{reverse('ai_starter:start')}?template_slug=card_grid")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="card_grid"', html=False)
        self.assertNotContains(response, '<select id="template_slug"', html=False)

    def test_legacy_direct_post_fallback_still_works(self):
        response = self.client.post(
            reverse('ai_starter:start'),
            {
                'business_name': 'Legacy Flow Co',
                'service_type': 'Electrician',
                'city': 'Breda',
                'template_slug': 'classic_service',
            },
        )

        self.assertEqual(response.status_code, 302)
        site = Site.objects.latest('created_at')
        self.assertEqual(site.business_name, 'Legacy Flow Co')
        self.assertEqual(site.template_slug, 'classic_service')

    def test_payload_summary_renders_key_values(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            website_request=self.website_request,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        )
        handoff.refresh_payload()

        admin_instance = SiteHandoffAdmin(SiteHandoff, AdminSite())
        summary = admin_instance.payload_summary(handoff)
        pretty = admin_instance.pretty_payload(handoff)

        self.assertIn('Schema: 1', str(summary))
        self.assertIn(str(self.site.public_id), str(summary))
        self.assertIn('Northline Plumbing', str(summary))
        self.assertIn('Content rows: 2', str(summary))
        self.assertIn('Manual/empty target', str(summary))
        self.assertIn('&quot;business_name&quot;: &quot;Northline Plumbing&quot;', str(pretty))

    def test_request_contact_summary_helper_includes_contact_info_when_linked(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            website_request=self.website_request,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        )
        handoff.refresh_payload()

        admin_instance = SiteHandoffAdmin(SiteHandoff, AdminSite())
        request_summary = admin_instance.request_contact_summary(handoff)

        self.assertIn('Jane Owner', str(request_summary))
        self.assertIn('jane@example.com', str(request_summary))
        self.assertIn('northline.example.com', str(request_summary))
        self.assertIn('Open linked request in admin', str(request_summary))

    def test_site_admin_helpers_return_status_and_link_safely(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        )
        handoff.refresh_payload()

        admin_instance = SiteAdmin(Site, AdminSite())

        self.assertEqual(admin_instance.latest_wordpress_handoff_status(self.site), 'Prepared')
        self.assertIn('Open latest handoff', str(admin_instance.latest_wordpress_handoff_link(self.site)))

    @override_settings(OPENAI_API_KEY='', GOF_AI_ENABLED=False, GOF_AI_MODEL='gpt-4.1-mini')
    def test_ai_disabled_returns_fallback_brief(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            website_request=self.website_request,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        )
        handoff.refresh_payload()

        brief = generate_handoff_brief(handoff)

        self.assertIn('Business summary', brief)
        self.assertIn('Northline Plumbing', brief)
        self.assertIn('AI is not configured in Django yet', brief)

    def test_clean_assistant_output_removes_wrapping_code_fences(self):
        raw = "```markdown\nSuggested reply\n\nHello there\n```\n"

        cleaned = clean_assistant_output(raw)

        self.assertEqual(cleaned, 'Suggested reply\n\nHello there')

    @override_settings(OPENAI_API_KEY='', GOF_AI_ENABLED=False, GOF_AI_MODEL='gpt-4.1-mini')
    def test_generate_staff_ai_brief_stores_fallback_brief_and_timestamp(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            website_request=self.website_request,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        )
        handoff.refresh_payload()

        handoff.generate_staff_ai_brief()
        handoff.refresh_from_db()

        self.assertIn('Business summary', handoff.staff_ai_brief)
        self.assertIn('Northline Plumbing', handoff.staff_ai_brief)
        self.assertIsNotNone(handoff.staff_ai_brief_generated_at)
        self.assertEqual(handoff.staff_ai_brief_error, '')

    @override_settings(OPENAI_API_KEY='', GOF_AI_ENABLED=False, GOF_AI_MODEL='gpt-4.1-mini')
    def test_admin_action_can_generate_staff_brief_without_api_key(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            website_request=self.website_request,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        )
        handoff.refresh_payload()

        request = RequestFactory().post('/admin/ai_starter/sitehandoff/')
        request.user = self.staff_user

        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))

        model_admin = SiteHandoffAdmin(SiteHandoff, AdminSite())
        model_admin.generate_staff_ai_handoff_brief(request, SiteHandoff.objects.filter(pk=handoff.pk))

        handoff.refresh_from_db()
        self.assertIn('Business summary', handoff.staff_ai_brief)
        self.assertIsNotNone(handoff.staff_ai_brief_generated_at)

    @override_settings(OPENAI_API_KEY='super-secret-key', GOF_AI_ENABLED=True, GOF_AI_MODEL='gpt-4.1-mini')
    def test_preview_page_for_staff_shows_ai_brief_status_without_exposing_api_key(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        )
        handoff.refresh_payload()
        handoff.staff_ai_brief = 'Business summary\n- Internal brief'
        handoff.staff_ai_brief_generated_at = handoff.updated_at
        handoff.save(update_fields=['staff_ai_brief', 'staff_ai_brief_generated_at', 'updated_at'])

        self.client.force_login(self.staff_user)
        response = self.client.get(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI brief')
        self.assertContains(response, 'Generated')
        self.assertNotContains(response, 'super-secret-key')
        self.assertNotContains(response, 'OPENAI_API_KEY')

    def test_anonymous_cannot_access_staff_handoffs_dashboard(self):
        response = self.client.get(reverse('ai_starter:staff_handoffs'))

        self.assertEqual(response.status_code, 403)

    def test_non_staff_user_cannot_access_staff_handoffs_dashboard(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse('ai_starter:staff_handoffs'))

        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_access_staff_handoffs_dashboard(self):
        SiteHandoff.objects.create(
            site=self.site,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        ).refresh_payload()
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_handoffs'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff handoff dashboard')

    def test_staff_dashboard_lists_a_handoff(self):
        SiteHandoff.objects.create(
            site=self.site,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        ).refresh_payload()
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_handoffs'))

        self.assertContains(response, 'Northline Plumbing')
        self.assertContains(response, 'Open preview')

    def test_staff_dashboard_shows_request_contact_summary_when_linked(self):
        SiteHandoff.objects.create(
            site=self.site,
            website_request=self.website_request,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        ).refresh_payload()
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_handoffs'))

        self.assertContains(response, 'Jane Owner')
        self.assertContains(response, 'jane@example.com')
        self.assertContains(response, 'Needs domain help')
        self.assertContains(response, 'GEMEENTE50')

    def test_staff_dashboard_shows_no_request_linked_when_absent(self):
        SiteHandoff.objects.create(
            site=self.site,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        ).refresh_payload()
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_handoffs'))

        self.assertContains(response, 'No request linked')

    def test_staff_dashboard_post_prepare_refresh_handoff_refreshes_payload_and_status(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            status=SiteHandoff.Status.FAILED,
            prepared_by=self.staff_user,
        )
        self.client.force_login(self.staff_user)
        SiteContent.objects.filter(site=self.site, section_key='hero', field_key='title').update(
            value='Fresh payload title'
        )

        response = self.client.post(
            reverse('ai_starter:staff_handoffs'),
            {'handoff_id': handoff.id, 'action': 'prepare_refresh_handoff'},
        )

        self.assertEqual(response.status_code, 302)
        handoff.refresh_from_db()
        self.assertEqual(handoff.status, SiteHandoff.Status.PREPARED)
        hero_entry = next(
            item for item in handoff.handoff_payload['content']
            if item['section_key'] == 'hero' and item['field_key'] == 'title'
        )
        self.assertEqual(hero_entry['value'], 'Fresh payload title')

    @override_settings(OPENAI_API_KEY='', GOF_AI_ENABLED=False, GOF_AI_MODEL='gpt-4.1-mini')
    def test_staff_dashboard_post_generate_ai_brief_stores_fallback_brief(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            website_request=self.website_request,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        )
        handoff.refresh_payload()
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('ai_starter:staff_handoffs'),
            {'handoff_id': handoff.id, 'action': 'generate_ai_brief'},
        )

        self.assertEqual(response.status_code, 302)
        handoff.refresh_from_db()
        self.assertIn('Business summary', handoff.staff_ai_brief)
        self.assertIsNotNone(handoff.staff_ai_brief_generated_at)

    def test_staff_dashboard_post_mark_completed_marks_completed(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        )
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('ai_starter:staff_handoffs'),
            {'handoff_id': handoff.id, 'action': 'mark_completed'},
        )

        self.assertEqual(response.status_code, 302)
        handoff.refresh_from_db()
        self.assertEqual(handoff.status, SiteHandoff.Status.COMPLETED)
        self.assertIsNotNone(handoff.completed_at)

    @override_settings(OPENAI_API_KEY='super-secret-key', GOF_AI_ENABLED=True, GOF_AI_MODEL='gpt-4.1-mini')
    def test_staff_dashboard_does_not_expose_openai_api_key(self):
        SiteHandoff.objects.create(
            site=self.site,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        ).refresh_payload()
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_handoffs'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'super-secret-key')
        self.assertNotContains(response, 'OPENAI_API_KEY')

    def test_staff_dashboard_uses_internal_layout_without_public_footer_copy(self):
        SiteHandoff.objects.create(
            site=self.site,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        ).refresh_payload()
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_handoffs'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Get Online Fast Staff')
        self.assertContains(response, 'View public site')
        self.assertNotContains(response, 'All rights reserved.')
        self.assertNotContains(response, 'Just Code Works platform')

    def test_anonymous_user_is_redirected_from_dashboard_domain_information_page(self):
        response = self.client.get(reverse('core:dashboard_domain_information'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_logged_in_user_can_access_dashboard_domain_information_page(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse('core:dashboard_domain_information'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Domain information')
        self.assertContains(response, 'Managed by')
        self.assertContains(response, 'Get Online Fast')
        self.assertContains(response, 'Available after payment/settlement where applicable')
        self.assertContains(response, 'This does not include website migration, email setup, DNS setup with another provider, or technical support for another provider.')
        self.assertContains(response, 'Continue website package')
        self.assertContains(response, 'View payment/settlement information')
        self.assertContains(response, 'Contact support')
        self.assertContains(response, 'noindex, nofollow')

    def test_staff_link_appears_in_public_header_for_staff_user(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('ai_starter:staff_handoffs'))
        self.assertContains(response, '>Staff<', html=False)

    def test_staff_link_does_not_appear_in_public_header_for_anonymous_user(self):
        response = self.client.get(
            reverse('ai_starter:preview', kwargs={'public_id': self.site.public_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('ai_starter:staff_handoffs'))

    def test_staff_root_redirects_to_handoffs_for_staff_user(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_root'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], reverse('ai_starter:staff_handoffs'))

    def test_staff_root_denies_anonymous_user(self):
        response = self.client.get(reverse('ai_starter:staff_root'))

        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_access_staff_template_wireframes(self):
        response = self.client.get(reverse('ai_starter:staff_template_wireframes'))

        self.assertEqual(response.status_code, 403)

    def test_non_staff_cannot_access_staff_template_wireframes(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse('ai_starter:staff_template_wireframes'))

        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_staff_template_wireframes(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_template_wireframes'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Template Wireframe Lab')
        self.assertContains(response, 'Preview reusable layout structures before final styling.')

    def test_staff_template_wireframes_page_includes_base_layouts_and_variants(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_template_wireframes'))

        self.assertContains(response, 'Boxed service layout')
        self.assertContains(response, 'Full-width visual layout')
        self.assertContains(response, 'Mixed layout')
        self.assertContains(response, 'hero_split')
        self.assertContains(response, 'services_icon_cards')
        self.assertContains(response, 'cta_full_width_band')

    def test_staff_nav_includes_wireframes_link_on_staff_pages(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_assistant'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('ai_starter:staff_template_wireframes'))
        self.assertContains(response, '>Wireframes<', html=False)

    def test_anonymous_cannot_access_staff_assistant(self):
        response = self.client.get(reverse('ai_starter:staff_assistant'))

        self.assertEqual(response.status_code, 403)

    def test_non_staff_cannot_access_staff_assistant(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse('ai_starter:staff_assistant'))

        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_staff_assistant(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_assistant'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff assistant')

    def test_staff_assistant_page_includes_form(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_assistant'))

        self.assertContains(response, 'customer_message')
        self.assertContains(response, 'Draft reply')
        self.assertContains(response, 'Try a demo message')
        self.assertContains(response, 'Tenho uma oficina e preciso de um website, mas nÃ£o sei bem o que preciso.')
        self.assertContains(response, 'Queria saber se conseguem criar um assistente AI para responder a clientes.')

    def test_infer_recommended_setup_for_garage_message(self):
        recommendation = infer_recommended_website_setup('Tenho uma oficina e preciso de um website, mas nÃ£o sei bem o que preciso.')

        self.assertIn('garage', recommendation['recommended_setup_label'].lower())
        self.assertTrue(any('quote' in item.lower() or 'contact' in item.lower() for item in recommendation['recommended_features']))

    def test_infer_recommended_setup_for_printing_message(self):
        recommendation = infer_recommended_website_setup('Tenho uma grÃ¡fica e queria receber pedidos de orÃ§amento pelo site.')

        self.assertIn('printing', recommendation['recommended_setup_label'].lower())
        self.assertTrue(any('quote' in item.lower() for item in recommendation['recommended_features'] + recommendation['recommended_pages_or_sections']))

    def test_infer_recommended_setup_for_shop_message_prefers_catalog_first(self):
        recommendation = infer_recommended_website_setup('Tenho uma loja pequena e queria mostrar produtos online, talvez vender mais tarde.')

        self.assertTrue('catalog' in recommendation['recommended_setup_label'].lower() or 'product' in recommendation['recommended_setup_label'].lower())
        self.assertFalse(recommendation['recommended_setup_label'].lower().startswith('ecommerce'))

    def test_infer_recommended_setup_for_ai_assistant_message_uses_manual_review_positioning(self):
        recommendation = infer_recommended_website_setup('Queria saber se conseguem criar um assistente AI para responder a clientes.')

        self.assertIn('ai reply assistant', recommendation['recommended_setup_label'].lower())
        self.assertTrue(any('manual review' in item.lower() or 'draft replies' in item.lower() for item in recommendation['recommended_features']))

    def test_infer_recommended_setup_for_unknown_business_uses_safe_default(self):
        recommendation = infer_recommended_website_setup('I need a website for my small business but I am not sure what I need.')

        self.assertIn('local service website', recommendation['recommended_setup_label'].lower())

    @override_settings(OPENAI_API_KEY='', GOF_AI_ENABLED=False, GOF_AI_MODEL='gpt-4.1-mini')
    def test_staff_assistant_post_returns_fallback_draft_without_api_key(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('ai_starter:staff_assistant'),
            {
                'customer_message': 'Ola, gostaria de saber mais sobre o website.',
                'reply_language': 'Portuguese',
                'reply_tone': 'friendly_professional',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Suggested reply')
        self.assertContains(response, 'Internal notes for staff')
        self.assertContains(response, 'Nothing was sent automatically')
        self.assertContains(response, 'Review before sending. Nothing was sent automatically.')
        self.assertContains(response, 'Recommended setup')
        self.assertContains(response, 'Why this recommendation was made')

    @override_settings(OPENAI_API_KEY='', GOF_AI_ENABLED=False, GOF_AI_MODEL='gpt-4.1-mini')
    def test_staff_assistant_ai_request_positions_early_access_manual_review(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('ai_starter:staff_assistant'),
            {
                'customer_message': 'Queria saber se conseguem criar um assistente AI para responder a clientes.',
                'reply_language': 'Portuguese',
                'reply_tone': 'friendly_professional',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Reply Assistant early-access add-on')
        self.assertContains(response, 'revisÃ£o manual')
        self.assertContains(response, 'Review before sending')

    @override_settings(OPENAI_API_KEY='', GOF_AI_ENABLED=False, GOF_AI_MODEL='gpt-4.1-mini')
    def test_staff_assistant_result_page_does_not_show_markdown_code_fences(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('ai_starter:staff_assistant'),
            {
                'customer_message': '```markdown\nOlÃ¡, podem ajudar?\n```',
                'reply_language': 'Portuguese',
                'reply_tone': 'friendly_professional',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '```markdown')

    @override_settings(OPENAI_API_KEY='', GOF_AI_ENABLED=False, GOF_AI_MODEL='gpt-4.1-mini')
    def test_staff_assistant_post_with_selected_handoff_includes_context_and_does_not_crash(self):
        handoff = SiteHandoff.objects.create(
            site=self.site,
            website_request=self.website_request,
            status=SiteHandoff.Status.PREPARED,
            prepared_by=self.staff_user,
        )
        handoff.refresh_payload()
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('ai_starter:staff_assistant'),
            {
                'handoff_id': handoff.id,
                'customer_message': 'Can you tell me what you need from us to continue?',
                'reply_language': 'English',
                'reply_tone': 'support_helpful',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Suggested reply')
        self.assertContains(response, 'Northline Plumbing')
        self.assertContains(response, 'Jane Owner')
        self.assertContains(response, 'Recommended setup')

    @override_settings(OPENAI_API_KEY='super-secret-key', GOF_AI_ENABLED=True, GOF_AI_MODEL='gpt-4.1-mini')
    def test_staff_assistant_result_does_not_expose_openai_api_key(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('ai_starter:staff_assistant'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'super-secret-key')
        self.assertNotContains(response, 'OPENAI_API_KEY')

    @override_settings(OPENAI_API_KEY='', GOF_AI_ENABLED=False, GOF_AI_MODEL='gpt-4.1-mini')
    def test_staff_assistant_does_not_touch_wordpress_files(self):
        plugin_file = Path(self.site._meta.apps.get_app_config('ai_starter').path).parent / (
            'jcw-wp-current/wp-content/plugins/jcw-ai-assistant/jcw-ai-assistant.php'
        )
        plugin_mtime_before = plugin_file.stat().st_mtime
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('ai_starter:staff_assistant'),
            {
                'customer_message': 'Please send me more info.',
                'reply_language': 'English',
                'reply_tone': 'short_direct',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(plugin_file.stat().st_mtime, plugin_mtime_before)


class ProjectAssetHelperTests(TestCase):
    def setUp(self):
        self.project_slug = 'axial-pagina-test'
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_project_asset_root = project_assets_module.PROJECT_ASSET_ROOT
        project_assets_module.PROJECT_ASSET_ROOT = Path(self.temp_dir.name)
        self.project_dir = project_assets_module.PROJECT_ASSET_ROOT / self.project_slug

    def tearDown(self):
        project_assets_module.PROJECT_ASSET_ROOT = self.original_project_asset_root
        self.temp_dir.cleanup()

    def test_normalize_project_slug_accepts_safe_slugs(self):
        self.assertEqual(normalize_project_slug('Axial Pagina'), 'axial-pagina')
        self.assertEqual(normalize_project_slug('axial-pagina'), 'axial-pagina')
        self.assertEqual(normalize_project_slug('Axial PÃ¡gina'), 'axial-pagina')

    def test_normalize_project_slug_rejects_unsafe_values(self):
        self.assertEqual(normalize_project_slug('../secrets'), '')
        self.assertEqual(normalize_project_slug('..\\secrets'), '')
        self.assertEqual(normalize_project_slug(''), '')
        self.assertEqual(normalize_project_slug('////'), '')

    def test_invalid_asset_types_are_rejected(self):
        with self.assertRaises(ValueError):
            list_project_assets('axial-pagina', 'downloads')

    def test_list_project_assets_returns_empty_list_when_folder_has_no_images(self):
        hero_dir = self.project_dir / 'hero'
        hero_dir.mkdir(parents=True, exist_ok=True)
        (hero_dir / '.gitkeep').write_text('', encoding='utf-8')

        self.assertEqual(list_project_assets(self.project_slug, 'hero'), [])

    def test_helper_finds_safe_image_and_builds_url(self):
        hero_dir = self.project_dir / 'hero'
        hero_dir.mkdir(parents=True, exist_ok=True)
        (hero_dir / 'hero-01.jpg').write_bytes(b'test-image')
        (hero_dir / 'notes.txt').write_text('ignore', encoding='utf-8')

        assets = list_project_assets(self.project_slug, 'hero')
        first_asset = get_first_project_asset(self.project_slug, 'hero')
        asset_url = get_project_asset_url(self.project_slug, 'hero', 'hero-01.jpg')

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]['filename'], 'hero-01.jpg')
        self.assertTrue(assets[0]['static_path'].endswith('axial-pagina-test/hero/hero-01.jpg'))
        self.assertEqual(assets[0]['relative_path'], 'template-assets/axial-pagina-test/hero/hero-01.jpg')
        self.assertIsNotNone(first_asset)
        self.assertEqual(first_asset['filename'], 'hero-01.jpg')
        self.assertEqual(first_asset['relative_path'], 'template-assets/axial-pagina-test/hero/hero-01.jpg')
        self.assertTrue(asset_url.endswith('/static/core/img/template-assets/axial-pagina-test/hero/hero-01.jpg'))

    def test_invalid_filename_or_missing_file_returns_empty_url(self):
        hero_dir = self.project_dir / 'hero'
        hero_dir.mkdir(parents=True, exist_ok=True)
        (hero_dir / 'hero-01.jpg').write_bytes(b'test-image')

        self.assertEqual(get_project_asset_url(self.project_slug, 'hero', '../hero-01.jpg'), '')
        self.assertEqual(get_project_asset_url(self.project_slug, 'hero', 'missing.jpg'), '')


class PublicInformationPageTests(TestCase):
    def test_homepage_is_indexable_and_has_meta_description(self):
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'noindex, nofollow')
        self.assertContains(response, '<meta name="description"', html=False)

    def test_examples_page_uses_starting_layout_language_and_stays_indexable(self):
        response = self.client.get(reverse('core:examples'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'noindex, nofollow')
        self.assertContains(response, 'Choose a starting layout before you start')
        self.assertContains(response, 'Starting layouts')
        self.assertContains(response, 'Start with this layout')
        self.assertContains(response, 'Choose this layout')
        self.assertContains(response, 'Layout direction only.')
        self.assertContains(response, reverse('ai_starter:start'))
        self.assertNotContains(response, 'Use this template')
        self.assertNotContains(response, 'Request this style')
        self.assertNotContains(response, 'Design examples')

    def test_public_navigation_hides_examples_link(self):
        home_response = self.client.get(reverse('core:home'))
        footer_response = self.client.get(reverse('core:terms'))

        self.assertEqual(home_response.status_code, 200)
        self.assertEqual(footer_response.status_code, 200)
        self.assertNotContains(home_response, f'href="{reverse("core:examples")}"', html=False)
        self.assertNotContains(footer_response, f'href="{reverse("core:examples")}"', html=False)

    def test_how_it_works_page_shows_included_launch_boost_block(self):
        response = self.client.get(reverse('core:how_it_works'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A practical path to launch')
        self.assertContains(response, 'Included launch boost')
        self.assertContains(response, 'Initial Facebook launch posts included during the first month')
        self.assertContains(response, 'This refers to launch post content only, not paid Facebook Ads budget')

    def test_public_information_pages_return_200_and_do_not_use_noindex(self):
        page_urls = [
            reverse('core:terms'),
            reverse('core:privacy_policy'),
            reverse('core:cookie_policy'),
            reverse('core:what_is_included'),
            reverse('core:payment_and_cancellation'),
            reverse('core:domain_hosting_and_dashboard'),
            reverse('core:addons_and_upgrades'),
            reverse('core:preview_licence'),
        ]

        for url in page_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertNotContains(response, 'noindex, nofollow')

    def test_home_footer_includes_public_information_links(self):
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('core:terms'))
        self.assertContains(response, reverse('core:privacy_policy'))
        self.assertContains(response, reverse('core:cookie_policy'))
        self.assertContains(response, reverse('core:what_is_included'))
        self.assertContains(response, reverse('core:payment_and_cancellation'))

    def test_public_information_pages_do_not_publish_private_address(self):
        response = self.client.get(reverse('core:terms'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A public business address will be added here later when the official virtual address is active.')
        self.assertNotContains(response, 'Joao')

    def test_payment_and_cancellation_page_includes_withdrawal_wording(self):
        response = self.client.get(reverse('core:payment_and_cancellation'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '14-day withdrawal or cooling-off period')
        self.assertContains(response, 'This page is practical guidance only and is not legal advice.')

    def test_preview_licence_page_explains_preview_ownership_rules(self):
        response = self.client.get(reverse('core:preview_licence'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'remain owned or licensed by Just Code Works / Get Online Fast')
        self.assertContains(response, 'Copying preview text, layouts, images, structures, or demo assets for public use without permission or payment is not allowed.')

    def test_public_pages_meta_and_footer_links_render(self):
        response = self.client.get(reverse('core:privacy_policy'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta name="description"', html=False)
        self.assertContains(response, reverse('core:what_is_included'))
        self.assertContains(response, reverse('core:payment_and_cancellation'))


class PublicContactPageTests(TestCase):
    def _contact_answer(self):
        self.client.get(reverse('core:contact'))
        session = self.client.session
        return str(session.get('contact_captcha_answer', '')).strip()

    def test_contact_page_renders_public_form_and_fallback_email(self):
        response = self.client.get(reverse('core:contact'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Send a message')
        self.assertContains(response, 'info@getonlinefast.eu')
        self.assertNotContains(response, 'noindex, nofollow')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='launch@test.example',
        CONTACT_EMAIL_TO='info@getonlinefast.eu',
    )
    def test_contact_form_sends_email_and_shows_success_message(self):
        answer = self._contact_answer()

        response = self.client.post(
            reverse('core:contact'),
            {
                'name': 'Taylor Visitor',
                'email': 'taylor@example.com',
                'phone': '+31612345678',
                'message': 'I would like to know which package fits my business.',
                'security_question': answer,
                'honeypot': '',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your message was sent successfully. We will get back to you soon.')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['info@getonlinefast.eu'])
        self.assertIn('Taylor Visitor', mail.outbox[0].body)
        self.assertIn('I would like to know which package fits my business.', mail.outbox[0].body)

    def test_contact_form_validation_error_is_shown_for_wrong_security_answer(self):
        self._contact_answer()

        response = self.client.post(
            reverse('core:contact'),
            {
                'name': 'Taylor Visitor',
                'email': 'taylor@example.com',
                'phone': '',
                'message': 'Please contact me.',
                'security_question': 'wrong',
                'honeypot': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please answer the security question correctly.')
        self.assertContains(response, 'Please correct the errors below and try again.')

    @patch('core.views.EmailMessage.send', side_effect=Exception('mail failed'))
    def test_contact_form_handles_email_failure_without_crashing(self, mocked_send):
        answer = self._contact_answer()

        response = self.client.post(
            reverse('core:contact'),
            {
                'name': 'Taylor Visitor',
                'email': 'taylor@example.com',
                'phone': '',
                'message': 'Please contact me.',
                'security_question': answer,
                'honeypot': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your message could not be sent right now. Please try again or contact us directly by email.')
        mocked_send.assert_called_once()


class WebsitePackagePaymentPageTests(TestCase):
    def test_payment_confirmation_route_returns_200(self):
        response = self.client.get(reverse('core:payment'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Complete your website activation')
        self.assertContains(response, 'Continue to secure payment')
        self.assertContains(response, 'noindex, nofollow')

    def test_payment_confirmation_page_contains_required_checkbox_texts(self):
        response = self.client.get(reverse('core:payment'))

        self.assertContains(response, 'I confirm that I am authorised to approve and pay for this website setup.')
        self.assertContains(response, 'I understand what is included in this website setup.')
        self.assertContains(response, 'I understand that custom changes outside the agreed setup may be quoted or billed separately.')
        self.assertContains(response, 'I understand that the website uses WordPress together with the Get Online Fast / JCW website tools and theme setup.')
        self.assertContains(response, 'I confirm that the content, images, logo and materials I provide may legally be used on my website.')
        self.assertContains(response, 'I have read and agree to the')

    def test_payment_confirmation_page_contains_required_legal_links(self):
        response = self.client.get(reverse('core:payment'))

        self.assertContains(response, reverse('core:terms'))
        self.assertContains(response, reverse('core:privacy_policy'))

    def test_payment_confirmation_page_contains_helpful_links(self):
        response = self.client.get(reverse('core:payment'))

        self.assertContains(response, reverse('core:support'))
        self.assertContains(response, reverse('core:terms'))
        self.assertContains(response, reverse('core:privacy_policy'))

    @override_settings(GETONLINEFAST_WEBSITE_PACKAGE_PAYMENT_URL='')
    def test_payment_confirmation_page_shows_safe_message_when_payment_url_missing(self):
        response = self.client.get(reverse('core:payment'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment link is not configured yet. Please contact')
        self.assertContains(response, 'disabled')

    @override_settings(GETONLINEFAST_WEBSITE_PACKAGE_PAYMENT_URL='https://buy.stripe.test/example')
    def test_payment_confirmation_page_renders_post_flow_when_payment_url_configured(self):
        response = self.client.get(reverse('core:payment'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Payment link is not configured yet. Please contact')
        self.assertContains(response, 'data-payment-confirmation-form')
        self.assertContains(response, 'data-payment-configured="true"')

    @override_settings(GETONLINEFAST_WEBSITE_PACKAGE_PAYMENT_URL='https://buy.stripe.test/example')
    def test_payment_confirmation_post_redirects_when_all_checks_are_submitted(self):
        response = self.client.post(
            reverse('core:payment'),
            {
                'confirm_authorised_payment': 'on',
                'confirm_included_scope': 'on',
                'confirm_custom_changes': 'on',
                'confirm_platform_basis': 'on',
                'confirm_content_rights': 'on',
                'confirm_legal_pages': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://buy.stripe.test/example')

    @override_settings(GETONLINEFAST_WEBSITE_PACKAGE_PAYMENT_URL='https://buy.stripe.test/example')
    def test_payment_confirmation_post_requires_all_checkboxes(self):
        response = self.client.post(
            reverse('core:payment'),
            {
                'confirm_authorised_payment': 'on',
                'confirm_included_scope': 'on',
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Please confirm all required points before continuing to secure payment.', status_code=400)

    def test_new_handoff_routes_return_200(self):
        self.assertEqual(self.client.get(reverse('core:after_payment')).status_code, 200)
        self.assertEqual(self.client.get(reverse('core:support')).status_code, 200)
        self.assertEqual(self.client.get(reverse('core:terms')).status_code, 200)
        self.assertEqual(self.client.get(reverse('core:privacy_policy')).status_code, 200)

    def test_robots_txt_lists_sitemap_and_disallows_payment_step(self):
        response = self.client.get('/robots.txt')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sitemap:')
        self.assertContains(response, '/en/payment/')
        self.assertContains(response, '/en/pay/website-package/')

    def test_sitemap_xml_lists_public_pages_and_excludes_payment_step(self):
        response = self.client.get('/sitemap.xml')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('core:home'))
        self.assertContains(response, reverse('core:support'))
        self.assertContains(response, reverse('core:terms'))
        self.assertNotContains(response, reverse('core:payment'))

