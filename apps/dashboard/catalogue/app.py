from django.conf.urls import url

from oscar.core.application import DashboardApplication
from oscar.core.loading import get_class


class CatalogueApplication(DashboardApplication):
    name = None

    default_permissions = ['is_staff', ]
    permissions_map = _map = {
        'catalogue-product': (['is_staff'], ['partner.dashboard_access'],['customer.dashboard_access']),
        'catalogue-product-create': (['is_staff'],['customer.dashboard_access'],
                                     ['partner.dashboard_access']),
        'catalogue-product-list': (['is_staff'], ['partner.dashboard_access'],['customer.dashboard_access']),
        'catalogue-product-delete': (['is_staff'],['customer.dashboard_access'],
                                     ['partner.dashboard_access']),
        'catalogue-product-lookup': (['is_staff'],['customer.dashboard_access'],
                                     ['partner.dashboard_access']),
        
	
    }

    product_list_view = get_class('dashboard.catalogue.views',
                                  'ProductListView')
    product_lookup_view = get_class('dashboard.catalogue.views',
                                    'ProductLookupView')

    product_createupdate_view = get_class('dashboard.catalogue.views',
                                          'ProductCreateUpdateView')
    product_delete_view = get_class('dashboard.catalogue.views',
                                    'ProductDeleteView')
									
    category_list_view = get_class('dashboard.catalogue.views',
                                   'CategoryListView')
    category_detail_list_view = get_class('dashboard.catalogue.views',
                                          'CategoryDetailListView')
    category_create_view = get_class('dashboard.catalogue.views',
                                     'CategoryCreateView')
    category_update_view = get_class('dashboard.catalogue.views',
                                     'CategoryUpdateView')
    category_delete_view = get_class('dashboard.catalogue.views',
                                     'CategoryDeleteView')

    def get_urls(self):
        urls = [
            url(r'^products/(?P<pk>\d+)/$',
                self.product_createupdate_view.as_view(),
                name='catalogue-product'),

            url(r'^products/create/$',
                self.product_createupdate_view.as_view(),
                name='catalogue-product-create'),	

            url(r'^products/(?P<parent_pk>[-\d]+)/create-variant/$',
                self.product_createupdate_view.as_view(),
                name='catalogue-product-create-child'),
            url(r'^products/(?P<pk>\d+)/delete/$',
                self.product_delete_view.as_view(),
                name='catalogue-product-delete'),
            url(r'^$', self.product_list_view.as_view(),
                name='catalogue-product-list'),

            url(r'^product-lookup/$', self.product_lookup_view.as_view(),
                name='catalogue-product-lookup'),
            url(r'^categories/$', self.category_list_view.as_view(),
                name='catalogue-category-list'),
            url(r'^categories/(?P<pk>\d+)/$',
                self.category_detail_list_view.as_view(),
                name='catalogue-category-detail-list'),
            url(r'^categories/create/$', self.category_create_view.as_view(),
                name='catalogue-category-create'),
            url(r'^categories/create/(?P<parent>\d+)$',
                self.category_create_view.as_view(),
                name='catalogue-category-create-child'),
            url(r'^categories/(?P<pk>\d+)/update/$',
                self.category_update_view.as_view(),
                name='catalogue-category-update'),
            url(r'^categories/(?P<pk>\d+)/delete/$',
                self.category_delete_view.as_view(),
                name='catalogue-category-delete'),           
			
        ]
        return self.post_process_urls(urls)


application = CatalogueApplication()
