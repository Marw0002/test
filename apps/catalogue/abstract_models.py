import logging
import os
from datetime import date, datetime

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.staticfiles.finders import find
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.base import File
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Count, Sum
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import get_language, pgettext_lazy
from treebeard.mp_tree import MP_Node

from oscar.core.compat import user_is_anonymous, user_is_authenticated
from oscar.core.loading import get_class, get_classes, get_model
from oscar.core.utils import slugify
from oscar.core.validators import non_python_keyword
from oscar.models.fields import AutoSlugField, NullCharField
from oscar.models.fields.slugfield import SlugField

ProductManager, BrowsableProductManager = get_classes(
    'catalogue.managers', ['ProductManager', 'BrowsableProductManager'])


@python_2_unicode_compatible
class AbstractCategory(MP_Node):
    """
    A product category. Merely used for navigational purposes; has no
    effects on business logic.

    Uses django-treebeard.
    """
    name = models.CharField(_('Name'), max_length=255, db_index=True)
    description = models.TextField(_('Description'), blank=True)
    slug = SlugField(_('Slug'), max_length=255, db_index=True)

    _slug_separator = '/'
    _full_name_separator = ' > '

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        """
        Returns a string representation of the category and it's ancestors,
        e.g. 'Books > Non-fiction > Essential programming'.

        It's rarely used in Oscar's codebase, but used to be stored as a
        CharField and is hence kept for backwards compatibility. It's also
        sufficiently useful to keep around.
        """
        names = [category.name for category in self.get_ancestors_and_self()]
        return self._full_name_separator.join(names)

    @property
    def full_slug(self):
        """
        Returns a string of this category's slug concatenated with the slugs
        of it's ancestors, e.g. 'books/non-fiction/essential-programming'.

        Oscar used to store this as in the 'slug' model field, but this field
        has been re-purposed to only store this category's slug and to not
        include it's ancestors' slugs.
        """
        slugs = [category.slug for category in self.get_ancestors_and_self()]
        return self._slug_separator.join(slugs)

    def generate_slug(self):
        """
        Generates a slug for a category. This makes no attempt at generating
        a unique slug.
        """
        return slugify(self.name)

    def ensure_slug_uniqueness(self):
        """
        Ensures that the category's slug is unique amongst it's siblings.
        This is inefficient and probably not thread-safe.
        """
        unique_slug = self.slug
        siblings = self.get_siblings().exclude(pk=self.pk)
        next_num = 2
        while siblings.filter(slug=unique_slug).exists():
            unique_slug = '{slug}_{end}'.format(slug=self.slug, end=next_num)
            next_num += 1

        if unique_slug != self.slug:
            self.slug = unique_slug
            self.save()

    def save(self, *args, **kwargs):
        """
        Oscar traditionally auto-generated slugs from names. As that is
        often convenient, we still do so if a slug is not supplied through
        other means. If you want to control slug creation, just create
        instances with a slug already set, or expose a field on the
        appropriate forms.
        """
        if self.slug:
            # Slug was supplied. Hands off!
            super(AbstractCategory, self).save(*args, **kwargs)
        else:
            self.slug = self.generate_slug()
            super(AbstractCategory, self).save(*args, **kwargs)
            # We auto-generated a slug, so we need to make sure that it's
            # unique. As we need to be able to inspect the category's siblings
            # for that, we need to wait until the instance is saved. We
            # update the slug and save again if necessary.
            self.ensure_slug_uniqueness()

    def get_ancestors_and_self(self):
        """
        Gets ancestors and includes itself. Use treebeard's get_ancestors
        if you don't want to include the category itself. It's a separate
        function as it's commonly used in templates.
        """
        return list(self.get_ancestors()) + [self]

    def get_descendants_and_self(self):
        """
        Gets descendants and includes itself. Use treebeard's get_descendants
        if you don't want to include the category itself. It's a separate
        function as it's commonly used in templates.
        """
        return list(self.get_descendants()) + [self]

    def get_absolute_url(self):
        """
        Our URL scheme means we have to look up the category's ancestors. As
        that is a bit more expensive, we cache the generated URL. That is
        safe even for a stale cache, as the default implementation of
        ProductCategoryView does the lookup via primary key anyway. But if
        you change that logic, you'll have to reconsider the caching
        approach.
        """
        current_locale = get_language()
        cache_key = 'CATEGORY_URL_%s_%s' % (current_locale, self.pk)
        url = cache.get(cache_key)
        if not url:
            url = reverse(
                'catalogue:category',
                kwargs={'category_slug': self.full_slug, 'pk': self.pk})
            cache.set(cache_key, url)
        return url

    class Meta:
        abstract = True
        app_label = 'catalogue'
        ordering = ['path']
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def has_children(self):
        return self.get_num_children() > 0

    def get_num_children(self):
        return self.get_children().count()


