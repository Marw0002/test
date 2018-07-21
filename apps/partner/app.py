from django.conf.urls import url
from django.views import generic

from oscar.core.application import Application
from oscar.core.loading import get_class


class PartnerApplication(Application):
    name = 'partner'

    vendor_view = get_class('partner.views', 'VendorView')	

    def get_urls(self):
        urls = [

            url(r'^$',
                self.vendor_view.as_view(),
                name='vendor-list')]

        return self.post_process_urls(urls)

application = PartnerApplication()
