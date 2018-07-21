from __future__ import unicode_literals
from django.conf.urls import url

from .views import BlogView
from oscar.core.application import Application


class BlogApplication(Application):
    name = 'article'

    def get_urls(self):
        urls = [
            url(r'^$', BlogView.as_view(), {}, 'article'),
			
        ]
        return self.post_process_urls(urls)


application = BlogApplication()

