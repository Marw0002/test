from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.views import generic

from oscar.apps.customer.reviews.app import application as reviews_app
from oscar.core.application import Application
from oscar.core.loading import get_class


class BaseCustomerApplication(Application):
    name = 'customer'
    summary_view = get_class('customer.views', 'AccountSummaryView')

    email_list_view = get_class('customer.views', 'EmailHistoryView')
    email_detail_view = get_class('customer.views', 'EmailDetailView')
    login_view = get_class('customer.views', 'AccountAuthView')
    logout_view = get_class('customer.views', 'LogoutView')
    register_view = get_class('customer.views', 'AccountRegView')
    profile_view = get_class('customer.views', 'ProfileView')
    profile_update_view = get_class('customer.views', 'ProfileUpdateView')
    profile_delete_view = get_class('customer.views', 'ProfileDeleteView')
    detail_view = get_class('customer.views', 'CompanyDetailView')
    vendor_view = get_class('customer.views', 'CompanyProfileView')
    vendor_update = get_class('customer.views', 'CompanyProfileUpdateView')
	
    change_password_view = get_class('customer.views', 'ChangePasswordView')

    notification_inbox_view = get_class('customer.notifications.views',
                                        'InboxView')
    notification_archive_view = get_class('customer.notifications.views',
                                          'ArchiveView')
    notification_update_view = get_class('customer.notifications.views',
                                         'UpdateView')
    notification_detail_view = get_class('customer.notifications.views',
                                         'DetailView')
										 
    wishlists_add_product_view = get_class('customer.wishlists.views',
                                           'WishListAddProduct')
    wishlists_list_view = get_class('customer.wishlists.views',
                                    'WishListListView')
    wishlists_detail_view = get_class('customer.wishlists.views',
                                      'WishListDetailView')
    wishlists_create_view = get_class('customer.wishlists.views',
                                      'WishListCreateView')
    wishlists_create_with_product_view = get_class('customer.wishlists.views',
                                                   'WishListCreateView')
    wishlists_update_view = get_class('customer.wishlists.views',
                                      'WishListUpdateView')
    wishlists_delete_view = get_class('customer.wishlists.views',
                                      'WishListDeleteView')
    wishlists_remove_product_view = get_class('customer.wishlists.views',
                                              'WishListRemoveProduct')
    wishlists_move_product_to_another_view = get_class(
        'customer.wishlists.views', 'WishListMoveProductToAnotherWishList')

    def get_urls(self):
        urls = [
            # Login, logout and register doesn't require login
            url(r'^login/$', self.login_view.as_view(), name='login'),
            url(r'^logout/$', self.logout_view.as_view(), name='logout'),
            url(r'^register/$', self.register_view.as_view(), name='register'),
            url(r'^$', login_required(self.summary_view.as_view()),
                name='summary'),
            url(r'^change-password/$',
                login_required(self.change_password_view.as_view()),
                name='change-password'),

            # Profile
            url(r'^profile/$',
                login_required(self.profile_view.as_view()),
                name='profile-view'),
            url(r'^profile/edit/$',
                login_required(self.profile_update_view.as_view()),
                name='profile-update'),
            url(r'^profile/delete/$',
                login_required(self.profile_delete_view.as_view()),
                name='profile-delete'),
				
            url(r'^vendor-profile/$',
                login_required(self.vendor_view.as_view()),
                name='vendor-view'),
            url(r'^vendor-profile/edit/$',
                login_required(self.vendor_update.as_view()),
                name='vendor-update'),						
            url(r'^(?P<company_slug>[\w-]*)_(?P<pk>\d+)/$',
                self.detail_view.as_view(), name='vendor-detail'),		

            # Email history
            url(r'^emails/$',
                login_required(self.email_list_view.as_view()),
                name='email-list'),
            url(r'^emails/(?P<email_id>\d+)/$',
                login_required(self.email_detail_view.as_view()),
                name='email-detail'),
            url(r'^(?P<company_slug>[\w-]*)_(?P<company_pk>\d+)/reviews/',self.reviews_app.urls),
            # Notifications
            # Redirect to notification inbox
            url(r'^notifications/$', generic.RedirectView.as_view(
                url='/accounts/notifications/inbox/', permanent=False)),
            url(r'^notifications/inbox/$',
                login_required(self.notification_inbox_view.as_view()),
                name='notifications-inbox'),
            url(r'^notifications/archive/$',
                login_required(self.notification_archive_view.as_view()),
                name='notifications-archive'),
            url(r'^notifications/update/$',
                login_required(self.notification_update_view.as_view()),
                name='notifications-update'),
            url(r'^notifications/(?P<pk>\d+)/$',
                login_required(self.notification_detail_view.as_view()),
                name='notifications-detail'),

            # Wishlists
            url(r'wishlists/$',
                login_required(self.wishlists_list_view.as_view()),
                name='wishlists-list'),
            url(r'wishlists/add/(?P<product_pk>\d+)/$',
                login_required(self.wishlists_add_product_view.as_view()),
                name='wishlists-add-product'),
            url(r'wishlists/(?P<key>[a-z0-9]+)/add/(?P<product_pk>\d+)/',
                login_required(self.wishlists_add_product_view.as_view()),
                name='wishlists-add-product'),
            url(r'wishlists/create/$',
                login_required(self.wishlists_create_view.as_view()),
                name='wishlists-create'),
            url(r'wishlists/create/with-product/(?P<product_pk>\d+)/$',
                login_required(self.wishlists_create_view.as_view()),
                name='wishlists-create-with-product'),
            # Wishlists can be publicly shared, no login required
            url(r'wishlists/(?P<key>[a-z0-9]+)/$',
                self.wishlists_detail_view.as_view(), name='wishlists-detail'),
            url(r'wishlists/(?P<key>[a-z0-9]+)/update/$',
                login_required(self.wishlists_update_view.as_view()),
                name='wishlists-update'),
            url(r'wishlists/(?P<key>[a-z0-9]+)/delete/$',
                login_required(self.wishlists_delete_view.as_view()),
                name='wishlists-delete'),
            url(r'wishlists/(?P<key>[a-z0-9]+)/lines/(?P<line_pk>\d+)/delete/',
                login_required(self.wishlists_remove_product_view.as_view()),
                name='wishlists-remove-product'),
            url(r'wishlists/(?P<key>[a-z0-9]+)/products/(?P<product_pk>\d+)/'
                r'delete/',
                login_required(self.wishlists_remove_product_view.as_view()),
                name='wishlists-remove-product'),
            url(r'wishlists/(?P<key>[a-z0-9]+)/lines/(?P<line_pk>\d+)/move-to/'
                r'(?P<to_key>[a-z0-9]+)/$',
                login_required(self.wishlists_move_product_to_another_view
                               .as_view()),
                name='wishlists-move-product-to-another')]

        return self.post_process_urls(urls)

		
class ReviewsApplication(Application):
    name = None
    reviews_app = reviews_app

    def get_urls(self):
        urlpatterns = super(ReviewsApplication, self).get_urls()
        urlpatterns += [
            url(r'^(?P<company_slug>[\w-]*)_(?P<company_pk>\d+)/reviews/',
                self.reviews_app.urls)
        ]
        return self.post_process_urls(urlpatterns)


class CustomerApplication(BaseCustomerApplication, ReviewsApplication):
    """
    Composite class combining Products with Reviews
    """

application = CustomerApplication()
