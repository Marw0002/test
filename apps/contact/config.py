from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ContactConfig(AppConfig):
    label = 'contact'
    name = 'oscar.apps.contact'
    verbose_name = _('contact')
