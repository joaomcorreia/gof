from django.core.management.commands.makemessages import Command as DjangoMakeMessagesCommand


class Command(DjangoMakeMessagesCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.set_defaults(no_location=True)
