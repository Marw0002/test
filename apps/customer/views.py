from django import http
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
from django.utils.http import urlquote
from django.forms import formset_factory

from oscar.apps.customer.utils import get_password_reset_url
from oscar.core.compat import get_user_model, user_is_authenticated
from oscar.core.loading import (
    get_class, get_classes, get_model, get_profile_class)
from oscar.core.utils import safe_referrer
from oscar.views.generic import PostActionMixin

from . import signals

PageTitleMixin, RegisterUserMixin = get_classes(
    'customer.mixins', ['PageTitleMixin', 'RegisterUserMixin'])
Dispatcher = get_class('customer.utils', 'Dispatcher')

EmailAuthenticationForm, EmailUserCreationForm, EmailVendorCreationForm, CompanyForm, CompanyProfileForm = get_classes(
    'customer.forms', ['EmailAuthenticationForm', 'EmailUserCreationForm', 'EmailVendorCreationForm',
                       'CompanyForm','CompanyProfileForm'])

PasswordChangeForm = get_class('customer.forms', 'PasswordChangeForm')
ProfileForm, ConfirmPasswordForm = get_classes(
    'customer.forms', ['ProfileForm', 'ConfirmPasswordForm'])
Email = get_model('customer', 'Email')
CommunicationEventType = get_model('customer', 'CommunicationEventType')
Company = get_model('customer','Company')
Product = get_model('catalogue', 'Product')
User = get_user_model()


# =======
# Account
# =======


class AccountSummaryView(generic.RedirectView):
    """
    View that exists for legacy reasons and customisability. It commonly gets
    called when the user clicks on "Account" in the navbar.

    Oscar defaults to just redirecting to the profile summary page (and
    that redirect can be configured via OSCAR_ACCOUNT_REDIRECT_URL), but
    it's also likely you want to display an 'account overview' page or
    such like. The presence of this view allows just that, without
    having to change a lot of templates.
    """
    pattern_name = settings.OSCAR_ACCOUNTS_REDIRECT_URL
    permanent = False


class AccountRegistrationView(RegisterUserMixin, generic.FormView):
    template_name = 'customer/registration.html'
    form_class = EmailUserCreationForm
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        if user_is_authenticated(request.user):
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super(AccountRegistrationView, self).get(
            request, *args, **kwargs)

    def get_form(self, bind_data=False):
        return self.form_class(
            **self.get_form_kwargs(bind_data))

    def get_logged_in_redirect(self):
        return reverse('customer:summary')

    def get_form_kwargs(self, bind_data=False):
        kwargs = super(AccountRegistrationView, self).get_form_kwargs()
        kwargs['initial'] = {
            'email': self.request.GET.get('email', ''),
            'redirect_url': self.request.GET.get(self.redirect_field_name, '')
        }
        kwargs['host'] = self.request.get_host()
        return kwargs	
		
    def get_context_data(self, *args, **kwargs):
        ctx = super(AccountRegistrationView, self).get_context_data(
            *args, **kwargs)
        ctx['cancel_url'] = safe_referrer(self.request, '')
        return ctx

    def form_valid(self, form):
        self.register_user(form)
        return redirect(form.cleaned_data['redirect_url'])

    def vendor_form_valid(self, form):
        self.register_user(form)
        return redirect(form.cleaned_data['redirect_url'])

