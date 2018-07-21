from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from oscar.core.application import Application
from oscar.core.loading import get_class


class VendorReviewsApplication(Application):
    name = None
    hidable_feature_name = "reviews"

    detail_view = get_class('customer.reviews.views', 'VendorReviewDetail')
    create_view = get_class('customer.reviews.views', 'CreateVendorReview')
    vote_view = get_class('customer.reviews.views', 'AddVoteView')
    list_view = get_class('customer.reviews.views', 'VendorReviewList')

    def get_urls(self):
        urls = [
            url(r'^(?P<pk>\d+)/$', self.detail_view.as_view(),
                name='reviews-detail'),
            url(r'^add/$', self.create_view.as_view(),
                name='reviews-add'),
            url(r'^(?P<pk>\d+)/vote/$',
                login_required(self.vote_view.as_view()),
                name='reviews-vote'),
            url(r'^$', self.list_view.as_view(), name='reviews-list'),
        ]
        return self.post_process_urls(urls)


application = VendorReviewsApplication()
