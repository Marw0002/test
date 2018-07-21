from haystack import indexes

from oscar.core.loading import get_class, get_model

# Load default strategy (without a user/request)
is_solr_supported = get_class('search.features', 'is_solr_supported')
#Selector = get_class('partner.strategy', 'Selector')


class ProductIndex(indexes.SearchIndex, indexes.Indexable):
    # Search text
    text = indexes.CharField(
        document=True, use_template=True,
        template_name='search/indexes/product/item_text.txt')

    title = indexes.EdgeNgramField(model_attr='title', null=True)
    title_exact = indexes.CharField(model_attr='title', null=True, indexed=False)

    # Fields for faceting
    category = indexes.MultiValueField(null=True, faceted=True)
    rating = indexes.IntegerField(null=True, faceted=True)

    # Spelling suggestions
    suggestions = indexes.FacetCharField()

    date_created = indexes.DateTimeField(model_attr='date_created')
    date_updated = indexes.DateTimeField(model_attr='date_updated')

    _strategy = None

    def get_model(self):
        return get_model('catalogue', 'Product')

    def index_queryset(self, using=None):
        # Only index browsable products (not each individual child product)
        return self.get_model().browsable.order_by('-date_updated')

    def read_queryset(self, using=None):
        return self.get_model().browsable.base_queryset()

    def prepare_category(self, obj):
        categories = obj.categories.all()
        if len(categories) > 0:
            return [category.full_name for category in categories]

    def prepare_rating(self, obj):
        if obj.rating is not None:
            return int(obj.rating)

    # Pricing and stock is tricky as it can vary per customer.  However, the
    # most common case is for customers to see the same prices and stock levels
    # and so we implement that case here.


    def prepare(self, obj):
        prepared_data = super(ProductIndex, self).prepare(obj)

        # We use Haystack's dynamic fields to ensure that the title field used
        # for sorting is of type "string'.
        if is_solr_supported():
            prepared_data['title_s'] = prepared_data['title']

        # Use title to for spelling suggestions
        prepared_data['suggestions'] = prepared_data['text']

        return prepared_data

    def get_updated_field(self):
        """
        Used to specify the field used to determine if an object has been
        updated

        Can be used to filter the query set when updating the index
        """
        return 'date_updated'
		


class CompanyIndex(indexes.SearchIndex, indexes.Indexable):
    # Search text
    text = indexes.CharField(
        document=True, use_template=True,
        template_name='search/indexes/company/item_text.txt')

    company_name = indexes.EdgeNgramField(model_attr='company_name', null=True)
    company_name_exact = indexes.CharField(model_attr='company_name', null=True, indexed=False)

    # Fields for faceting
    category = indexes.MultiValueField(null=True, faceted=True)
    rating = indexes.IntegerField(null=True, faceted=True)

    # Spelling suggestions
    suggestions = indexes.FacetCharField()

    date_created = indexes.DateTimeField(model_attr='date_created')
    date_updated = indexes.DateTimeField(model_attr='date_updated')

    _strategy = None

    def get_model(self):
        return get_model('customer', 'Company')

    def index_queryset(self, using=None):
        # Only index browsable products (not each individual child product)
        return self.get_model().browsable.order_by('-date_updated')

    def read_queryset(self, using=None):
        return self.get_model().browsable.base_queryset()

    def prepare_category(self, obj):
        categories = obj.categories.all()
        if len(categories) > 0:
            return [category.full_name for category in categories]

    def prepare_rating(self, obj):
        if obj.rating is not None:
            return int(obj.rating)

    # Pricing and stock is tricky as it can vary per customer.  However, the
    # most common case is for customers to see the same prices and stock levels
    # and so we implement that case here.

    def prepare(self, obj):
        prepared_data = super(CompanyIndex, self).prepare(obj)

        # We use Haystack's dynamic fields to ensure that the title field used
        # for sorting is of type "string'.
        if is_solr_supported():
            prepared_data['company_name_s'] = prepared_data['company_name']

        # Use title to for spelling suggestions
        prepared_data['suggestions'] = prepared_data['text']

        return prepared_data

    def get_updated_field(self):
        """
        Used to specify the field used to determine if an object has been
        updated

        Can be used to filter the query set when updating the index
        """
        return 'date_updated'		

		
		