@python_2_unicode_compatible
class AbstractProductCategory(models.Model):
    """
    Joining model between products and categories. Exists to allow customising.
    """
    product = models.ForeignKey(
        'catalogue.Product',
        on_delete=models.CASCADE,
        verbose_name=_("Product"))
    category = models.ForeignKey(
        'catalogue.Category',
        on_delete=models.CASCADE,
        verbose_name=_("Category"))

    class Meta:
        abstract = True
        app_label = 'catalogue'
        ordering = ['product', 'category']
        unique_together = ('product', 'category')
        verbose_name = _('Product category')
        verbose_name_plural = _('Product categories')

    def __str__(self):
        return u"<productcategory for product '%s'>" % self.product


@python_2_unicode_compatible
class AbstractProduct(models.Model):
    
    # Title is mandatory for canonical products but optional for child products
    title = models.CharField(pgettext_lazy(u'Product title', u'Title'),
                             max_length=255, blank=True)
    slug = models.SlugField(_('Slug'), max_length=255, unique=False)
    description = models.TextField(_('Description'), blank=True)
 
    color = models.ManyToManyField(
        'catalogue.ProjectColor',
        related_name='color_theme',
        verbose_name=_("Color"), blank = True)
    theme = models.ManyToManyField(
        'catalogue.ProjectTheme',
        related_name='project_theme',
        verbose_name=_("Theme"), blank = True)
		
    color_name=models.CharField(max_length=255, blank=True)
		
    theme_name=models.CharField(max_length=255, blank=True)
	
	
    date_created = models.DateTimeField(_("Date created"), auto_now_add=True)

    # This field is used by Haystack to reindex search
    date_updated = models.DateTimeField(
        _("Date updated"), auto_now=True, db_index=True)

    categories = models.ForeignKey(
        'catalogue.Category',
        verbose_name=_("Categories"), null=True)
		
    BUDGET_CHOICES = (
        ('$','Affordable ($)'),
        ('$$','Standard ($$)'),
        ('$$$','Luxury ($$$)'),
    )
    budget = models.CharField(_('Project budget'),max_length=20, choices=BUDGET_CHOICES, null=True, blank=True)

    #: Determines if a product may be used in an offer. It is illegal to
    #: discount some types of product (e.g. ebooks) and this field helps
    #: merchants from avoiding discounting such products
    #: Note that this flag is ignored for child products; they inherit from
    #: the parent product.

    company = models.ForeignKey('customer.company', on_delete=models.CASCADE, blank=True)
	
    objects = ProductManager()
    browsable = BrowsableProductManager()

    class Meta:
        abstract = True
        app_label = 'catalogue'
        ordering = ['-date_created']
        verbose_name = _('Product')
        verbose_name_plural = _('Products')

    def __init__(self, *args, **kwargs):
        super(AbstractProduct, self).__init__(*args, **kwargs)
        #self.attr = ProductAttributesContainer(product=self)

    def __str__(self):
        if self.title:
            return self.title
        if self.attribute_summary:
            return u"%s (%s)" % (self.get_title(), self.attribute_summary)
        else:
            return self.get_title()

    def get_absolute_url(self):
        """
        Return a product's absolute url
        """
        return reverse('catalogue:detail',
                       kwargs={'product_slug': self.slug, 'pk': self.id})


    def _clean_standalone(self):
        """
        Validates a stand-alone product
        """
        if not self.title:
            raise ValidationError(_("Your product must have a title."))
        #if not self.product_class:
        #    raise ValidationError(_("Your product must have a product class."))
        #if self.parent_id:
        #    raise ValidationError(_("Only child products can have a parent."))


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.get_title())
        super(AbstractProduct, self).save(*args, **kwargs)

    # Properties

    def get_title(self):
        """
        Return a product's title or it's parent's title if it has no title
        """
        title = self.title
        #if not title and self.parent_id:
        #    title = self.parent.title
        return title
    get_title.short_description = pgettext_lazy(u"Product title", u"Title")


    def get_categories(self):
        """
        Return a product's categories or parent's if there is a parent product.
        """
        return self.categories
    get_categories.short_description = _("Categories")

    # Images

    def get_missing_image(self):
        """
        Returns a missing image object.
        """
        # This class should have a 'name' property so it mimics the Django file
        # field.
        return MissingProductImage()

    def primary_image(self):
        """
        Returns the primary image for a product. Usually used when one can
        only display one product image, e.g. in a list of products.
        """
        images = self.images.all()
        ordering = self.images.model.Meta.ordering
        if not ordering or ordering[0] != 'display_order':
            # Only apply order_by() if a custom model doesn't use default
            # ordering. Applying order_by() busts the prefetch cache of
            # the ProductManager
            images = images.order_by('display_order')
        try:
            return images[0]
        except IndexError:
            return {
                'original': self.get_missing_image(),
                'caption': '',
                'is_missing': True}

    @property
    def sorted_recommended_products(self):
        """Keeping order by recommendation ranking."""
        return [r.recommendation for r in self.primary_recommendations
                                              .select_related('recommendation').all()]


