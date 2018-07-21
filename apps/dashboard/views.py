from datetime import timedelta
from decimal import Decimal as D
from decimal import ROUND_UP

from django.db.models import Avg, Count, Sum
from django.utils.timezone import now
from django.views.generic import TemplateView
from django_tables2 import SingleTableMixin, SingleTableView

from oscar.apps.promotions.models import AbstractPromotion
from oscar.core.compat import get_user_model
from oscar.core.loading import get_model, get_classes

(ProductForm,
 ProductSearchForm,
 CategoryForm) \
    = get_classes('dashboard.catalogue.forms',
                  ('ProductForm',
                   'ProductSearchForm',
                   'CategoryForm'))

ProductTable, CategoryTable \
    = get_classes('dashboard.catalogue.tables',
                  ('ProductTable', 'CategoryTable'))				   

Product = get_model('catalogue', 'Product')
User = get_user_model()

def filter_products(queryset, user):
    """
    Restrict the queryset to products the given user has access to.
    A staff user is allowed to access all Products.
    A non-staff user is only allowed access to a product if they are in at
    least one stock record's partner user list.
    """
    if user.is_staff:
        return queryset
    return queryset.filter(company=user.company).distinct()	

class IndexView(SingleTableView):

    """
    Dashboard view of the product list.
    Supports the permission-based dashboard.
    """

    template_name = 'dashboard/catalogue/product_list.html'
    form_class = ProductSearchForm
    #productclass_form_class = ProductClassSelectForm
    table_class = ProductTable
    context_table_name = 'products'

    def get_context_data(self, **kwargs):
        ctx = super(IndexView, self).get_context_data(**kwargs)
        ctx['form'] = self.form
        #ctx['productclass_form'] = self.productclass_form_class()
        return ctx

    '''def get_description(self, form):
        if form.is_valid() and any(form.cleaned_data.values()):
            return _('Product search results')
        return _('Products')

    def get_table(self, **kwargs):
        if 'recently_edited' in self.request.GET:
            kwargs.update(dict(orderable=False))

        table = super(ProductListView, self).get_table(**kwargs)
        table.caption = self.get_description(self.form)
        return table'''

    def get_table_pagination(self, table):
        return dict(per_page=20)

    def filter_queryset(self, queryset):
        """
        Apply any filters to restrict the products that appear on the list
        """
        return filter_products(queryset, self.request.user)

    def get_queryset(self):
        """
        Build the queryset for this list
        """
        queryset = Product.browsable.base_queryset()
        queryset = self.filter_queryset(queryset)
        queryset = self.apply_search(queryset)
        return queryset

    def apply_search(self, queryset):
        """
        Filter the queryset and set the description according to the search
        parameters given
        """
        self.form = self.form_class(self.request.GET)

        if not self.form.is_valid():
            return queryset

        data = self.form.cleaned_data

        if data.get('upc'):
            # Filter the queryset by upc
            # If there's an exact match, return it, otherwise return results
            # that contain the UPC
            matches_upc = Product.objects.filter(upc=data['upc'])
            qs_match = queryset.filter(
                Q(id__in=matches_upc.values('id')) |
                Q(id__in=matches_upc.values('parent_id')))

            if qs_match.exists():
                queryset = qs_match
            else:
                matches_upc = Product.objects.filter(upc__icontains=data['upc'])
                queryset = queryset.filter(
                    Q(id__in=matches_upc.values('id')) | Q(id__in=matches_upc.values('parent_id')))

        if data.get('title'):
            queryset = queryset.filter(title__icontains=data['title'])

        return queryset
	
	
