from django import forms
from django.utils.translation import gettext_lazy as _


class StarterOnboardingForm(forms.Form):
    business_name = forms.CharField(label=_('Business name'), max_length=120)
    service_type = forms.CharField(label=_('Service type'), max_length=120)
    city = forms.CharField(label=_('City'), max_length=120)
