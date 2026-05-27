from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class PrintDesignAccessTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username='staff-user',
            password='test-pass-123',
            is_staff=True,
        )
        self.regular_user = user_model.objects.create_user(
            username='regular-user',
            password='test-pass-123',
        )

    def test_anonymous_user_is_redirected_to_admin_login(self):
        response = self.client.get(reverse('print_design:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_regular_user_is_redirected_to_admin_login(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('print_design:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_staff_user_can_access_index(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('print_design:index'))
        self.assertEqual(response.status_code, 200)

    def test_staff_user_can_access_service_detail(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('print_design:service_detail', kwargs={'service_slug': 'flyers'}))
        self.assertEqual(response.status_code, 200)
