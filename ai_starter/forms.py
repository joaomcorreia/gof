from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class StarterOnboardingForm(forms.Form):
    business_name = forms.CharField(label=_('Business name'), max_length=120)
    service_type = forms.CharField(label=_('Service type'), max_length=120)
    city = forms.CharField(label=_('City'), max_length=120)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            if not data:
                return []
            return [single_file_clean(item, initial) for item in data]

        result = single_file_clean(data, initial)
        return [result] if result else []


class WebsiteRequestForm(forms.Form):
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'pdf', 'doc', 'docx'}
    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_TOTAL_SIZE = 40 * 1024 * 1024

    business_name = forms.CharField(label=_('Business name'), max_length=120)
    business_type = forms.CharField(label=_('Business type'), max_length=120)
    existing_website_url = forms.URLField(label=_('Existing website URL'), required=False)
    current_domain = forms.CharField(label=_('Current domain'), max_length=255, required=False)
    needs_domain_help = forms.TypedChoiceField(
        label=_('Need help with domain setup?'),
        choices=((True, _('Yes')), (False, _('No'))),
        coerce=lambda value: str(value).lower() in {'1', 'true', 'yes'},
        empty_value=False,
        widget=forms.Select,
    )
    business_address = forms.CharField(label=_('Business address'), max_length=255, required=False)
    service_area = forms.CharField(label=_('Service area'), max_length=255, required=False)
    main_language = forms.ChoiceField(label=_('Main language'), choices=settings.LANGUAGES)
    extra_languages = forms.CharField(label=_('Extra languages'), max_length=255, required=False)
    contact_name = forms.CharField(label=_('Contact name'), max_length=120)
    contact_email = forms.EmailField(label=_('Contact email'))
    contact_phone = forms.CharField(label=_('Contact phone'), max_length=40, required=False)
    contact_whatsapp = forms.CharField(label=_('Contact WhatsApp'), max_length=40, required=False)
    main_services = forms.CharField(label=_('Main services'), widget=forms.Textarea)
    business_description = forms.CharField(label=_('Business description'), required=False, widget=forms.Textarea)
    opening_hours = forms.CharField(label=_('Opening hours'), max_length=255, required=False)
    social_links = forms.CharField(label=_('Social links'), required=False, widget=forms.Textarea)
    preferred_colors = forms.CharField(label=_('Preferred colors'), max_length=255, required=False)
    style_notes = forms.CharField(label=_('Style notes'), required=False, widget=forms.Textarea)
    special_requests = forms.CharField(label=_('Special requests'), required=False, widget=forms.Textarea)
    supporting_files = MultipleFileField(
        label=_('Logo, photos, and useful files'),
        required=False,
        widget=MultipleFileInput(attrs={'accept': '.jpg,.jpeg,.png,.webp,.pdf,.doc,.docx'}),
        help_text=_('Allowed: jpg, jpeg, png, webp, pdf, doc, docx. Max 10MB each, 40MB total.'),
    )
    request_acknowledgement = forms.BooleanField(
        label=_('I understand this is a request and Get Online Fast will contact me before starting.'),
        required=True,
    )

    def clean_supporting_files(self):
        files = self.cleaned_data.get('supporting_files') or []
        total_size = 0

        for upload in files:
            extension = upload.name.rsplit('.', 1)[-1].lower() if '.' in upload.name else ''
            if extension not in self.ALLOWED_EXTENSIONS:
                raise forms.ValidationError(_('Unsupported file type: %(name)s') % {'name': upload.name})

            if upload.size > self.MAX_FILE_SIZE:
                raise forms.ValidationError(_('File exceeds 10MB: %(name)s') % {'name': upload.name})

            total_size += upload.size

        if total_size > self.MAX_TOTAL_SIZE:
            raise forms.ValidationError(_('Total upload size cannot exceed 40MB.'))

        return files
