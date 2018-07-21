from django.conf import settings

from oscar.core.loading import get_model


def get_default_review_status():
    VendorReview = get_model('reviews', 'VendorReview')

    if settings.OSCAR_MODERATE_REVIEWS:
        return VendorReview.FOR_MODERATION

    return VendorReview.APPROVED