class AccountRegView(RegisterUserMixin, generic.TemplateView):
    """
    This is actually a slightly odd double form view that allows a customer to
    either login or register.
    """
    template_name = 'customer/registration.html'
    user_prefix, vendor_prefix = 'user', 'vendor'
    user_form_class = EmailUserCreationForm
    vendor_form_class = CompanyForm
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        if user_is_authenticated(request.user):
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super(AccountRegView, self).get(
            request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        ctx = super(AccountRegView, self).get_context_data(*args, **kwargs)
        if 'user_form' not in kwargs:
            ctx['user_form'] = self.get_user_form()
        if 'vendor_form' not in kwargs:
            ctx['vendor_form'] = self.get_vendor_form()
        return ctx

    def post(self, request, *args, **kwargs):
        # Use the name of the submit button to determine which form to validate
        if u'user_submit' in request.POST:
            return self.validate_user_form()
        elif u'vendor_submit' in request.POST:
            return self.validate_vendor_form()
        return http.HttpResponseBadRequest()

    # LOGIN

    def get_user_form(self, bind_data=False):
        return self.user_form_class(
            **self.get_user_form_kwargs(bind_data))

    def get_user_form_kwargs(self, bind_data=False):
        kwargs = {}
        kwargs['host'] = self.request.get_host()
        kwargs['prefix'] = self.user_prefix
        kwargs['initial'] = {
            'redirect_url': self.request.GET.get(self.redirect_field_name, ''),
        }
        if bind_data and self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def validate_user_form(self):
        form = self.get_user_form(bind_data=True)
        if form.is_valid(): 
            user=self.register_user(form)   #send registration email if settings in default OSCAR_SEND_CONFIRMATION_EMAIL is set to true
            msg = self.get_registration_success_message(form)
            messages.success(self.request, msg)

            return redirect(self.get_registration_success_url(form))

        ctx = self.get_context_data(user_form=form)
        return self.render_to_response(ctx)

    def get_vendor_form(self, bind_data=False):
        return self.vendor_form_class(
            **self.get_vendor_form_kwargs(bind_data))

    def get_vendor_form_kwargs(self, bind_data=False):
        kwargs = {}
        kwargs['prefix'] = self.vendor_prefix
        kwargs['initial'] = {
            'redirect_url': self.request.GET.get(self.redirect_field_name, ''),
        }
        if bind_data and self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def validate_vendor_form(self):
        
        form1 = self.get_user_form(bind_data=True)
        form2 = self.get_vendor_form(bind_data=True)		
        if form1.is_valid():
            company_name=form2['company_name'].value()		
            if (len(Company.objects.filter(company_name__iexact=company_name))==1):
                company=Company.objects.get(company_name=company_name)
                if not company.user is None:
                    form2.is_valid()
                else:
                    user=form1.save()
                    company.user=user
                    company.save()					
                    dashboard_access_perm = Permission.objects.get(codename='dashboard_access', content_type__app_label='customer')
                    user.user_permissions.add(dashboard_access_perm)			
                    msg = self.get_registration_success_message(form1)
                    messages.success(self.request, msg)
            else:
                user=form1.save()
                #form2 = self.get_vendor_form(bind_data=True)			
                instance = form2.save(commit=False)  # this is the trick.
                instance.user = user
                instance.save()
                #form2.save()
                #self.register_user(form1)
			    #add permission
                dashboard_access_perm = Permission.objects.get(codename='dashboard_access', content_type__app_label='customer')
                user.user_permissions.add(dashboard_access_perm)			
                msg = self.get_registration_success_message(form1)
                messages.success(self.request, msg)
            
                return redirect(self.get_registration_success_url(form1))

        ctx = self.get_context_data(user_form=form1, vendor_form=form2)
        return self.render_to_response(ctx)

    def get_registration_success_message(self, form):
        return _("Thanks for registering!")

    def get_registration_success_url(self, form):
        redirect_url = form.cleaned_data['redirect_url']
        if redirect_url:
            return redirect_url

        return settings.LOGIN_REDIRECT_URL		
		
		
class AccountAuthView(RegisterUserMixin, generic.TemplateView):
    """
    This is actually a slightly odd double form view that allows a customer to
    either login or register.
    """
    template_name = 'customer/login_registration.html'
    login_prefix, registration_prefix = 'login', 'registration'
    login_form_class = EmailAuthenticationForm
    registration_form_class = EmailUserCreationForm
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        if user_is_authenticated(request.user):
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super(AccountAuthView, self).get(
            request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        ctx = super(AccountAuthView, self).get_context_data(*args, **kwargs)
        if 'login_form' not in kwargs:
            ctx['login_form'] = self.get_login_form()
        if 'registration_form' not in kwargs:
            ctx['registration_form'] = self.get_registration_form()
        return ctx

    def post(self, request, *args, **kwargs):
        # Use the name of the submit button to determine which form to validate
        if u'login_submit' in request.POST:
            return self.validate_login_form()
        elif u'registration_submit' in request.POST:
            return self.validate_registration_form()
        return http.HttpResponseBadRequest()

    # LOGIN

    def get_login_form(self, bind_data=False):
        return self.login_form_class(
            **self.get_login_form_kwargs(bind_data))

    def get_login_form_kwargs(self, bind_data=False):
        kwargs = {}
        kwargs['host'] = self.request.get_host()
        kwargs['prefix'] = self.login_prefix
        kwargs['initial'] = {
            'redirect_url': self.request.GET.get(self.redirect_field_name, ''),
        }
        if bind_data and self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def validate_login_form(self):
        form = self.get_login_form(bind_data=True)
        if form.is_valid():
            user = form.get_user()

            # Grab a reference to the session ID before logging in
            old_session_key = self.request.session.session_key

            auth_login(self.request, form.get_user())

            # Raise signal robustly (we don't want exceptions to crash the
            # request handling). We use a custom signal as we want to track the
            # session key before calling login (which cycles the session ID).
            signals.user_logged_in.send_robust(
                sender=self, request=self.request, user=user,
                old_session_key=old_session_key)

            msg = self.get_login_success_message(form)
            if msg:
                messages.success(self.request, msg)

            return redirect(self.get_login_success_url(form))

        ctx = self.get_context_data(login_form=form)
        return self.render_to_response(ctx)

    def get_login_success_message(self, form):
        return _("Welcome back")

    def get_login_success_url(self, form):
        redirect_url = form.cleaned_data['redirect_url']
        if redirect_url:
            return redirect_url

        # Redirect staff members to dashboard as that's the most likely place
        # they'll want to visit if they're logging in.
        if self.request.user.is_staff:
            return reverse('dashboard:index')

        return settings.LOGIN_REDIRECT_URL

    # REGISTRATION

    def get_registration_form(self, bind_data=False):
        return self.registration_form_class(
            **self.get_registration_form_kwargs(bind_data))

    def get_registration_form_kwargs(self, bind_data=False):
        kwargs = {}
        kwargs['host'] = self.request.get_host()
        kwargs['prefix'] = self.registration_prefix
        kwargs['initial'] = {
            'redirect_url': self.request.GET.get(self.redirect_field_name, ''),
        }
        if bind_data and self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def validate_registration_form(self):
        form = self.get_registration_form(bind_data=True)
        if form.is_valid():
            self.register_user(form)

            msg = self.get_registration_success_message(form)
            messages.success(self.request, msg)

            return redirect(self.get_registration_success_url(form))

        ctx = self.get_context_data(registration_form=form)
        return self.render_to_response(ctx)

    def get_registration_success_message(self, form):
        return _("Thanks for registering!")

    def get_registration_success_url(self, form):
        redirect_url = form.cleaned_data['redirect_url']
        if redirect_url:
            return redirect_url

        return settings.LOGIN_REDIRECT_URL


class LogoutView(generic.RedirectView):
    url = settings.OSCAR_HOMEPAGE
    permanent = False

    def get(self, request, *args, **kwargs):
        auth_logout(request)
        response = super(LogoutView, self).get(request, *args, **kwargs)

        for cookie in settings.OSCAR_COOKIES_DELETE_ON_LOGOUT:
            response.delete_cookie(cookie)

        return response


# =============
# Profile
# =============


class ProfileView(PageTitleMixin, generic.TemplateView):
    template_name = 'customer/profile/profile.html'
    page_title = _('Profile')
    active_tab = 'profile'

    def get_context_data(self, **kwargs):
        ctx = super(ProfileView, self).get_context_data(**kwargs)
        ctx['profile_fields'] = self.get_profile_fields(self.request.user)
        return ctx

    def get_profile_fields(self, user):
        field_data = []

        # Check for custom user model
        for field_name in User._meta.additional_fields:
            field_data.append(
                self.get_model_field_data(user, field_name))

        # Check for profile class
        profile_class = get_profile_class()
        if profile_class:
            try:
                profile = profile_class.objects.get(user=user)
            except ObjectDoesNotExist:
                profile = profile_class(user=user)

            field_names = [f.name for f in profile._meta.local_fields]
            for field_name in field_names:
                if field_name in ('user', 'id'):
                    continue
                field_data.append(
                    self.get_model_field_data(profile, field_name))

        return field_data

    def get_model_field_data(self, model_class, field_name):
        """
        Extract the verbose name and value for a model's field value
        """
        field = model_class._meta.get_field(field_name)
        if field.choices:
            value = getattr(model_class, 'get_%s_display' % field_name)()
        else:
            value = getattr(model_class, field_name)
        return {
            'name': getattr(field, 'verbose_name'),
            'value': value,
        }


class ProfileUpdateView(PageTitleMixin, generic.FormView):
    form_class = ProfileForm
    template_name = 'customer/profile/profile_form.html'
    communication_type_code = 'EMAIL_CHANGED'
    page_title = _('Edit Profile')
    active_tab = 'profile'
    success_url = reverse_lazy('customer:profile-view')

    def get_form_kwargs(self):
        kwargs = super(ProfileUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Grab current user instance before we save form.  We may need this to
        # send a warning email if the email address is changed.
        try:
            old_user = User.objects.get(id=self.request.user.id)
        except User.DoesNotExist:
            old_user = None

        form.save()

        # We have to look up the email address from the form's
        # cleaned data because the object created by form.save() can
        # either be a user or profile instance depending whether a profile
        # class has been specified by the AUTH_PROFILE_MODULE setting.
        new_email = form.cleaned_data.get('email')
        if new_email and old_user and new_email != old_user.email:
            # Email address has changed - send a confirmation email to the old
            # address including a password reset link in case this is a
            # suspicious change.
            ctx = {
                'user': self.request.user,
                'site': get_current_site(self.request),
                'reset_url': get_password_reset_url(old_user),
                'new_email': new_email,
            }
            msgs = CommunicationEventType.objects.get_and_render(
                code=self.communication_type_code, context=ctx)
            Dispatcher().dispatch_user_messages(old_user, msgs)

        messages.success(self.request, _("Profile updated"))
        return redirect(self.get_success_url())


class ProfileDeleteView(PageTitleMixin, generic.FormView):
    form_class = ConfirmPasswordForm
    template_name = 'customer/profile/profile_delete.html'
    page_title = _('Delete profile')
    active_tab = 'profile'
    success_url = settings.OSCAR_HOMEPAGE

    def get_form_kwargs(self):
        kwargs = super(ProfileDeleteView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.request.user.delete()
        messages.success(
            self.request,
            _("Your profile has now been deleted. Thanks for using the site."))
        return redirect(self.get_success_url())


class ChangePasswordView(PageTitleMixin, generic.FormView):
    form_class = PasswordChangeForm
    template_name = 'customer/profile/change_password_form.html'
    communication_type_code = 'PASSWORD_CHANGED'
    page_title = _('Change Password')
    active_tab = 'profile'
    
    success_url = reverse_lazy('customer:profile-view')

    def get_form_kwargs(self):
        kwargs = super(ChangePasswordView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, self.request.user)
        messages.success(self.request, _("Password updated"))

        ctx = {
            'user': self.request.user,
            'site': get_current_site(self.request),
            'reset_url': get_password_reset_url(self.request.user),
        }
        msgs = CommunicationEventType.objects.get_and_render(
            code=self.communication_type_code, context=ctx)
        Dispatcher().dispatch_user_messages(self.request.user, msgs)

        return redirect(self.get_success_url())

class CompanyProfileView(PageTitleMixin, generic.TemplateView):
    template_name = 'customer/profile/company_profile.html'
    page_title = _('Company Info')
    active_tab = 'company_info' 
	
		
def filter_questions(queryset, company):

    return queryset.filter(company=company).distinct()

class CompanyProfileUpdateView(PageTitleMixin, generic.FormView):
    
    form_class = CompanyProfileForm
    template_name = 'customer/profile/vendor_form.html'
    page_title = _('Edit Company Info')
    active_tab = 'company_info'
    success_url = reverse_lazy('customer:vendor-view')

    def get_form_kwargs(self):
        kwargs = super(CompanyProfileUpdateView, self).get_form_kwargs()
        kwargs['company'] = self.request.user.company

        return kwargs

    def form_valid(self, form):
        # Grab current user instance before we save form.  We may need this to
        # send a warning email if the email address is changed.
        try:
            old_company = Company.objects.get(id=self.request.user.company.id)
        except old_company.DoesNotExist:
            old_company = None

        form.save()

        # We have to look up the email address from the form's
        # cleaned data because the object created by form.save() can
        # either be a user or profile instance depending whether a profile
        # class has been specified by the AUTH_PROFILE_MODULE setting.
        #new_email = form.cleaned_data.get('email')
        #if new_email and old_user and new_email != old_user.email:
            # Email address has changed - send a confirmation email to the old
            # address including a password reset link in case this is a
            # suspicious change.
        #    ctx = {
        #        'user': self.request.user,
        #        'site': get_current_site(self.request),
        #        'reset_url': get_password_reset_url(old_user),
        #        'new_email': new_email,
        #    }
        #    msgs = CommunicationEventType.objects.get_and_render(
        #        code=self.communication_type_code, context=ctx)
        #    Dispatcher().dispatch_user_messages(old_user, msgs)

        messages.success(self.request, _("Profile updated"))
        return redirect(self.get_success_url())		

def filter_products(queryset, company):
    """
    Restrict the queryset to products the given user has access to.
    A staff user is allowed to access all Products.
    A non-staff user is only allowed access to a product if they are in at
    least one stock record's partner user list.
    """
    #return queryset.filter(stockrecords__partner__users__pk=user.pk).distinct()
    return queryset.filter(company_name=company.company_name).distinct()	
		

class CompanyDetailView(generic.DetailView):
    context_object_name = 'company'
    model = Company
    template_folder = "partner"

    # Whether to redirect to the URL with the right path
    enforce_paths = True

    def get(self, request, **kwargs):
        """
        Ensures that the correct URL is used before rendering a response
        """
        self.object = company = self.get_object()
        redirect = self.redirect_if_necessary(request.path, company)
        if redirect is not None:
            return redirect

        response = super(CompanyDetailView, self).get(request, **kwargs)
        #self.send_signal(request, response, product)
        return response

    def get_object(self, queryset=None):
        # Check if self.object is already set to prevent unnecessary DB calls
        if hasattr(self, 'object'):
            return self.object
        else:
            return super(CompanyDetailView, self).get_object(queryset)

    def redirect_if_necessary(self, current_path, company):
        #if self.enforce_parent and product.is_child:
        #    return HttpResponsePermanentRedirect(
        #        product.parent.get_absolute_url())

        if self.enforce_paths:
            expected_path = company.get_absolute_url()
            if expected_path != urlquote(current_path):
                return HttpResponsePermanentRedirect(expected_path)

    def get_context_data(self, **kwargs):
        ctx = super(CompanyDetailView, self).get_context_data(**kwargs)
        company=self.get_object()
        projects=Product.objects.filter(company=company)      
        ctx['projects']=projects
        if not (projects.count()==0):
            main_project=Product.objects.filter(company=company).order_by('-id')[0]
            ctx['main_project']=main_project
        return ctx
		

    def get_template_names(self):
        """
        Return a list of possible templates.

        If an overriding class sets a template name, we use that. Otherwise,
        we try 2 options before defaulting to catalogue/detail.html:
            1). detail-for-upc-<upc>.html
            2). detail-for-class-<classname>.html

        This allows alternative templates to be provided for a per-product
        and a per-item-class basis.
        """
        if self.template_name:
            return [self.template_name]

        return ['%s/detail.html' % (self.template_folder)]
		
# =============
# Email history
# =============

class EmailHistoryView(PageTitleMixin, generic.ListView):
    context_object_name = "emails"
    template_name = 'customer/email/email_list.html'
    paginate_by = settings.OSCAR_EMAILS_PER_PAGE
    page_title = _('Email History')
    active_tab = 'emails'

    def get_queryset(self):
        return Email._default_manager.filter(user=self.request.user)


class EmailDetailView(PageTitleMixin, generic.DetailView):
    """Customer email"""
    template_name = "customer/email/email_detail.html"
    context_object_name = 'email'
    active_tab = 'emails'

    def get_object(self, queryset=None):
        return get_object_or_404(Email, user=self.request.user,
                                 id=self.kwargs['email_id'])

    def get_page_title(self):
        """Append email subject to page title"""
        return u'%s: %s' % (_('Email'), self.object.subject)

