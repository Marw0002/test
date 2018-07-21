from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ArticleConfig(AppConfig):
    label = 'article'
    name = 'oscar.apps.article'
    verbose_name = _('article')