class IndexView2(TemplateView):
    """
    An overview view which displays several reports about the shop.

    Supports the permission-based dashboard. It is recommended to add a
    index_nonstaff.html template because Oscar's default template will
    display potentially sensitive store information.
    """

    def get_template_names(self):
        if self.request.user.is_staff or self.request.user.company.is_vendor:
            return ['dashboard/index.html', ]
        else:
            return ['dashboard/index_nonstaff.html', 'dashboard/index.html']

    def get_context_data(self, **kwargs):
        ctx = super(IndexView, self).get_context_data(**kwargs)
        ctx.update(self.get_stats())
        return ctx

    '''def get_active_site_offers(self):
        """
        Return active conditional offers of type "site offer". The returned
        ``Queryset`` of site offers is filtered by end date greater then
        the current date.
        """
        return ConditionalOffer.objects.filter(
            end_datetime__gt=now(), offer_type=ConditionalOffer.SITE)

    def get_active_vouchers(self):
        """
        Get all active vouchers. The returned ``Queryset`` of vouchers
        is filtered by end date greater then the current date.
        """
        return Voucher.objects.filter(end_datetime__gt=now())

    def get_number_of_promotions(self, abstract_base=AbstractPromotion):
        """
        Get the number of promotions for all promotions derived from
        *abstract_base*. All subclasses of *abstract_base* are queried
        and if another abstract base class is found this method is executed
        recursively.
        """
        total = 0
        for cls in abstract_base.__subclasses__():
            if cls._meta.abstract:
                total += self.get_number_of_promotions(cls)
            else:
                total += cls.objects.count()
        return total

    def get_open_baskets(self, filters=None):
        """
        Get all open baskets. If *filters* dictionary is provided they will
        be applied on all open baskets and return only filtered results.
        """
        if filters is None:
            filters = {}
        filters['status'] = Basket.OPEN
        return Basket.objects.filter(**filters)

    def get_hourly_report(self, hours=24, segments=10):
        """
        Get report of order revenue split up in hourly chunks. A report is
        generated for the last *hours* (default=24) from the current time.
        The report provides ``max_revenue`` of the hourly order revenue sum,
        ``y-range`` as the labeling for the y-axis in a template and
        ``order_total_hourly``, a list of properties for hourly chunks.
        *segments* defines the number of labeling segments used for the y-axis
        when generating the y-axis labels (default=10).
        """
        # Get datetime for 24 hours agao
        time_now = now().replace(minute=0, second=0)
        start_time = time_now - timedelta(hours=hours - 1)

        orders_last_day = Order.objects.filter(date_placed__gt=start_time)

        order_total_hourly = []
        for hour in range(0, hours, 2):
            end_time = start_time + timedelta(hours=2)
            hourly_orders = orders_last_day.filter(date_placed__gt=start_time,
                                                   date_placed__lt=end_time)
            total = hourly_orders.aggregate(
                Sum('total_incl_tax')
            )['total_incl_tax__sum'] or D('0.0')
            order_total_hourly.append({
                'end_time': end_time,
                'total_incl_tax': total
            })
            start_time = end_time

        max_value = max([x['total_incl_tax'] for x in order_total_hourly])
        divisor = 1
        while divisor < max_value / 50:
            divisor *= 10
        max_value = (max_value / divisor).quantize(D('1'), rounding=ROUND_UP)
        max_value *= divisor
        if max_value:
            segment_size = (max_value) / D('100.0')
            for item in order_total_hourly:
                item['percentage'] = int(item['total_incl_tax'] / segment_size)

            y_range = []
            y_axis_steps = max_value / D(str(segments))
            for idx in reversed(range(segments + 1)):
                y_range.append(idx * y_axis_steps)
        else:
            y_range = []
            for item in order_total_hourly:
                item['percentage'] = 0

        ctx = {
            'order_total_hourly': order_total_hourly,
            'max_revenue': max_value,
            'y_range': y_range,
        }
        return ctx'''

    def get_stats(self):
        datetime_24hrs_ago = now() - timedelta(hours=24)

        #orders = Order.objects.all()
        #orders_last_day = orders.filter(date_placed__gt=datetime_24hrs_ago)

        #open_alerts = StockAlert.objects.filter(status=StockAlert.OPEN)
        #closed_alerts = StockAlert.objects.filter(status=StockAlert.CLOSED)

        #total_lines_last_day = Line.objects.filter(
        #    order__in=orders_last_day).count()
        stats = {
            #'total_orders_last_day': orders_last_day.count(),
            #'total_lines_last_day': total_lines_last_day,

            #'average_order_costs': orders_last_day.aggregate(
            #    Avg('total_incl_tax')
            #)['total_incl_tax__avg'] or D('0.00'),

            #'total_revenue_last_day': orders_last_day.aggregate(
            #    Sum('total_incl_tax')
            #)['total_incl_tax__sum'] or D('0.00'),

            #'hourly_report_dict': self.get_hourly_report(hours=24),
            'total_customers_last_day': User.objects.filter(
                date_joined__gt=datetime_24hrs_ago,
            ).count(),

            #'total_open_baskets_last_day': self.get_open_baskets({
            #    'date_created__gt': datetime_24hrs_ago
            #}).count(),

            'total_products': Product.objects.count(),
            #'total_open_stock_alerts': open_alerts.count(),
            #'total_closed_stock_alerts': closed_alerts.count(),

            #'total_site_offers': self.get_active_site_offers().count(),
            #'total_vouchers': self.get_active_vouchers().count(),
            #'total_promotions': self.get_number_of_promotions(),

            'total_customers': User.objects.count()
            #'total_open_baskets': self.get_open_baskets().count(),
            #'total_orders': orders.count(),
            #'total_lines': Line.objects.count(),
            #'total_revenue': orders.aggregate(
            #    Sum('total_incl_tax')
            #)['total_incl_tax__sum'] or D('0.00'),

            #'order_status_breakdown': orders.order_by(
            #    'status'
            #).values('status').annotate(freq=Count('id'))
        }
        return stats
