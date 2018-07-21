from __future__ import unicode_literals
from django.conf.urls import url
from django.views.generic import TemplateView

from .views import ContactUsView, ContactVendorView
from oscar.core.application import Application


class ContactApplication(Application):
    name = 'contact'

    def get_urls(self):
        urls = [
            url(r'^$', ContactUsView.as_view(), {}, 'contactus'),
            url(r'^success/$', TemplateView.as_view(
                template_name='contactus/contact_success.html'),
                {}, 'contactus-success'),
            url(r'^(?P<company_slug>[\w-]*)_(?P<pk>\d+)/$', ContactVendorView.as_view(), {}, 'contactvendor'),		
        ]
        return self.post_process_urls(urls)


application = ContactApplication()

