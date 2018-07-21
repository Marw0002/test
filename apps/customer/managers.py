from django.db import models


class CommunicationTypeManager(models.Manager):

    def get_and_render(self, code, context):
        """
        Return a dictionary of rendered messages, ready for sending.

        This method wraps around whether an instance of this event-type exists
        in the database.  If not, then an instance is created on the fly and
        used to generate the message contents.
        """
        try:
            commtype = self.get(code=code)
        except self.model.DoesNotExist:
            commtype = self.model(code=code)
        return commtype.get_messages(context)

		
class CompanyQuerySet(models.query.QuerySet):

    def base_queryset(self):
        """
        Applies select_related and prefetch_related for commonly related
        models to save on queries
        """

        return self
    def browsable(self):
        """
        Excludes non-canonical products.
        """
        #return self.filter(parent=None)
        return self.filter()


class CompanyManager(models.Manager):
    """
    Uses ProductQuerySet and proxies its methods to allow chaining

    Once Django 1.7 lands, this class can probably be removed:
    https://docs.djangoproject.com/en/dev/releases/1.7/#calling-custom-queryset-methods-from-the-manager  # noqa
    """

    def get_queryset(self):
        return CompanyQuerySet(self.model, using=self._db)

    def browsable(self):
        return self.get_queryset().browsable()

    def base_queryset(self):
        return self.get_queryset().base_queryset()


class BrowsableCompanyManager(CompanyManager):
    """
    Excludes non-canonical products

    Could be deprecated after Oscar 0.7 is released
    """

    def get_queryset(self):
        return super(BrowsableCompanyManager, self).get_queryset().browsable()		