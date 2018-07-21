from oscar.apps.customer.reviews.abstract_models import (
    AbstractVendorReview, AbstractVote)
from oscar.core.loading import is_model_registered

if not is_model_registered('reviews', 'VendorReview'):
    class VendorReview(AbstractVendorReview):
        pass


if not is_model_registered('reviews', 'Vote'):
    class Vote(AbstractVote):
        pass
