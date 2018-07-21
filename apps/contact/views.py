from __future__ import unicode_literals

from django.conf import settings
from django.core.mail import send_mail
from django.template import loader
from django.views.generic.edit import FormView

from oscar.apps.contact.form import ContactUsForm, ContactVendorForm, SUBJECT_CHOICES

from oscar.core.loading import get_model

class ContactUsView(FormView):
    template_name = 'contact/contact.html'
    email_template_name = 'contact/contact_notification_email.txt'
    form_class = ContactUsForm
    success_url = "/contact/success/"
    subject = "Contact Us Request"

    def get_initial(self):
        initial = super(ContactUsView, self).get_initial()
        initial['active_tab']='contact_us'
        if not self.request.user.is_anonymous:
            initial['name'] = self.request.user.get_full_name()
            initial['email'] = self.request.user.email
        #initial['subject'] = '-----'

        return initial
		
    def form_valid(self, form):
        form_data = form.cleaned_data

        if not self.request.user.is_anonymous:
            form_data['username'] = self.request.user.username

        #form_data['subject'] = dict(SUBJECT_CHOICES)[form_data['subject']]

        # POST to the support email
        sender = settings.SERVER_EMAIL
        recipients = (getattr(settings, 'CONTACT_US_EMAIL'),)

        tmpl = loader.get_template(self.email_template_name)
        send_mail(self.subject, tmpl.render(form_data), sender, recipients)

        return super(ContactUsView, self).form_valid(form)
		
		

class ContactVendorView(FormView):
    template_name = 'contact/contactvendor.html'
    email_template_name = 'contact/contact_notification_email.txt'
    form_class = ContactVendorForm
    success_url = "/contact/success/"
    subject = "Contact Vendor Request"

    def get_initial(self, **kwargs):
        initial = super(ContactVendorView, self).get_initial()
        if not self.request.user.is_anonymous:
            initial['name'] = self.request.user.get_full_name()
            initial['email'] = self.request.user.email
        #initial['subject'] = '-----'    
        slug=self.kwargs['company_slug']
        company=Company.objects.get(slug=slug)
        print(company.company_email)
		
        return initial

    def form_valid(self, form, **kwargs):
        form_data = form.cleaned_data

        if not self.request.user.is_anonymous:
            form_data['username'] = self.request.user.username

        #form_data['subject'] = dict(SUBJECT_CHOICES)[form_data['subject']]

        # POST to the support email
        sender = settings.SERVER_EMAIL

        slug=self.kwargs['company_slug']
        company=Company.objects.get(slug=slug)
		
        recipients = company.company_email
		
        tmpl = loader.get_template(self.email_template_name)
        send_mail(self.subject, tmpl.render(form_data), sender, recipients)

        return super(ContactVendorView, self).form_valid(form)		