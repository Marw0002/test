from django.conf.urls import url
from django.views.generic import RedirectView

from oscar.core.application import Application

class PromotionsApplication(Application):
    name = 'promotions'

    def get_urls(self):
        urls = [
            url(r'^$', RedirectView.as_view(url='/ideas/'), name='home'),
        ]
        return self.post_process_urls(urls)


application = PromotionsApplication()
