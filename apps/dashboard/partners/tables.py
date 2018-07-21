from django_tables2 import A, Column, LinkColumn, TemplateColumn
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html

from oscar.core.loading import get_class, get_model

DashboardTable = get_class('dashboard.tables', 'DashboardTable')
Company = get_model('customer', 'company')

class VendorTable(DashboardTable):
    company_name = TemplateColumn(
        verbose_name=_('Company Name'),
        template_name='dashboard/partners/product_row_title.html',
         accessor=A('company_name'))
    company_logo = TemplateColumn(
        verbose_name=_('Company Logo'),
        template_name='dashboard/partners/product_row_image.html',
        orderable=False, accessor=A('company_logo'))
    check = TemplateColumn(
        template_name='dashboard/partners/user_row_checkbox.html',
        verbose_name=' ', orderable=False)

    user = Column(accessor='user')
    actions = TemplateColumn(
        verbose_name=_('Actions'),
        template_name='dashboard/partners/product_row_actions.html',
        orderable=False)

    icon = "sitemap"

    class Meta(DashboardTable.Meta):
        model = Company
        fields = ('company_name','user','company_logo')
        #fields = ('upc', 'date_updated')
        sequence = ('company_name','user','company_logo' # 'upc','product_class', 
                    #'variants', 'stock_records',
                    #'...', 'date_updated', 'actions')
                    ,'actions')
        #order_by = '-date_updated'
		
		