class AbstractProductRecommendation(models.Model):
    """
    'Through' model for product recommendations
    """
    primary = models.ForeignKey(
        'catalogue.Product',
        on_delete=models.CASCADE,
        related_name='primary_recommendations',
        verbose_name=_("Primary product"))
    recommendation = models.ForeignKey(
        'catalogue.Product',
        on_delete=models.CASCADE,
        verbose_name=_("Recommended product"))
    ranking = models.PositiveSmallIntegerField(
        _('Ranking'), default=0,
        help_text=_('Determines order of the products. A product with a higher'
                    ' value will appear before one with a lower ranking.'))

    class Meta:
        abstract = True
        app_label = 'catalogue'
        ordering = ['primary', '-ranking']
        unique_together = ('primary', 'recommendation')
        verbose_name = _('Product recommendation')
        verbose_name_plural = _('Product recomendations')


class MissingProductImage(object):

    """
    Mimics a Django file field by having a name property.

    sorl-thumbnail requires all it's images to be in MEDIA_ROOT. This class
    tries symlinking the default "missing image" image in STATIC_ROOT
    into MEDIA_ROOT for convenience, as that is necessary every time an Oscar
    project is setup. This avoids the less helpful NotFound IOError that would
    be raised when sorl-thumbnail tries to access it.
    """

    def __init__(self, name=None):
        self.name = name if name else settings.OSCAR_MISSING_IMAGE_URL
        media_file_path = os.path.join(settings.MEDIA_ROOT, self.name)
        # don't try to symlink if MEDIA_ROOT is not set (e.g. running tests)
        if settings.MEDIA_ROOT and not os.path.exists(media_file_path):
            self.symlink_missing_image(media_file_path)

    def symlink_missing_image(self, media_file_path):
        static_file_path = find('oscar/img/%s' % self.name)
        if static_file_path is not None:
            try:
                # Check that the target directory exists, and attempt to
                # create it if it doesn't.
                media_file_dir = os.path.dirname(media_file_path)
                if not os.path.exists(media_file_dir):
                    os.makedirs(media_file_dir)
                os.symlink(static_file_path, media_file_path)
            except OSError:
                raise ImproperlyConfigured((
                    "Please copy/symlink the "
                    "'missing image' image at %s into your MEDIA_ROOT at %s. "
                    "This exception was raised because Oscar was unable to "
                    "symlink it for you.") % (media_file_path,
                                              settings.MEDIA_ROOT))
            else:
                logging.info((
                    "Symlinked the 'missing image' image at %s into your "
                    "MEDIA_ROOT at %s") % (media_file_path,
                                           settings.MEDIA_ROOT))


