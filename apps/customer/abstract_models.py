import hashlib
import random

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Count, Sum
from django.template import TemplateDoesNotExist, engines
from django.template.loader import get_template
from django.utils import six, timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property
from django.dispatch import receiver
from django.db.models.signals import post_save
from phonenumber_field.modelfields import PhoneNumberField

from oscar.apps.customer.managers import CommunicationTypeManager
from oscar.core.loading import get_classes
from oscar.core.compat import AUTH_USER_MODEL
from oscar.models.fields import AutoSlugField
from oscar.core.utils import slugify
from oscar.core.compat import user_is_anonymous, user_is_authenticated

CompanyManager, BrowsableCompanyManager = get_classes(
    'customer.managers', ['CompanyManager', 'BrowsableCompanyManager'])

class UserManager(auth_models.BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and
        password.
        """
        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')
        email = UserManager.normalize_email(email)
        user = self.model(
            email=email, is_staff=False, is_active=True,
            is_superuser=False, 
            last_login=now, date_joined=now, **extra_fields)\
		
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        u = self.create_user(email, password, **extra_fields)
        u.is_staff = True
        u.is_active = True
        u.is_superuser = True
        u.save(using=self._db)
        return u


class AbstractUser(auth_models.AbstractBaseUser,
                   auth_models.PermissionsMixin):
    """
    An abstract base user suitable for use in Oscar projects.

    This is basically a copy of the core AbstractUser model but without a
    username field
    """
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(
        _('First name'), max_length=255, blank=True)
    last_name = models.CharField(
        _('Last name'), max_length=255, blank=True)
    is_staff = models.BooleanField(
        _('Staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin '
                    'site.'))
    is_active = models.BooleanField(
        _('Active'), default=True,
        help_text=_('Designates whether this user should be treated as '
                    'active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'),
                                       default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'

    class Meta:
        abstract = True
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        return self.first_name

    def _migrate_alerts_to_user(self):
        """
        Transfer any active alerts linked to a user's email address to the
        newly registered user.
        """
        ProductAlert = self.alerts.model
        alerts = ProductAlert.objects.filter(
            email=self.email, status=ProductAlert.ACTIVE)
        alerts.update(user=self, key='', email='')

    def save(self, *args, **kwargs):
        super(AbstractUser, self).save(*args, **kwargs)
        # Migrate any "anonymous" product alerts to the registered user
        # Ideally, this would be done via a post-save signal. But we can't
        # use get_user_model to wire up signals to custom user models
        # see Oscar ticket #1127, Django ticket #19218
        self._migrate_alerts_to_user()


@python_2_unicode_compatible
class AbstractEmail(models.Model):
    """
    This is a record of all emails sent to a customer.
    Normally, we only record order-related emails.
    """
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='emails',
        verbose_name=_("User"),
        null=True)
    email = models.EmailField(_('Email Address'), null=True, blank=True)
    subject = models.TextField(_('Subject'), max_length=255)
    body_text = models.TextField(_("Body Text"))
    body_html = models.TextField(_("Body HTML"), blank=True)
    date_sent = models.DateTimeField(_("Date Sent"), auto_now_add=True)

    class Meta:
        abstract = True
        app_label = 'customer'
        verbose_name = _('Email')
        verbose_name_plural = _('Emails')

    def __str__(self):
        if self.user:
            return _(u"Email to %(user)s with subject '%(subject)s'") % {
                'user': self.user.get_username(), 'subject': self.subject}
        else:
            return _(u"Anonymous email to %(email)s with subject '%(subject)s'") % {
                'email': self.email, 'subject': self.subject}


@python_2_unicode_compatible
class AbstractCommunicationEventType(models.Model):
    """
    A 'type' of communication.  Like an order confirmation email.
    """

    #: Code used for looking up this event programmatically.
    # e.g. PASSWORD_RESET. AutoSlugField uppercases the code for us because
    # it's a useful convention that's been enforced in previous Oscar versions
    code = AutoSlugField(
        _('Code'), max_length=128, unique=True, populate_from='name',
        separator=six.u("_"), uppercase=True, editable=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z_][0-9a-zA-Z_]*$',
                message=_(
                    "Code can only contain the letters a-z, A-Z, digits, "
                    "and underscores, and can't start with a digit."))],
        help_text=_("Code used for looking up this event programmatically"))

    #: Name is the friendly description of an event for use in the admin
    name = models.CharField(
        _('Name'), max_length=255,
        help_text=_("This is just used for organisational purposes"))

    # We allow communication types to be categorised
    # For backwards-compatibility, the choice values are quite verbose
    ORDER_RELATED = 'Order related'
    USER_RELATED = 'User related'
    CATEGORY_CHOICES = (
        (ORDER_RELATED, _('Order related')),
        (USER_RELATED, _('User related'))
    )

    category = models.CharField(
        _('Category'), max_length=255, default=ORDER_RELATED,
        choices=CATEGORY_CHOICES)

    # Template content for emails
    # NOTE: There's an intentional distinction between None and ''. None
    # instructs Oscar to look for a file-based template, '' is just an empty
    # template.
    email_subject_template = models.CharField(
        _('Email Subject Template'), max_length=255, blank=True, null=True)
    email_body_template = models.TextField(
        _('Email Body Template'), blank=True, null=True)
    email_body_html_template = models.TextField(
        _('Email Body HTML Template'), blank=True, null=True,
        help_text=_("HTML template"))

    # Template content for SMS messages
    sms_template = models.CharField(_('SMS Template'), max_length=170,
                                    blank=True, null=True,
                                    help_text=_("SMS template"))

    date_created = models.DateTimeField(_("Date Created"), auto_now_add=True)
    date_updated = models.DateTimeField(_("Date Updated"), auto_now=True)

    objects = CommunicationTypeManager()

    # File templates
    email_subject_template_file = 'customer/emails/commtype_%s_subject.txt'
    email_body_template_file = 'customer/emails/commtype_%s_body.txt'
    email_body_html_template_file = 'customer/emails/commtype_%s_body.html'
    sms_template_file = 'customer/sms/commtype_%s_body.txt'

    class Meta:
        abstract = True
        app_label = 'customer'
        verbose_name = _("Communication event type")
        verbose_name_plural = _("Communication event types")

    def get_messages(self, ctx=None):
        """
        Return a dict of templates with the context merged in

        We look first at the field templates but fail over to
        a set of file templates that follow a conventional path.
        """
        code = self.code.lower()

        # Build a dict of message name to Template instances
        templates = {'subject': 'email_subject_template',
                     'body': 'email_body_template',
                     'html': 'email_body_html_template',
                     'sms': 'sms_template'}
        for name, attr_name in templates.items():
            field = getattr(self, attr_name, None)
            if field is not None:
                # Template content is in a model field
                templates[name] = engines['django'].from_string(field)
            else:
                # Model field is empty - look for a file template
                template_name = getattr(self, "%s_file" % attr_name) % code
                try:
                    templates[name] = get_template(template_name)
                except TemplateDoesNotExist:
                    templates[name] = None

        # Pass base URL for serving images within HTML emails
        if ctx is None:
            ctx = {}
        ctx['static_base_url'] = getattr(
            settings, 'OSCAR_STATIC_BASE_URL', None)

        messages = {}
        for name, template in templates.items():
            messages[name] = template.render(ctx) if template else ''

        # Ensure the email subject doesn't contain any newlines
        messages['subject'] = messages['subject'].replace("\n", "")
        messages['subject'] = messages['subject'].replace("\r", "")

        return messages

    def __str__(self):
        return self.name

    def is_order_related(self):
        return self.category == self.ORDER_RELATED

    def is_user_related(self):
        return self.category == self.USER_RELATED


@python_2_unicode_compatible
class AbstractNotification(models.Model):
    recipient = models.ForeignKey(
        AUTH_USER_MODEL,
        db_index=True,
        on_delete=models.CASCADE,
        related_name='notifications')

    # Not all notifications will have a sender.
    sender = models.ForeignKey(
        AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True)

    # HTML is allowed in this field as it can contain links
    subject = models.CharField(max_length=255)
    body = models.TextField()

    # Some projects may want to categorise their notifications.  You may want
    # to use this field to show a different icons next to the notification.
    category = models.CharField(max_length=255, blank=True)

    INBOX, ARCHIVE = 'Inbox', 'Archive'
    choices = (
        (INBOX, _('Inbox')),
        (ARCHIVE, _('Archive')))
    location = models.CharField(max_length=32, choices=choices,
                                default=INBOX)

    date_sent = models.DateTimeField(auto_now_add=True)
    date_read = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'customer'
        ordering = ('-date_sent',)
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self):
        return self.subject

    def archive(self):
        self.location = self.ARCHIVE
        self.save()
    archive.alters_data = True

    @property
    def is_read(self):
        return self.date_read is not None


class AbstractProductAlert(models.Model):
    """
    An alert for when a product comes back in stock
    """
    product = models.ForeignKey(
        'catalogue.Product',
        on_delete=models.CASCADE)

    # A user is only required if the notification is created by a
    # registered user, anonymous users will only have an email address
    # attached to the notification
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        blank=True,
        db_index=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="alerts",
        verbose_name=_('User'))
    email = models.EmailField(_("Email"), db_index=True, blank=True)

    # This key are used to confirm and cancel alerts for anon users
    key = models.CharField(_("Key"), max_length=128, blank=True, db_index=True)

    # An alert can have two different statuses for authenticated
    # users ``ACTIVE`` and ``CANCELLED`` and anonymous users have an
    # additional status ``UNCONFIRMED``. For anonymous users a confirmation
    # and unsubscription key are generated when an instance is saved for
    # the first time and can be used to confirm and unsubscribe the
    # notifications.
    UNCONFIRMED, ACTIVE, CANCELLED, CLOSED = (
        'Unconfirmed', 'Active', 'Cancelled', 'Closed')
    STATUS_CHOICES = (
        (UNCONFIRMED, _('Not yet confirmed')),
        (ACTIVE, _('Active')),
        (CANCELLED, _('Cancelled')),
        (CLOSED, _('Closed')),
    )
    status = models.CharField(_("Status"), max_length=20,
                              choices=STATUS_CHOICES, default=ACTIVE)

    date_created = models.DateTimeField(_("Date created"), auto_now_add=True)
    date_confirmed = models.DateTimeField(_("Date confirmed"), blank=True,
                                          null=True)
    date_cancelled = models.DateTimeField(_("Date cancelled"), blank=True,
                                          null=True)
    date_closed = models.DateTimeField(_("Date closed"), blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'customer'
        verbose_name = _('Product alert')
        verbose_name_plural = _('Product alerts')

    @property
    def is_anonymous(self):
        return self.user is None

    @property
    def can_be_confirmed(self):
        return self.status == self.UNCONFIRMED

    @property
    def can_be_cancelled(self):
        return self.status in (self.ACTIVE, self.UNCONFIRMED)

    @property
    def is_cancelled(self):
        return self.status == self.CANCELLED

    @property
    def is_active(self):
        return self.status == self.ACTIVE

    def confirm(self):
        self.status = self.ACTIVE
        self.date_confirmed = timezone.now()
        self.save()
    confirm.alters_data = True

    def cancel(self):
        self.status = self.CANCELLED
        self.date_cancelled = timezone.now()
        self.save()
    cancel.alters_data = True

    def close(self):
        self.status = self.CLOSED
        self.date_closed = timezone.now()
        self.save()
    close.alters_data = True

    def get_email_address(self):
        if self.user:
            return self.user.email
        else:
            return self.email

    def save(self, *args, **kwargs):
        if not self.id and not self.user:
            self.key = self.get_random_key()
            self.status = self.UNCONFIRMED
        # Ensure date fields get updated when saving from modelform (which just
        # calls save, and doesn't call the methods cancel(), confirm() etc).
        if self.status == self.CANCELLED and self.date_cancelled is None:
            self.date_cancelled = timezone.now()
        if not self.user and self.status == self.ACTIVE \
                and self.date_confirmed is None:
            self.date_confirmed = timezone.now()
        if self.status == self.CLOSED and self.date_closed is None:
            self.date_closed = timezone.now()

        return super(AbstractProductAlert, self).save(*args, **kwargs)

    def get_random_key(self):
        """
        Get a random generated key based on SHA-1 and email address
        """
        salt = hashlib.sha1(str(random.random()).encode('utf8')).hexdigest()
        return hashlib.sha1((salt + self.email).encode('utf8')).hexdigest()

    def get_confirm_url(self):
        return reverse('customer:alerts-confirm', kwargs={'key': self.key})

    def get_cancel_url(self):
        return reverse('customer:alerts-cancel-by-key', kwargs={'key':
                                                                self.key})

class AbstractCompany(models.Model):

    company_name = models.CharField(_('Company Name'), max_length=100, blank=True, unique = True, null=True)
	
    is_vendor = models.BooleanField(('Vendor status'), default=False,
        help_text=('Designates whether the user is customer or vendor.'))
    user = models.OneToOneField(AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    rating = models.FloatField(_('Rating'), null=True, editable=False)
    company_logo = models.ImageField(
        _("Company Logo"), upload_to=settings.OSCAR_IMAGE_FOLDER, max_length=255, null=True, blank=True)
    description = models.CharField(_('Services Offered (Interior Design, Contractor, Decoration, etc)'), max_length=50, blank=True)
	
    city = models.ForeignKey('customer.city', blank=True, null=True)
    slug = models.SlugField(_('Slug'), max_length=255, unique=False)
    company_email = models.EmailField(_('Company Email Address'), null=True, blank=True)
    contact=PhoneNumberField(_('Company Contact Number'),blank=True)
    websiteadd = models.CharField(('Homepage Link e.g. http://www.comfy.com'), max_length=100, blank=True, null=True)
    instagramadd = models.CharField(('Instagram Link e.g. https://www.instagram.com/comfy'), max_length=100, blank=True, null=True)
    facebookadd = models.CharField(('Facebook Link e.g. https://www.facebook.com/comfy'), max_length=100, blank=True, null=True)
    
    valid_date = models.DateField(_("Access validity until"), blank=True, null=True)    
	
    SECTOR_CHOICES = (
        ('INTERIOR DESIGN', 'interior_design'),
        ('CONTRACTOR', 'contractor'),
        ('OTHER', 'other'),
    )

    company_sector = models.CharField(('Company Name'),max_length=100, choices=SECTOR_CHOICES, default='INTERIOR DESIGN')
    
    pricing = models.TextField(_('Price List'), blank=True)
	
    price_low = models.CharField(_('Price Range Low'),max_length=20, null=True, blank=True)	
    price_high = models.CharField(_('Price Range High'),max_length=20, null=True, blank=True)
	
    objects = CompanyManager()
    browsable = BrowsableCompanyManager()	
	
    class Meta:
        abstract=True
        app_label = 'customer'
        permissions = (("dashboard_access","Can access dashboard"),)

    def __init__(self, *args, **kwargs):
        super(AbstractCompany, self).__init__(*args, **kwargs)
		
    def __str__(self):
        return self.company_name

    # Updating methods

    def update_rating(self):
        """
        Recalculate rating field
        """
        self.rating = self.calculate_rating()
        self.save()
    update_rating.alters_data = True

    def calculate_rating(self):
        """
        Calculate rating value
        """
        result = self.reviews.filter(
            status=self.reviews.model.APPROVED
        ).aggregate(
            sum=Sum('score'), count=Count('id'))
        reviews_sum = result['sum'] or 0
        reviews_count = result['count'] or 0
        rating = None
        if reviews_count > 0:
            rating = float(reviews_sum) / reviews_count
        return rating

    def has_review_by(self, user):
        if user_is_anonymous(user):
            return False
        return self.reviews.filter(user=user).exists()

    def is_review_permitted(self, user):
        """
        Determines whether a user may add a review on this product.

        Default implementation respects OSCAR_ALLOW_ANON_REVIEWS and only
        allows leaving one review per user and product.

        Override this if you want to alter the default behaviour; e.g. enforce
        that a user purchased the product to be allowed to leave a review.
        """
        if user_is_authenticated(user) or settings.OSCAR_ALLOW_ANON_REVIEWS:
            return not self.has_review_by(user)
        else:
            return False

    @cached_property
    def num_approved_reviews(self):
        return self.reviews.approved().count()	

    def display_name(self):
        return self.company_name
		
    def get_name(self):
        """
        Return a product's title or it's parent's title if it has no title
        """
        name = self.company_name
        return name		

    def get_absolute_url(self):
        """
        Return a product's absolute url
        """
        return reverse('customer:vendor-detail',
                       kwargs={'company_slug': self.slug, 'pk': self.id})

    def get_contact_url(self):
        """
        Return a product's absolute url
        """
        return reverse('contact:contactvendor',
                       kwargs={'company_slug': self.slug, 'pk': self.id})					   
					   
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.get_name())
        super(AbstractCompany, self).save(*args, **kwargs)

		
class AbstractCity(models.Model):

    name = models.CharField(_("City"), max_length=50, blank=True)
    country = models.ForeignKey('customer.country', related_name='vendor_city',verbose_name=_("City"),on_delete=models.CASCADE)
	
    class Meta:
        abstract=True
        app_label = 'customer'

    def __init__(self, *args, **kwargs):
        super(AbstractCity, self).__init__(*args, **kwargs)
		
    def __str__(self):
        return self.name	

class AbstractCountry(models.Model):

    name = models.CharField(_("Country"), max_length=50, blank=True)
    code = models.CharField(_("Code"), max_length=20, blank=True)
	
	
    class Meta:
        abstract=True
        app_label = 'customer'
    def __init__(self, *args, **kwargs):
        super(AbstractCountry, self).__init__(*args, **kwargs)
		
    def __str__(self):
        return self.name
		
		
    