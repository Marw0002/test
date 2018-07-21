from django import template

from oscar.core.compat import assignment_tag
from oscar.core.loading import get_model

Theme = get_model('catalogue', 'ProjectTheme')
register = template.Library()

@register.inclusion_tag('oscar/catalogue/browse.html')
def get_category_list():
    return {'themes': Theme.objects.all()}

#assignment_tag = assignment_tag(register)

