from __future__ import unicode_literals

from django.template import loader
from django.views.generic import TemplateView



class BlogView(TemplateView):
    template_name = 'article.html'		