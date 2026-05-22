from django import forms
from django.utils.translation import gettext_lazy as _


class ContactForm(forms.Form):
    name = forms.CharField(label=_('Name'), max_length=120)
    email = forms.EmailField(label=_('Email'))
    phone = forms.CharField(label=_('Phone (optional)'), max_length=50, required=False)
    message = forms.CharField(label=_('Message'), widget=forms.Textarea(attrs={'rows': 6}))
    security_question = forms.CharField(label=_('Security question'), max_length=20)
    honeypot = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_honeypot(self):
        value = self.cleaned_data.get('honeypot', '').strip()
        if value:
            raise forms.ValidationError(_('Invalid submission.'))
        return value