@python_2_unicode_compatible
class AbstractProductImage(models.Model):
    """
    An image of a product
    """
    product = models.ForeignKey(
        'catalogue.Product',
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_("Product"))
    original = models.ImageField(
        _("Original"), upload_to=settings.OSCAR_IMAGE_FOLDER, max_length=255)
    caption = models.CharField(_("Caption"), max_length=200, blank=True)

    #: Use display_order to determine which is the "primary" image
    display_order = models.PositiveIntegerField(
        _("Display order"), default=0,
        help_text=_("An image with a display order of zero will be the primary"
                    " image for a product"))
    date_created = models.DateTimeField(_("Date created"), auto_now_add=True)

    class Meta:
        abstract = True
        app_label = 'catalogue'
        # Any custom models should ensure that this ordering is unchanged, or
        # your query count will explode. See AbstractProduct.primary_image.
        ordering = ["display_order"]
        verbose_name = _('Product image')
        verbose_name_plural = _('Product images')

    def __str__(self):
        return u"Image of '%s'" % self.product

    def is_primary(self):
        """
        Return bool if image display order is 0
        """
        return self.display_order == 0

    def delete(self, *args, **kwargs):
        """
        Always keep the display_order as consecutive integers. This avoids
        issue #855.
        """
        super(AbstractProductImage, self).delete(*args, **kwargs)
        for idx, image in enumerate(self.product.images.all()):
            image.display_order = idx
            image.save()



@python_2_unicode_compatible
class AbstractProjectTheme(models.Model):

    name = models.CharField(_("Caption"), max_length=100, blank=True)
    display_order = models.PositiveIntegerField(
        _("Display order"), default=0)

    class Meta:
        abstract = True
        app_label = 'catalogue'
        # Any custom models should ensure that this ordering is unchanged, or
        # your query count will explode. See AbstractProduct.primary_image.
        ordering = ["display_order"]
        verbose_name = _('Project Theme')
        verbose_name_plural = _('Project Theme')

    def __str__(self):
        return u"%s" % self.name

    def delete(self, *args, **kwargs):
        """
        Always keep the display_order as consecutive integers. This avoids
        issue #855.
        """
        super(AbstractProjectTheme, self).delete(*args, **kwargs)
        for idx, image in enumerate(self.themes.all()):
            theme.display_order = idx
            theme.save()

@python_2_unicode_compatible
class AbstractProjectColor(models.Model):

    name = models.CharField(_("Color"), max_length=100)    
    display_order = models.PositiveIntegerField(
        _("Display order"), default=0,
        help_text=_("Display order of the color"))

    class Meta:
        abstract = True
        app_label = 'catalogue'
        # Any custom models should ensure that this ordering is unchanged, or
        # your query count will explode. See AbstractProduct.primary_image.
        ordering = ["display_order"]
        verbose_name = _('Theme Color')
        verbose_name_plural = _('Theme Color')

    def __str__(self):
        return u"%s" % self.name

    def delete(self, *args, **kwargs):
        """
        Always keep the display_order as consecutive integers. This avoids
        issue #855.
        """
        super(AbstractProjectColor, self).delete(*args, **kwargs)
        for idx, color in enumerate(self.colors.all()):
            color.display_order = idx
            color.save()

