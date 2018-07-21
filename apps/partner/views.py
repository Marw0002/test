from django import http
from django.conf import settings
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site

from django.core.urlresolvers import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.views import generic

from oscar.core.loading import get_model


Company = get_model('customer','Company')


class VendorView(generic.TemplateView):
    """
    Browse all vendor
    """
    template_name = 'partner/browse.html'

    def get(self, request, *args, **kwargs):

        return super(VendorView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = {}
        ctx['companies']= Company.objects.filter(is_vendor=True)		
        ctx['active_tab']='all_vendors'       	
        return ctx
