from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class VendorReviewsConfig(AppConfig):
    label = 'reviews'
    name = 'oscar.apps.customer.reviews'
    verbose_name = _('Vendor reviews')
