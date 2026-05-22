from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Send a basic test email using the configured Django email backend.'

    def add_arguments(self, parser):
        parser.add_argument('recipient', help='Recipient email address')

    def handle(self, *args, **options):
        recipient = options['recipient']

        try:
            sent_count = send_mail(
                subject='Get Online Fast email test',
                message='This is a test email sent by Django for Get Online Fast.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f'Email send failed: {exc}') from exc

        if sent_count != 1:
            raise CommandError(f'Email send failed: expected 1 email, sent {sent_count}.')

        self.stdout.write(self.style.SUCCESS(f'Test email sent successfully to {recipient}.'))
